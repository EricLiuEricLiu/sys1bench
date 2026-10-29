import { api } from './api.js';
import { el, actionLink, installEnterShortcut, lastResultUrl } from './ui.js';
const root=document.querySelector('#leaderboard');installEnterShortcut();
const actions=document.querySelector('#leaderboard-actions');
const previous=lastResultUrl();
if(previous)actions.append(actionLink('Back to your result',previous,{primary:true}));
actions.append(actionLink('Take the test','/?view=test',{secondary:Boolean(previous),primary:!previous}));
try {
  const data=await api('/api/leaderboard');root.replaceChildren();
  root.append(el('h2','i-round__heading','Humans'),el('p','app-note',data.humans.count?`${data.humans.count} first ${data.humans.count===1?'attempt':'attempts'} · ${Math.round(data.humans.accuracy*100)}% average accuracy`:'No completed attempts yet. Be the first.'));
  for(const entry of data.humans.distribution){const row=el('div','app-benchmark');row.append(el('span','',`${entry.correct} / 15`),el('span','',`${entry.count} ${entry.count===1?'attempt':'attempts'}`));root.append(row);}
  root.append(el('h2','i-round__heading','AI models'));
  if(data.models.length){
    const table=el('table','app-models');const head=el('thead');const headings=el('tr');for(const name of ['Model','Correct','Accuracy'])headings.append(el('th','',name));head.append(headings);table.append(head);
    const body=el('tbody');for(const model of data.models){const row=el('tr');const label=el('th','',model.name);label.scope='row';row.append(label,el('td','',`${model.correct} / ${model.total}`),el('td','',`${Math.round(model.correct/model.total*100)}%`));body.append(row);}table.append(body);root.append(table);
    for(const model of data.models)if(model.inputNotes)root.append(el('p','app-fine',`${model.name}: ${model.inputNotes}`));
    root.append(el('p','app-fine','Models answer independently with thinking disabled. Humans see feedback between questions. These are different conditions on the same pilot question set.'));
  } else root.append(el('p','app-note','Model evaluations are being prepared.'));
  root.append(el('p','app-fine',`Question set ${data.datasetVersion} · Random guessing: 50%`));
} catch {root.replaceChildren(el('p','app-note','The leaderboard is temporarily unavailable. Please try again.'));}
