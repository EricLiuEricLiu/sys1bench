import { cpSync, readFileSync, readdirSync, existsSync, rmSync } from 'node:fs';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
import { TIMING, PROTOCOL, MINIMUM_VIEWS } from '../web/benchmark.js';
const bank = JSON.parse(readFileSync('data/question-bank.server.json', 'utf8'));
assert.equal(bank.practice.length, 2, 'Two distinct educational practice rounds are required');
assert.equal(bank.pairs.length, 15);
assert.deepEqual(bank.timing, TIMING, 'The question set and deployed timing must agree');
assert.equal(bank.humanProtocolId, PROTOCOL, 'The question set and deployed protocol must agree');
const seen = new Set();
for (const p of [...bank.practice, ...bank.pairs]) {
  assert.notEqual(p.left.views, p.right.views);
  assert.notEqual(p.left.author.id, p.right.author.id, 'Every pair must compare different authors');
  for (const side of ['left','right']) {
    const post = p[side];
    assert(!seen.has(post.id), 'Practice and scored posts must not overlap'); seen.add(post.id);
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
for (const file of ['index.html','app.js','components.js','components.css','tokens.css','leaderboard.html','leaderboard.js']) assert(existsSync(`web/${file}`), `Missing web/${file}`);
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
