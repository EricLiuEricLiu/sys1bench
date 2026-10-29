import { cpSync, readFileSync, readdirSync, existsSync, rmSync } from 'node:fs';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import { TIMING, PROTOCOL, MINIMUM_VIEWS } from '../web/benchmark.js';
const bank = JSON.parse(readFileSync('data/question-bank.server.json', 'utf8'));
assert.equal(bank.practice.length, 2, 'Two distinct educational practice rounds are required');
assert.equal(bank.pairs.length, 15);
assert.deepEqual(bank.timing, TIMING, 'The question set and deployed timing must agree');
assert.equal(bank.humanProtocolId, PROTOCOL, 'The question set and deployed protocol must agree');
const models=JSON.parse(readFileSync('data/model-results.server.json','utf8')).results;
const modelKeys=new Set();
for(const model of models) {
  const key=`${model.datasetVersion}:${model.humanProtocol}:${model.modelId}`;assert(!modelKeys.has(key),'Only one primary result per model and cohort');modelKeys.add(key);
  assert.equal(model.real,true,'Only actual model results may be published');
  assert(Number.isInteger(model.correct) && model.correct>=0 && model.correct<=model.total);
  assert.equal(model.total,15);
  assert(model.correct+model.unanswered<=model.total);
  assert(Number.isInteger(model.unanswered) && model.unanswered>=0 && model.unanswered<=15);
  assert(model.modelId && model.name && model.protocol && model.runId && model.evaluatedAt);
  assert.equal(model.condition,'independent-no-thinking');
  assert(/^[a-f0-9]{64}$/.test(model.bankSha256));
  if(model.datasetVersion===bank.version) {
    assert.equal(model.humanProtocol,PROTOCOL);
    assert.equal(model.bankSha256,createHash('sha256').update(readFileSync('data/question-bank.server.json')).digest('hex'));
  }
}
const avatars=JSON.parse(readFileSync('data/avatars.server.json','utf8'));
assert.equal(avatars.datasetVersion,bank.version);
assert.equal(avatars.bankSha256,createHash('sha256').update(readFileSync('data/question-bank.server.json')).digest('hex'));
const seen = new Set();
for (const p of [...bank.practice, ...bank.pairs]) {
  assert.notEqual(p.left.views, p.right.views);
  assert.notEqual(p.left.author.id, p.right.author.id, 'Every pair must compare different authors');
  for (const side of ['left','right']) {
    const post = p[side];
    assert(!seen.has(post.id), 'Practice and scored posts must not overlap'); seen.add(post.id);
    const avatar=avatars.byPost[post.id];
    assert(avatar && /^avatars\/[a-f0-9]{64}\.(?:jpg|png|webp)$/.test(avatar.assetFile),'Missing captured avatar');
    assert.equal(avatar.sourceAvatarUrl,post.author.avatarUrl);
    assert.equal(createHash('sha256').update(readFileSync(`web/${avatar.assetFile}`)).digest('hex'),avatar.sha256);
    assert(Number.isSafeInteger(post.views) && post.views >= MINIMUM_VIEWS, 'Every post must meet the high-reach floor');
    for (const metric of ['replies','reposts','likes','impressions']) assert(Number.isSafeInteger(post.engagement?.[metric]) && post.engagement[metric] >= 0, `Missing captured ${metric}`);
    assert.equal(post.engagement.impressions, post.views, 'The impression target must match the captured view count');
    for (const media of post.media) {
      assert(/^media\/[\w.-]+\.(?:jpg|jpeg|png|webp)$/.test(media.assetFile));
      const bytes = readFileSync(`web/${media.assetFile}`);
      assert.equal(createHash('sha256').update(bytes).digest('hex'), media.sha256);
    }
  }
}
for (const file of ['index.html','app.js','components.js','components.css','tokens.css','leaderboard.html','leaderboard.js','results.html','results.js','ui.js','api.js']) assert(existsSync(`web/${file}`), `Missing web/${file}`);
function inspect(directory) {
  for (const f of readdirSync(directory,{withFileTypes:true})) {
    if (f.isDirectory()) inspect(`${directory}/${f.name}`);
    else assert(!/(questions|question-bank|stimuli|provenance|\.env|\.sql|\.jsonl)/i.test(f.name), `Private data in public assets: ${f.name}`);
  }
}
inspect('web');
rmSync('dist',{recursive:true,force:true});
cpSync('web','dist',{recursive:true});
console.log(`Built System 1 Bench: ${bank.version}, 2 practice + 15 scored pairs; answers remain in the Worker.`);
