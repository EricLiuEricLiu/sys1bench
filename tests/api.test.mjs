import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';
import { createApp, displayPost } from '../server/index.js';
import bank from '../data/question-bank.server.json' with { type: 'json' };

function fixture() {
  const sqlite=new DatabaseSync(':memory:');
  sqlite.exec(readFileSync(new URL('../migrations/0001_human_runs.sql',import.meta.url),'utf8'));
  const DB={prepare(sql){return {bind(...values){this.values=values;return this;},async first(){return sqlite.prepare(sql).get(...(this.values??[]))??null;},async all(){return {results:sqlite.prepare(sql).all(...(this.values??[]))};},async run(){return sqlite.prepare(sql).run(...(this.values??[]));}};},async batch(statements){sqlite.exec('BEGIN');try{const results=[];for(const s of statements)results.push(await s.run());sqlite.exec('COMMIT');return results;}catch(e){sqlite.exec('ROLLBACK');throw e;}}};
  let time=1000000;
  const app=createApp({now:()=>time});
  let cookie='';
  async function request(path,data,headers={}) {
    const res=await app.fetch(new Request(`https://sys1bench.com${path}`,{method:data===undefined?'GET':'POST',headers:{...(cookie?{cookie}:{}),...headers},body:data===undefined?undefined:JSON.stringify(data)}),{DB});
    if(res.headers.get('set-cookie'))cookie=res.headers.get('set-cookie').split(';')[0];
    return {status:res.status,data:await res.json()};
  }
  async function completeRun() {
    const created=await request('/api/runs',{}); assert.equal(created.status,201);
    for(let ordinal=0;ordinal<17;ordinal++) {
      const next=await request(`/api/runs/${created.data.id}/next`);
      assert.equal(next.data.ordinal,ordinal);
      assert(!JSON.stringify(next.data).includes('"views"'));
      const opened=await request(`/api/runs/${created.data.id}/open`,{ordinal}); assert.equal(opened.status,200);
      time+=1200;
      const saved=await request(`/api/runs/${created.data.id}/answer`,{ordinal,choice:'left',observedMs:1200,responseMs:1200,correct:true});
      assert.equal(saved.status,200);
      assert.equal(Boolean(saved.data.feedback),true);
      for (const side of ['left','right']) {
        assert.deepEqual(Object.keys(saved.data.feedback.engagement[side]),['replies','reposts','likes','impressions']);
        assert(Object.values(saved.data.feedback.engagement[side]).every(Number.isSafeInteger));
      }
      time+=2500;
      assert.equal(saved.data.complete,ordinal===16);
    }
    return request(`/api/runs/${created.data.id}/result`);
  }
  return {request,completeRun,sqlite,DB,advance:ms=>time+=ms};
}

test('current question set uses one 15-second window, real engagement metrics, and different authors',()=>{
  assert.deepEqual(bank.timing,{roundMs:15000,revealMs:2500});
  for(const pair of [...bank.practice,...bank.pairs]) {
    assert.notEqual(pair.left.author.id,pair.right.author.id);
    assert(pair.left.views>=100000 && pair.right.views>=100000);
    for(const side of ['left','right']) {
      const post=pair[side];
      assert.equal(post.engagement.impressions,post.views);
      for(const key of ['replies','reposts','likes','impressions'])assert(Number.isSafeInteger(post.engagement[key]) && post.engagement[key]>=0);
    }
  }
});
test('scored questions include several very popular posts',()=>{
  const popular=bank.pairs.flatMap(pair=>[pair.left,pair.right]).filter(post=>post.engagement.impressions>=10000000);
  assert(popular.length>=3);
});
test('display payload contains no outcomes, followers, source URLs or matching metadata',()=>{
  for(const pair of [...bank.practice,...bank.pairs])for(const side of ['left','right']) {
    const post=displayPost(pair[side]);
    assert.deepEqual(Object.keys(post),['id','text','displayText','author','media']);
    assert(!/"(?:views|engagement|replies|reposts|likes|impressions|matching|followerCounts|followers)"\s*:/.test(JSON.stringify(post)));
    assert.deepEqual(Object.keys(post.author),['name','handle','avatarUrl','verified']);
    for(const image of post.media)assert(image.url.startsWith('/media/'));
  }
});
test('two education rounds are unscored; every answer reveals only its own metrics and scoring stays on the server',async()=>{
  const f=fixture(); const result=await f.completeRun();
  assert.equal(result.status,200);assert.equal(result.data.total,15);assert.equal(result.data.answers.length,15);
  const correct=f.sqlite.prepare("SELECT SUM(correct) AS correct FROM human_answers WHERE kind='scored'").get().correct;
  assert.equal(result.data.correct,correct);assert(result.data.answers[0].pair.left.views>0);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM human_answers').get().n,17);
  f.sqlite.close();
});
test('repeat completions stay out of human aggregate and mock/model scores are never invented',async()=>{
  const f=fixture();const first=await f.completeRun();const second=await f.completeRun();
  assert.equal(first.data.countedInAggregate,true);assert.equal(second.data.countedInAggregate,false);
  const board=await f.request('/api/leaderboard');assert.equal(board.data.humans.count,1);assert.deepEqual(board.data.models,[]);
  f.sqlite.close();
});
test('rejects unopened, expired, out-of-order, invalid, late, and cross-origin submissions',async()=>{
  const f=fixture();const created=await f.request('/api/runs',{});const id=created.data.id;
  const answer={ordinal:0,choice:'left',observedMs:1200,responseMs:1200};
  assert.equal((await f.request(`/api/runs/${id}/result`)).status,409);
  assert.equal((await f.request(`/api/runs/${id}/answer`,answer)).status,409);
  assert.equal((await f.request(`/api/runs/${id}/open`,{ordinal:2})).status,409);
  await f.request(`/api/runs/${id}/open`,{ordinal:0});
  assert.equal((await f.request(`/api/runs/${id}/answer`,answer)).status,409);
  f.advance(1200);
  assert.equal((await f.request(`/api/runs/${id}/answer`,{...answer,choice:'up'})).status,400);
  assert.equal((await f.request(`/api/runs/${id}/answer`,{...answer,responseMs:15000,observedMs:15000})).status,400);
  assert.equal((await f.request(`/api/runs/${id}/answer`,{...answer,responseMs:1200,observedMs:10000})).status,400);
  assert.equal((await f.request(`/api/runs/${id}/answer`,{...answer,choice:null,responseMs:null})).status,400);
  f.advance(20001);
  assert.equal((await f.request(`/api/runs/${id}/answer`,answer)).status,409);
  assert.equal((await f.request('/api/runs',{}, {Origin:'https://example.com'})).status,403);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM human_answers').get().n,0);f.sqlite.close();
});
test('aborted runs never produce results or leaderboard entries',async()=>{
  const f=fixture();const created=await f.request('/api/runs',{});const id=created.data.id;
  await f.request(`/api/runs/${id}/abort`,{});
  assert.equal((await f.request(`/api/runs/${id}/next`)).status,409);
  assert.equal((await f.request(`/api/runs/${id}/result`)).status,409);
  assert.equal((await f.request('/api/leaderboard')).data.humans.count,0);f.sqlite.close();
});
test('a post can be selected immediately or just before the 15-second deadline',async()=>{
  for(const elapsed of [0,500,14999]) {
    const f=fixture();const created=await f.request('/api/runs',{});const id=created.data.id;
    assert.deepEqual(created.data.timing,{roundMs:15000,revealMs:2500});
    const next=await f.request(`/api/runs/${id}/next`);
    assert(!JSON.stringify(next.data).includes('"engagement"'));
    await f.request(`/api/runs/${id}/open`,{ordinal:0});
    f.advance(elapsed);
    const saved=await f.request(`/api/runs/${id}/answer`,{ordinal:0,choice:'right',observedMs:elapsed,responseMs:elapsed});
    assert.equal(saved.status,200);assert.equal(saved.data.saved,true);
    const original=[...bank.practice,...bank.pairs].flatMap(p=>[p.left,p.right]).find(p=>p.id===next.data.pair.right.id);
    assert.deepEqual(saved.data.feedback.engagement.right,original.engagement);
    assert.equal((await f.request(`/api/runs/${id}/answer`,{ordinal:0,choice:'left',observedMs:elapsed,responseMs:elapsed})).status,409);
    assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM human_answers').get().n,1);
    f.sqlite.close();
  }
});
test('a 15-second timeout is recorded as unanswered and still reveals metrics',async()=>{
  const f=fixture();const created=await f.request('/api/runs',{});const id=created.data.id;
  await f.request(`/api/runs/${id}/open`,{ordinal:0});
  f.advance(15010);
  const saved=await f.request(`/api/runs/${id}/answer`,{ordinal:0,choice:null,observedMs:15010,responseMs:null});
  assert.equal(saved.status,200);assert.equal(saved.data.feedback.correct,false);
  assert(saved.data.feedback.engagement.left.impressions>0);
  const row=f.sqlite.prepare('SELECT choice,correct,response_ms FROM human_answers').get();
  assert.deepEqual({...row},{choice:null,correct:0,response_ms:null});
  f.sqlite.close();
});
test('comparison cohorts stay separate across question-set versions and timing protocols',async()=>{
  const f=fixture();await f.completeRun();
  const other=createApp({dataset:{...bank,version:'previous-pilot'}});
  const result=await other.fetch(new Request('https://sys1bench.com/api/leaderboard'),{DB:f.DB});
  const board=await result.json();assert.equal(board.humans.count,0);
  assert.equal((await f.request('/api/leaderboard')).data.humans.count,1);
  const previousTiming=`${bank.version}:human-15s5s-cross-author-highreach-education2-v3`;
  f.sqlite.prepare('UPDATE human_first_results SET cohort=?').run(previousTiming);
  assert.equal((await f.request('/api/leaderboard')).data.humans.count,0);
  assert.equal(f.sqlite.prepare('SELECT COUNT(*) AS n FROM human_first_results WHERE cohort=?').get(previousTiming).n,1);
  f.sqlite.close();
});
