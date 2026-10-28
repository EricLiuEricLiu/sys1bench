import { cpSync, readFileSync, readdirSync, existsSync, rmSync } from 'node:fs';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';
const bank = JSON.parse(readFileSync('data/question-bank.server.json', 'utf8'));
assert.equal(bank.practice.length, 2, 'Two distinct educational practice rounds are required');
assert.equal(bank.pairs.length, 15);
const seen = new Set();
for (const p of [...bank.practice, ...bank.pairs]) {
  assert.notEqual(p.left.views, p.right.views);
  for (const side of ['left','right']) {
    const post = p[side];
    assert(!seen.has(post.id), 'Practice and scored posts must not overlap'); seen.add(post.id);
    assert(Number.isSafeInteger(post.views) && post.views > 0);
    for (const media of post.media) {
      assert(/^media\/[\w.-]+\.jpg$/.test(media.assetFile));
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
