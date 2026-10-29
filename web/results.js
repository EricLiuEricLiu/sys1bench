import { renderPostPair } from './components.js';
import { api } from './api.js';
import { el, frame, actionLink, installEnterShortcut, rememberResult, warningIcon } from './ui.js';
const root=el('div','app-shell');document.body.replaceChildren(root);installEnterShortcut();
function row(name,value,detail) { const n=el('div','app-benchmark');const label=el('div','app-benchmark-label');label.append(el('span','',name));if(detail)label.append(el('span','app-fine',detail));n.append(label,el('span','app-benchmark-value',value));return n; }
try {
  const id=new URLSearchParams(location.search).get('run');if(!/^[a-f0-9-]{36}$/.test(id??''))throw new Error('This result could not be found.');
  const main=frame(root,null,'Your result','Loading…');main.classList.add('app-main--results');
  const result=await api(`/api/runs/${id}/result`);rememberResult(id);
  main.replaceChildren(el('p','app-kicker','YOUR INTERNET INSTINCT'),el('h1','app-title',`${result.correct} / ${result.total}`),el('p','app-body','Pairs predicted correctly.'));
  const comparison=el('section','app-benchmarks');comparison.append(row('You',`${Math.round(result.correct/result.total*100)}%`),row('Random guessing','50%','Expected accuracy'));main.append(comparison);
  const actions=el('div','app-actions');actions.append(actionLink('View the leaderboard','/leaderboard',{primary:true}),actionLink('Retry','/?view=test',{secondary:true}));main.insertBefore(actions,comparison);
  const details=el('details','app-review');details.append(el('summary','','Review the pairs'));
  for(const [i,a] of result.answers.entries()) {
    const item=el('section','app-review-item');item.append(el('p',`app-kicker ${a.choice===null?'':a.correct?'is-correct':'is-wrong'}`,`${i+1} · ${a.choice===null?'UNANSWERED':a.correct?'CORRECT':'INCORRECT'}`),renderPostPair(a.pair,{engagement:{left:a.pair.left.engagement,right:a.pair.right.engagement},selected:a.choice,sourceLinks:true}));details.append(item);
  }
  main.append(details,el('p','app-fine',result.countedInAggregate?'Your first completed attempt contributes to the pilot comparison.':'Repeat attempts are saved and excluded from the pilot comparison.'));
  main.focus({preventScroll:true});
  api('/api/leaderboard').then(board=>{if(board.cohort!==result.cohort)return;comparison.append(row('Other first attempts',board.humans.count?`${Math.round(board.humans.accuracy*100)}%`:'—',`${board.humans.count} completed pilot ${board.humans.count===1?'attempt':'attempts'}`));for(const model of board.models)comparison.append(row(model.name,`${Math.round(model.correct/model.total*100)}%`,`${model.correct} / ${model.total}`));if(board.models.length)comparison.append(el('p','app-fine','AI models answer independently with thinking disabled. People receive feedback between rounds.'));}).catch(()=>{});
} catch(error) {
  const main=frame(root,'RESULT UNAVAILABLE','Let’s try again.',error.message);main.prepend(warningIcon());main.append(actionLink('Retry','/?view=test',{primary:true}));
}
