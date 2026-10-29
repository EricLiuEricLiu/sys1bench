import test from 'node:test';
import assert from 'node:assert/strict';
import { arrangeRankings } from '../web/ranking.js';

test('your row is first while keeping its actual rank and not inventing gaps in a complete board',()=>{
  const entries=[{key:'ai',kind:'ai',position:1,rank:1},{key:'human:2',kind:'human',position:2,rank:2},{key:'you',isYou:true,kind:'human',position:3,rank:2},{key:'human:4',kind:'human',position:4,rank:4}];
  const rows=arrangeRankings({entries,totalEntries:4});
  assert.equal(rows[0].entry.key,'you');assert.equal(rows[0].entry.rank,2);
  assert(rows.every(r=>r.type==='entry'));assert.equal(new Set(rows.map(r=>r.entry.key)).size,4);
});
test('omission counts exclude your already-pinned row and preserve all returned AI entries',()=>{
  const entries=[{key:'h1',position:1},{key:'a',kind:'ai',position:8},{key:'h24',position:24},{key:'you',isYou:true,position:25,rank:20},{key:'h26',position:26},{key:'b',kind:'ai',position:79},{key:'h100',position:100}];
  const rows=arrangeRankings({entries,totalEntries:100});
  assert.equal(rows[0].entry.key,'you');
  assert.equal(rows.filter(r=>r.type==='gap').reduce((sum,r)=>sum+r.count,0),100-entries.length);
  assert.deepEqual(rows.filter(r=>r.type==='entry'&&r.entry.kind==='ai').map(r=>r.entry.key),['a','b']);
});
test('an empty board stays empty and a viewer-only board has no omitted entries',()=>{
  assert.deepEqual(arrangeRankings({entries:[],totalEntries:0}),[]);
  const you={isYou:true,position:1,rank:1};assert.deepEqual(arrangeRankings({entries:[you],totalEntries:1}),[{type:'entry',entry:you}]);
});
