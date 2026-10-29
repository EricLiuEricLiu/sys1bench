import { createRoundController } from './components.js';
import { TIMING } from './benchmark.js';
import { api } from './api.js';
import { el, button, frame, installEnterShortcut, warningIcon, postSkeleton, rememberResult, resultUrl } from './ui.js';

let run;
let controller;
let roundHost;
let token=0;
let revealTimer;
const controllers=new Set();
const root=el('div','app-shell');
function stop() { token++;clearTimeout(revealTimer);for(const c of controllers)c.destroy();controllers.clear();controller=null;roundHost=null; }
async function abortRun() { if(run){const id=run.id;run=null;await api(`/api/runs/${id}/abort`,{}).catch(()=>{});} }
function errorScreen(error) {
  stop();abortRun();
  const main=frame(root,'TEST INTERRUPTED','Let’s start fresh.',error?.message??'Keep this window in focus for the whole round. This attempt won’t receive a score.');
  main.prepend(warningIcon());main.append(button('Try again',intro));main.focus({preventScroll:true});
}
function intro() {
  stop();abortRun();
  const main=frame(root,null,'Practice rounds','Select the post with more impressions.');main.classList.add('app-main--practice');
  main.append(postSkeleton(),button('Start practice',start));main.focus({preventScroll:true});
}
async function start() {
  stop();const current=token;
  try {
    const created=await api('/api/runs',{});if(current!==token)return;run=created;
    await displayRound(await prepareRound(current),current);
  } catch(error){if(current===token)errorScreen(error);}
}
async function prepareRound(current) {
  const round=await api(`/api/runs/${run.id}/next`);if(current!==token)return null;
  const mount=el('section','app-round');
  const active=createRoundController({mount,pair:round.pair,roundMs:TIMING.roundMs,
    roundLabel:round.kind==='practice'?`Practice ${round.ordinal+1} / 2 · unscored`:`${String(round.ordinal-1).padStart(2,'0')} / 15`,
    onDisplay:()=>{
      if(current!==token)return false;
      if(!roundHost){roundHost=frame(root);roundHost.classList.add('app-main--round');root.classList.add('app-shell--round');}
      const previous=controller;roundHost.replaceChildren(mount);controller=active;
      if(previous){previous.destroy();controllers.delete(previous);}return true;
    },
    onComplete:async answer=>{
      if(current!==token)return;
      try {
        const saved=await api(`/api/runs/${run.id}/answer`,{ordinal:round.ordinal,choice:answer.choice,responseMs:answer.responseMs,observedMs:answer.observedMs});
        if(current!==token||!active.reveal(saved.feedback))return;
        // Keep the revealed pair painted while the next pair loads and decodes.
        const next=saved.complete?null:prepareRound(current).then(value=>({value}),error=>({error}));
        revealTimer=setTimeout(async()=>{
          if(current!==token||controller!==active)return;
          try {
            if(saved.complete){rememberResult(run.id);location.assign(resultUrl(run.id));return;}
            const prepared=await next;if(prepared.error)throw prepared.error;
            await displayRound(prepared.value,current);
          }catch(error){if(current===token)errorScreen(error);}
        },TIMING.revealMs);
      }catch(error){if(current===token)errorScreen(error);}
    },
    onInterrupt:info=>errorScreen(info.reason==='asset-error'?new Error('A post image couldn’t load. Please try again.'):undefined),
  });
  controllers.add(active);
  const ready=await active.prepare();if(current!==token||!ready)return null;
  return {round,controller:active};
}
async function displayRound(prepared,current) {
  if(!prepared||current!==token)return;
  await api(`/api/runs/${run.id}/open`,{ordinal:prepared.round.ordinal});
  if(current===token)await prepared.controller.start();
}
installEnterShortcut();
if(new URLSearchParams(location.search).get('view')==='test') {
  window.addEventListener('app-error',event=>errorScreen(event.detail));
  document.body.className='';document.body.replaceChildren(root);document.title='Internet instinct — System 1 Bench';intro();
}
