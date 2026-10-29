import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync } from 'node:fs';
import { createApp, displayPost } from '../server/index.js';
import bank from '../data/question-bank.server.json' with { type: 'json' };

function fixture() {
  const sqlite=new DatabaseSync(':memory:');
  for(const name of readdirSync(new URL('../migrations/',import.meta.url)).filter(n=>n.endsWith('.sql')).sort())sqlite.exec(readFileSync(new URL(`../migrations/${name}`,import.meta.url),'utf8'));
  const DB={prepare(sql){return {bind(...values){this.values=values;return this;},async first(){return sqlite.prepare(sql).get(...(this.values??[]))??null;},async all(){return {results:sqlite.prepare(sql).all(...(this.values??[]))};},async run(){return sqlite.prepare(sql).run(...(this.values??[]));}};},async batch(statements){sqlite.exec('BEGIN');try{const results=[];for(const s of statements)results.push(await s.run());sqlite.exec('COMMIT');return results;}catch(e){sqlite.exec('ROLLBACK');throw e;}}};
  let time=1000000;
  const app=createApp({now:()=>time,modelResults:[]});
  let cookie='';
  async function request(path,data,headers={},target=app) {
    const res=await target.fetch(new Request(`https://sys1bench.com${path}`,{method:data===undefined?'GET':'POST',headers:{...(cookie?{cookie}:{}),...headers},body:data===undefined?undefined:JSON.stringify(data)}),{DB});
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

test('saved result snapshots survive a changed question set and remain private to the participant',async()=>{
  const f=fixture();const original=await f.completeRun();
  const runId=original.data.id;
  assert(f.sqlite.prepare('SELECT result_json FROM human_runs WHERE id=?').get(runId).result_json);
  const changed=createApp({dataset:{...bank,version:'future-question-set',pairs:bank.pairs.slice().reverse()}});
  const restored=await f.request(`/api/runs/${runId}/result`,undefined,{},changed);
  assert.equal(restored.status,200);assert.deepEqual(restored.data,original.data);
  const outsider=await f.request(`/api/runs/${runId}/result`,undefined,{cookie:`s1b_participant=${crypto.randomUUID()}`},changed);
  assert.equal(outsider.status,404);
  f.sqlite.close();
});
test('leaderboard exposes only real model runs for the current dataset and human protocol',async()=>{
  const f=fixture();
  const real={real:true,datasetVersion:bank.version,humanProtocol:'human-15s-visible-feedback-cross-author-education2-v4',modelId:'test/validated',name:'Validated model',protocol:'no-thinking-test',correct:10,total:15,unanswered:0,condition:'independent-no-thinking'};
  const app=createApp({modelResults:[real,{...real,modelId:'test/mock',real:false},{...real,modelId:'test/old',datasetVersion:'previous'},{...real,modelId:'test/other',humanProtocol:'previous'}]});
  const board=await f.request('/api/leaderboard',undefined,{},app);
  assert.equal(board.data.models.length,1);assert.equal(board.data.models[0].modelId,'test/validated');
  f.sqlite.close();
});

const rankedModels=[['a',11],['b',9],['c',7],['d',4]].map(([id,correct])=>({
  real:true,datasetVersion:bank.version,humanProtocol:'human-15s-visible-feedback-cross-author-education2-v4',
  modelId:`test/${id}`,name:`Model ${id}`,protocol:'no-thinking-test',correct,total:15,unanswered:0,
}));
function seedHuman(f,correct,{cohort=`${bank.version}:human-15s-visible-feedback-cross-author-education2-v4`,time=2000000}={}) {
  const id=crypto.randomUUID(),participant=crypto.randomUUID();
  f.sqlite.prepare("INSERT INTO human_runs(id,participant_id,cohort,dataset_version,assignments,created_at,finished_at,status) VALUES(?,?,?,?,?,?,?,'complete')").run(id,participant,cohort,bank.version,'[]',time-1000,time);
  f.sqlite.prepare('INSERT INTO human_first_results(participant_id,cohort,run_id,correct,total,completed_at) VALUES(?,?,?,?,15,?)').run(participant,cohort,id,correct,time);
  return {id,participant,correct};
}
test('humans and AI share competition ranks without exposing human identifiers',async()=>{
  const f=fixture();const people=[seedHuman(f,11),seedHuman(f,11,{time:2000001}),seedHuman(f,9,{time:2000002})];
  const app=createApp({modelResults:rankedModels});const board=(await f.request('/api/leaderboard',undefined,{},app)).data;
  assert.equal(board.totalEntries,7);assert.equal(board.abbreviated,false);
  assert.equal(board.entries.filter(e=>e.kind==='human').length,3);
  assert.equal(board.entries.filter(e=>e.kind==='ai').length,4);
  assert(board.entries.filter(e=>e.correct===11).every(e=>e.rank===1));
  assert(board.entries.filter(e=>e.correct===9).every(e=>e.rank===4));
  assert(board.entries.filter(e=>e.kind==='human').every(e=>/^Human \d+$/.test(e.name)));
  const payload=JSON.stringify(board);for(const person of people){assert(!payload.includes(person.id));assert(!payload.includes(person.participant));}
  f.sqlite.close();
});
test('long personal boards keep the viewer, leaders, neighbors, tail, and every AI with full-population ranks',async()=>{
  const f=fixture();const result=(await f.completeRun()).data;
  const people=Array.from({length:120},(_,i)=>seedHuman(f,i%16,{time:2000000+i}));
  seedHuman(f,15,{cohort:'another-cohort'});
  const app=createApp({modelResults:rankedModels});
  const board=(await f.request(`/api/runs/${result.id}/leaderboard`,undefined,{},app)).data;
  const you=board.entries.find(e=>e.isYou);
  assert.equal(board.totalEntries,125);assert.equal(board.abbreviated,true);assert(board.entries.length<=14);
  assert.equal(you.correct,result.correct);assert.equal(you.rank,1+people.filter(p=>p.correct>result.correct).length+rankedModels.filter(m=>m.correct>result.correct).length);
  assert.deepEqual(new Set(board.entries.filter(e=>e.kind==='ai').map(e=>e.modelId)),new Set(rankedModels.map(m=>m.modelId)));
  assert(board.entries.some(e=>e.position===1));assert(board.entries.some(e=>e.position===125));
  const publicBoard=(await f.request('/api/leaderboard',undefined,{},app)).data;
  assert.equal(publicBoard.totalEntries,125);assert(publicBoard.entries.length<=9);assert(!publicBoard.entries.some(e=>e.isYou));
  const changed=createApp({dataset:{...bank,version:'future'},modelResults:rankedModels});
  const archived=await f.request(`/api/runs/${result.id}/leaderboard`,undefined,{},changed);
  assert.equal(archived.status,200);assert.equal(archived.data.cohort,result.cohort);assert.equal(archived.data.totalEntries,125);
  const outsider=await f.request(`/api/runs/${result.id}/leaderboard`,undefined,{cookie:`s1b_participant=${crypto.randomUUID()}`},app);
  assert.equal(outsider.status,404);
  f.sqlite.close();
});
test('repeat result boards replace only your comparison row and leave the shared first-attempt board unchanged',async()=>{
  const f=fixture();const first=(await f.completeRun()).data;const repeat=(await f.completeRun()).data;
  const app=createApp({modelResults:rankedModels});
  const personal=(await f.request(`/api/runs/${repeat.id}/leaderboard`,undefined,{},app)).data;
  assert.equal(personal.viewer.isRepeat,true);assert.equal(personal.totalEntries,5);
  assert.equal(personal.entries.filter(e=>e.kind==='human').length,1);assert.equal(personal.entries.find(e=>e.isYou).correct,repeat.correct);
  const shared=(await f.request('/api/leaderboard',undefined,{},app)).data;
  assert.equal(shared.humans.count,1);assert.equal(shared.entries.find(e=>e.kind==='human').correct,first.correct);
  const pending=(await f.request('/api/runs',{})).data;
  assert.equal((await f.request(`/api/runs/${pending.id}/leaderboard`)).status,409);
  f.sqlite.close();
});
