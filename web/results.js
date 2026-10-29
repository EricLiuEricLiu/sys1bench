import { renderPostPair } from './components.js';
import { api } from './api.js';
import { renderRanking } from './ranking.js';
import { el, frame, actionLink, installEnterShortcut, rememberResult, warningIcon } from './ui.js';
const root=el('div','app-shell');document.body.replaceChildren(root);installEnterShortcut();
try {
  const id=new URLSearchParams(location.search).get('run');if(!/^[a-f0-9-]{36}$/.test(id??''))throw new Error('This result could not be found.');
  const main=frame(root,null,'Your result','Loading…');main.classList.add('app-main--results','app-main--ranked');
  const result=await api(`/api/runs/${id}/result`);rememberResult(id);
  main.replaceChildren(el('p','app-kicker','YOUR INTERNET INSTINCT'),el('h1','app-title','Leaderboard'));
  const rankings=el('section','app-ranking');rankings.append(el('p','app-fine','Loading rankings…'));main.append(rankings);
  const actions=el('div','app-actions');actions.append(actionLink('Retry','/?view=test',{primary:true}));main.append(actions);
  const details=el('details','app-review');details.append(el('summary','','Review the pairs'));
  for(const [i,a] of result.answers.entries()) {
    const item=el('section','app-review-item');item.append(el('p',`app-kicker ${a.choice===null?'':a.correct?'is-correct':'is-wrong'}`,`${i+1} · ${a.choice===null?'UNANSWERED':a.correct?'CORRECT':'INCORRECT'}`),renderPostPair(a.pair,{engagement:{left:a.pair.left.engagement,right:a.pair.right.engagement},selected:a.choice,sourceLinks:true}));details.append(item);
  }
  main.append(details);
  main.focus({preventScroll:true});
  api(`/api/runs/${id}/leaderboard`).then(board=>rankings.replaceWith(renderRanking(board,{heading:false}))).catch(()=>rankings.replaceChildren(el('p','app-fine',`You scored ${result.correct} / ${result.total}. Rankings are temporarily unavailable. Your result is saved.`)));

} catch(error) {
  const main=frame(root,'RESULT UNAVAILABLE','Let’s try again.',error.message);main.prepend(warningIcon());main.append(actionLink('Retry','/?view=test',{primary:true}));
}
