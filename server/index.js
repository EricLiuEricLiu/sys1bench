import bank from '../data/question-bank.server.json' with { type: 'json' };
import { TIMING, PROTOCOL } from '../web/benchmark.js';

const COOKIE = 's1b_participant';
const UUID = /^[a-f0-9-]{36}$/;
const json = (data, status = 200, extra = {}) => new Response(JSON.stringify(data), {
  status, headers: { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...extra },
});
const fail = (message, status = 400) => Object.assign(new Error(message), { status });

export function displayPost(post) {
  return {
    id: post.id,
    text: post.displayText ?? post.text,
    displayText: post.displayText ?? post.text,
    author: { name: post.author.name, handle: post.author.handle, avatarUrl: post.author.avatarUrl, verified: Boolean(post.author.verified) },
    media: post.media.map(m => ({ type: m.type, url: `/${m.assetFile}`, assetFile: `/${m.assetFile}`, width: m.width, height: m.height, alt: m.alt ?? '' })),
  };
}

function shuffle(items) {
  const a = [...items];
  for (let i = a.length - 1; i > 0; i--) {
    let n;
    const ceiling = Math.floor(2 ** 32 / (i + 1)) * (i + 1);
    do { n = crypto.getRandomValues(new Uint32Array(1))[0]; } while (n >= ceiling);
    const j = n % (i + 1);
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

export function makeAssignments(dataset) {
  return [...dataset.practice.map(p => ({ pairId: p.id, kind: 'practice' })), ...shuffle(dataset.pairs).map(p => ({ pairId: p.id, kind: 'scored' }))]
    .map(a => ({ ...a, flipped: Boolean(crypto.getRandomValues(new Uint8Array(1))[0] & 1) }));
}

export function gradeAnswer(pair, choice) {
  return choice !== null && pair[choice].engagement.impressions > pair[choice === 'left' ? 'right' : 'left'].engagement.impressions;
}

export function createApp({ dataset = bank, now = Date.now } = {}) {
  const cohort = `${dataset.version}:${PROTOCOL}`;
  const byId = new Map([...dataset.practice, ...dataset.pairs].map(p => [p.id, p]));
  const assignPair = a => {
    const p = byId.get(a.pairId);
    return a.flipped ? { id: p.id, left: p.right, right: p.left } : p;
  };
  const publicPair = p => ({ id: p.id, left: displayPost(p.left), right: displayPost(p.right) });

  async function body(request) {
    if (Number(request.headers.get('content-length')) > 4096) throw fail('Request is too large.', 413);
    const text = await request.text();
    if (text.length > 4096) throw fail('Request is too large.', 413);
    try { return JSON.parse(text || '{}'); } catch { throw fail('Invalid JSON.'); }
  }

  return {
    async fetch(request, env) {
      const url = new URL(request.url);
      if (!url.pathname.startsWith('/api/')) return env.ASSETS.fetch(request);
      try {
        if (request.method === 'POST' && request.headers.get('Origin') && request.headers.get('Origin') !== url.origin) throw fail('Origin is not allowed.', 403);
        const cookie = request.headers.get('Cookie')?.split(';').map(p => p.trim()).find(p => p.startsWith(`${COOKIE}=`))?.slice(COOKIE.length + 1);
        const participant = UUID.test(cookie ?? '') ? cookie : null;
        if (url.pathname === '/api/health' && request.method === 'GET') {
          await env.DB.prepare('SELECT id FROM human_runs LIMIT 1').first();
          return json({ status: 'ok', datasetVersion: dataset.version, protocol: PROTOCOL, timing: TIMING });
        }
        if (url.pathname === '/api/runs' && request.method === 'POST') {
          const id = crypto.randomUUID();
          const owner = participant ?? crypto.randomUUID();
          const count = await env.DB.prepare('SELECT COUNT(*) AS n FROM human_runs WHERE participant_id=? AND created_at>?').bind(owner, now() - 3600000).first();
          if (count.n >= 30) throw fail('Please wait before starting another test.', 429);
          await env.DB.prepare('INSERT INTO human_runs (id,participant_id,cohort,dataset_version,assignments,created_at) VALUES (?,?,?,?,?,?)')
            .bind(id, owner, cohort, dataset.version, JSON.stringify(makeAssignments(dataset)), now()).run();
          return json({ id, datasetVersion: dataset.version, practiceRounds: dataset.practice.length, scoredRounds: dataset.pairs.length, timing: TIMING }, 201,
            { 'Set-Cookie': `${COOKIE}=${owner}; Path=/; HttpOnly; SameSite=Lax; Max-Age=31536000${url.protocol === 'https:' ? '; Secure' : ''}` });
        }
        if (url.pathname === '/api/leaderboard' && request.method === 'GET') {
          const aggregate = await env.DB.prepare('SELECT COUNT(*) AS count, AVG(1.0*correct/total) AS accuracy FROM human_first_results WHERE cohort=?').bind(cohort).first();
          const distribution = await env.DB.prepare('SELECT correct,COUNT(*) AS count FROM human_first_results WHERE cohort=? GROUP BY correct ORDER BY correct DESC').bind(cohort).all();
          return json({ cohort, datasetVersion: dataset.version, protocol: PROTOCOL, humans: { ...aggregate, distribution: distribution.results }, models: [], pilot: true });
        }
        const match = url.pathname.match(/^\/api\/runs\/([a-f0-9-]{36})\/(next|open|answer|result|abort)$/);
        if (!match) throw fail('Not found.', 404);
        if (!participant) throw fail('Enable cookies to take the test.', 401);
        const run = await env.DB.prepare('SELECT * FROM human_runs WHERE id=? AND participant_id=?').bind(match[1], participant).first();
        if (!run) throw fail('Test not found.', 404);
        if (run.cohort !== cohort) throw fail('This test has changed. Please start again.', 409);
        const assignments = JSON.parse(run.assignments);
        const action = match[2];
        if (action === 'abort' && request.method === 'POST') {
          await env.DB.prepare("UPDATE human_runs SET status='aborted' WHERE id=? AND status='active'").bind(run.id).run();
          return json({ status: 'aborted' });
        }
        if (action === 'result' && request.method === 'GET') {
          if (run.status !== 'complete') throw fail('Finish the test first.', 409);
          const rows = await env.DB.prepare('SELECT * FROM human_answers WHERE run_id=? ORDER BY ordinal').bind(run.id).all();
          const scored = rows.results.filter(a => a.kind === 'scored');
          const first = await env.DB.prepare('SELECT run_id FROM human_first_results WHERE participant_id=? AND cohort=?').bind(participant, cohort).first();
          return json({ cohort, correct: scored.filter(a => a.correct).length, total: scored.length, missed: scored.filter(a => a.choice === null).length,
            countedInAggregate: first?.run_id === run.id,
            answers: scored.map(a => { const p = assignPair(assignments[a.ordinal]); return { choice: a.choice, correct: Boolean(a.correct), pair: { ...publicPair(p), left: { ...displayPost(p.left), views: p.left.views, engagement: p.left.engagement, url: p.left.url }, right: { ...displayPost(p.right), views: p.right.views, engagement: p.right.engagement, url: p.right.url } } }; }) });
        }
        if (run.status !== 'active') throw fail('This test is no longer active.', 409);
        if (action === 'next' && request.method === 'GET') {
          const assignment = assignments[run.next_ordinal];
          return json({ ordinal: run.next_ordinal, kind: assignment.kind, pair: publicPair(assignPair(assignment)) });
        }
        if (action === 'open' && request.method === 'POST') {
          const data = await body(request);
          if (data.ordinal !== run.next_ordinal) throw fail('Round is out of order.', 409);
          await env.DB.prepare('UPDATE human_runs SET opened_at=COALESCE(opened_at,?) WHERE id=? AND next_ordinal=? AND status=\'active\'').bind(now(), run.id, run.next_ordinal).run();
          return json({ opened: true });
        }
        if (action === 'answer' && request.method === 'POST') {
          const data = await body(request);
          if (data.ordinal !== run.next_ordinal) throw fail('Round is out of order.', 409);
          if (![null, 'left', 'right'].includes(data.choice) || !Number.isFinite(data.observedMs) || data.observedMs < 0 || data.observedMs > TIMING.roundMs + 1500) throw fail('Invalid round timing. Please start again.');
          if (data.choice === null) {
            if (data.responseMs !== null || data.observedMs < TIMING.roundMs - 100) throw fail('The round is still open.');
          } else if (!Number.isFinite(data.responseMs) || data.responseMs < 0 || data.responseMs >= TIMING.roundMs || Math.abs(data.responseMs - data.observedMs) > 100) throw fail('Answer deadline has passed.');
          const elapsed = run.opened_at === null ? null : now() - run.opened_at;
          if (elapsed === null || elapsed < data.observedMs - 300 || elapsed > TIMING.roundMs + 5000) throw fail('Round expired. Please start again.', 409);
          const assignment = assignments[run.next_ordinal];
          const pair = assignPair(assignment);
          const correct = gradeAnswer(pair, data.choice);
          const end = run.next_ordinal + 1 === assignments.length;
          const statements = [
            env.DB.prepare('INSERT INTO human_answers (run_id,ordinal,pair_id,kind,choice,correct,response_ms,observed_ms,answered_at) SELECT ?,?,?,?,?,?,?,?,? FROM human_runs WHERE id=? AND next_ordinal=? AND status=\'active\'')
              .bind(run.id, run.next_ordinal, pair.id, assignment.kind, data.choice, Number(correct), data.responseMs ?? null, data.observedMs, now(), run.id, run.next_ordinal),
            env.DB.prepare('UPDATE human_runs SET next_ordinal=next_ordinal+1,opened_at=NULL,status=?,finished_at=? WHERE id=? AND next_ordinal=? AND status=\'active\'')
              .bind(end ? 'complete' : 'active', end ? now() : null, run.id, run.next_ordinal),
          ];
          if (end) statements.push(env.DB.prepare('INSERT OR IGNORE INTO human_first_results (participant_id,cohort,run_id,correct,total,completed_at) SELECT participant_id,cohort,id,(SELECT COALESCE(SUM(correct),0) FROM human_answers WHERE run_id=? AND kind=\'scored\'),15,? FROM human_runs WHERE id=? AND status=\'complete\'')
            .bind(run.id, now(), run.id));
          await env.DB.batch(statements);
          return json({ saved: true, complete: end, feedback: { correct, winner: pair.left.engagement.impressions > pair.right.engagement.impressions ? 'left' : 'right', engagement: { left: pair.left.engagement, right: pair.right.engagement } } });
        }
        throw fail('Method is not allowed.', 405);
      } catch (error) {
        if (!error.status) console.error('API request failed', error.name);
        return json({ error: error.status ? error.message : 'Something went wrong. Please try again.' }, error.status ?? 500);
      }
    },
  };
}

export default createApp();
