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
      time+=6100;
      const saved=await request(`/api/runs/${created.data.id}/answer`,{ordinal,choice:'left',observedMs:6000,responseMs:100,correct:true});
      assert.equal(saved.status,200);
      assert.equal(Boolean(saved.data.feedback),ordinal<2);
      assert.equal(saved.data.complete,ordinal===16);
    }
    return request(`/api/runs/${created.data.id}/result`);
  }
  return {request,completeRun,sqlite,DB,advance:ms=>time+=ms};
}

test('current question set uses 6/4 timing, different authors, and higher-reach posts',()=>{
  assert.deepEqual(bank.timing,{exposureMs:6000,decisionMs:4000});
  for(const pair of [...bank.practice,...bank.pairs]) {
    assert.notEqual(pair.left.author.id,pair.right.author.id);
    assert(pair.left.views>=100000 && pair.right.views>=100000);
  }
});
test('display payload contains no outcomes, followers, source URLs or matching metadata',()=>{
  for(const pair of [...bank.practice,...bank.pairs])for(const side of ['left','right']) {
    const post=displayPost(pair[side]);
    assert.deepEqual(Object.keys(post),['id','text','displayText','author','media']);
    assert(!/"(?:views|matching|followerCounts|followers)"\s*:/.test(JSON.stringify(post)));
    assert.deepEqual(Object.keys(post.author),['name','handle','avatarUrl','verified']);
    for(const image of post.media)assert(image.url.startsWith('/media/'));
  }
});
test('two education rounds are unscored; score is computed on server and labels appear only after completion',async()=>{
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
test('rejects early answers, expired rounds, out-of-order submissions, invalid choices, and cross-origin writes',async()=>{
  const f=fixture();const created=await f.request('/api/runs',{});const id=created.data.id;
  assert.equal((await f.request(`/api/runs/${id}/result`)).status,409);
  assert.equal((await f.request(`/api/runs/${id}/open`,{ordinal:2})).status,409);
  await f.request(`/api/runs/${id}/open`,{ordinal:0});
  const answer={ordinal:0,choice:'left',observedMs:6000,responseMs:50};
  assert.equal((await f.request(`/api/runs/${id}/answer`,answer)).status,409);
  f.advance(6100);
  assert.equal((await f.request(`/api/runs/${id}/answer`,{...answer,choice:'up'})).status,400);
  assert.equal((await f.request(`/api/runs/${id}/answer`,{...answer,responseMs:4000})).status,400);
  f.advance(16000);
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
test('the expanded decision window accepts a 3-second choice after a 6-second glimpse',async()=>{
  const f=fixture();const created=await f.request('/api/runs',{});const id=created.data.id;
  assert.deepEqual(created.data.timing,{exposureMs:6000,decisionMs:4000});
  await f.request(`/api/runs/${id}/open`,{ordinal:0});
  f.advance(9100);
  const saved=await f.request(`/api/runs/${id}/answer`,{ordinal:0,choice:'right',observedMs:6000,responseMs:3000});
  assert.equal(saved.status,200);assert.equal(saved.data.saved,true);
  f.sqlite.close();
});
test('comparison cohorts stay separate across question-set versions',async()=>{
  const f=fixture();await f.completeRun();
  const other=createApp({dataset:{...bank,version:'previous-pilot'}});
  const result=await other.fetch(new Request('https://sys1bench.com/api/leaderboard'),{DB:f.DB});
  const board=await result.json();assert.equal(board.humans.count,0);
  assert.equal((await f.request('/api/leaderboard')).data.humans.count,1);
  f.sqlite.close();
});
