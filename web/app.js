import { createRoundController, renderPostPair } from './components.js';

let run;
let controller;
let token = 0;
const root = document.createElement('div');
root.className = 'app-shell';
const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
function button(label, action) { const n = el('button','i-button',label); n.type='button'; n.addEventListener('click',action); return n; }
async function api(path, data) {
  const response = await fetch(path, { method: data === undefined ? 'GET' : 'POST', credentials: 'same-origin', headers: data === undefined ? {} : {'Content-Type':'application/json'}, body: data === undefined ? undefined : JSON.stringify(data) });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error ?? 'The test could not load.');
  return result;
}
function frame(kicker, title, copy) {
  root.replaceChildren();
  const header = el('header','app-header');
  const home=el('a','app-brand','System 1 Bench'); home.href='/';
  const label=el('span','app-mono','INTERNET INSTINCT'); header.append(home,label);
  const main=el('main','app-main'); main.tabIndex=-1; main.id='test-main';
  if(kicker)main.append(el('p','app-kicker',kicker));
  if(title)main.append(el('h1','app-title',title));
  if(copy)main.append(el('p','app-body',copy));
  root.append(header,main,el('footer','app-footer','English pilot · 3 seconds to look · 2 seconds to choose'));
  return main;
}
function stop() { token++; controller?.destroy(); controller=null; }
async function abortRun() { if(run) { const id=run.id; run=null; await api(`/api/runs/${id}/abort`,{}).catch(()=>{}); } }
function errorScreen(error) {
  stop(); abortRun();
  const main=frame('TEST INTERRUPTED','Let’s start fresh.',error?.message ?? 'Keep this window in focus for the whole round. This attempt won’t receive a score.');
  main.append(button('Try again →',intro)); main.focus({preventScroll:true});
}
function intro() {
  stop(); abortRun();
  const main=frame('TWO PRACTICE ROUNDS','First, get the rhythm.','Look for 3 seconds. The posts disappear. Choose which got more views in 2 seconds.');
  main.append(el('p','app-note','One text pair, then one image pair. You’ll see feedback after each. Neither counts toward your score.'),button('Start practice →',start));
  main.append(el('p','app-fine','Your answers and timings are saved anonymously. A browser cookie keeps repeat attempts out of the pilot comparison. No account needed.'));
  main.focus({preventScroll:true});
}
async function start() {
  stop(); const current=token;
  frame('PREPARING','One moment.','Loading your practice rounds.');
  try { const created=await api('/api/runs',{}); if(current!==token)return; run=created; await showRound(); } catch(e) { if(current===token)errorScreen(e); }
}
async function showRound() {
  controller?.destroy(); const current=token;
  frame('GET READY','One moment.','Loading the next pair.');
  try {
    const round=await api(`/api/runs/${run.id}/next`);
    if(current!==token)return;
    const main=frame(); main.classList.add('app-main--round');
    const mount=el('section','app-round'); main.append(mount);
    const practice=round.kind==='practice';
    controller=createRoundController({mount,pair:round.pair,exposureMs:3000,choiceMs:2000,
      roundLabel:practice?`Practice ${round.ordinal+1} / 2 · unscored`:`${String(round.ordinal-1).padStart(2,'0')} / 15`,
      onComplete:async result=>{
        if(current!==token)return;
        mount.replaceChildren(el('p','app-transition','Saving…'));
        try {
          const saved=await api(`/api/runs/${run.id}/answer`,{ordinal:round.ordinal,choice:result.choice,responseMs:result.responseMs,observedMs:result.observedMs});
          if(current!==token)return;
          if(practice) education(round,result,saved.feedback);
          else if(saved.complete) await results();
          else { mount.replaceChildren(el('p','app-transition',result.choice?'Choice saved.':'Time’s up.')); setTimeout(()=>{if(current===token)showRound();},500); }
        } catch(e){if(current===token)errorScreen(e);}
      },onInterrupt:info=>errorScreen(info.reason==='asset-error'?new Error('A post image couldn’t load. Please try again.'):undefined),
    });
    const ready=await controller.prepare();
    if(current!==token || !ready)return;
    await api(`/api/runs/${run.id}/open`,{ordinal:round.ordinal});
    if(current!==token)return;
    await controller.start();
  } catch(e) { if(current===token)errorScreen(e); }
}
function education(round,result,feedback) {
  controller?.destroy();
  const second=round.ordinal===1;
  const main=frame(`PRACTICE ${round.ordinal+1} / 2 · UNSCORED`,result.choice===null?'Time’s up.':feedback.correct?'You got it.':'Here’s what happened.',`The ${feedback.winner} post received more views.`);
  const pair=renderPostPair(round.pair); pair.classList.add('app-feedback-pair'); main.append(pair);
  main.append(el('p','app-note',`Left: ${feedback.views.left.toLocaleString()} views · Right: ${feedback.views.right.toLocaleString()} views`));
  main.append(el('p','app-note',second?'Next are 15 scored pairs. Trust your first impression; answers appear at the end.':'Next, try a pair with images. Look at the whole post, then choose after it disappears.'));
  main.append(button(second?'Begin the test →':'Try image practice →',showRound)); main.focus({preventScroll:true});
}
function row(name,value,detail) {
  const n=el('div','app-benchmark'); const label=el('div','app-benchmark-label'); label.append(el('span','',name),el('span','app-fine',detail));
  n.append(label,el('span','app-benchmark-value',value)); return n;
}
async function results() {
  controller?.destroy();
  const result=await api(`/api/runs/${run.id}/result`);
  const main=frame('YOUR INTERNET INSTINCT',`${result.correct} / ${result.total}`,'Pairs predicted correctly.'); main.classList.add('app-main--results');
  const comparison=el('section','app-benchmarks'); comparison.append(row('You',`${Math.round(result.correct/result.total*100)}%`,`${result.missed} unanswered`),row('Random guessing','50%','Expected accuracy'));
  main.append(comparison);
  try { const board=await api('/api/leaderboard'); comparison.append(row('Other first attempts',board.humans.count?`${Math.round(board.humans.accuracy*100)}%`:'—',`${board.humans.count} completed pilot attempts`),row('AI models','—','Evaluations coming soon')); } catch { comparison.append(row('Comparisons','—','Temporarily unavailable')); }
  main.append(el('p','app-fine',result.countedInAggregate?'Your first completed attempt in this browser contributes to the pilot comparison.':'This repeat attempt is saved but excluded from the pilot comparison.'),el('p','app-fine','This curated question set uses captured cumulative views. It is a small pilot, with no validated human percentile yet.'));
  const link=el('a','app-source','View the leaderboard →'); link.href='/leaderboard.html'; main.append(link);
  const details=el('details','app-review'); details.append(el('summary','','Review the pairs'));
  for(const [i,a] of result.answers.entries()) {
    const item=el('section','app-review-item'); item.append(el('p','app-kicker',`${i+1} · ${a.choice===null?'UNANSWERED':a.correct?'CORRECT':'INCORRECT'}`),renderPostPair(a.pair));
    for(const side of ['left','right']) { const post=a.pair[side]; const source=el('a','app-source',`${side}: ${post.views.toLocaleString()} views · Original post ↗`); source.href=post.url; source.target='_blank'; source.rel='noopener noreferrer'; item.append(source,el('br')); }
    details.append(item);
  }
  main.append(details); main.focus({preventScroll:true});
}
if(new URLSearchParams(location.search).get('view')==='test') {
  document.body.className=''; document.body.replaceChildren(root); document.title='Internet instinct — System 1 Bench'; intro();
}
