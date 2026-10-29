import { el } from './ui.js';

export function arrangeRankings(board) {
  const viewer=board.entries.find(entry=>entry.isYou);
  const rows=viewer?[{type:'entry',entry:viewer}]:[];
  let previous=0;
  function gap(until) {
    const count=until-previous-1-(viewer && viewer.position>previous && viewer.position<until?1:0);
    if(count>0)rows.push({type:'gap',count});
  }
  for(const entry of board.entries.filter(entry=>!entry.isYou).sort((a,b)=>a.position-b.position)) {
    gap(entry.position);rows.push({type:'entry',entry});previous=entry.position;
  }
  gap(board.totalEntries+1);
  return rows;
}

export function renderRanking(board,{heading=true}={}) {
  const section=el('section','app-ranking');
  if(heading)section.append(el('h2','i-round__heading','Leaderboard'));
  if(!board.entries.length){section.append(el('p','app-note','No completed results yet.'));return section;}
  if(board.abbreviated)section.append(el('p','app-ranking__summary',`Showing ${board.entries.length.toLocaleString('en')} of ${board.totalEntries.toLocaleString('en')} entries · all AI scores included`));
  const table=el('table','app-ranking__table');table.append(el('caption','i-sr-only',board.entries.some(entry=>entry.isYou)?'Ranked human and AI results. Your result appears first.':'Ranked human and AI results.'));
  const head=el('thead');const headings=el('tr');
  for(const title of ['Rank','Participant','Score','Accuracy']){const th=el('th','',title);th.scope='col';headings.append(th);}head.append(headings);table.append(head);
  const body=el('tbody');
  for(const row of arrangeRankings(board)) {
    const tr=el('tr',row.type==='gap'?'app-ranking__gap':row.entry.isYou?'app-ranking__you':'');
    if(row.type==='gap') { const td=el('td','',`⋯ ${row.count.toLocaleString('en')} ${row.count===1?'entry':'entries'} omitted ⋯`);td.colSpan=4;tr.append(td);body.append(tr);continue; }
    const entry=row.entry;
    const rank=el('td','app-ranking__rank',`#${entry.rank.toLocaleString('en')}`);
    const participant=el('th','app-ranking__participant');participant.scope='row';
    const label=el('div','app-ranking__label');label.append(el('span','app-ranking__name',entry.name));
    if(entry.kind==='ai'){const badge=el('span','app-ranking__tag','AI');badge.setAttribute('aria-label','AI model');label.append(badge);}
    participant.append(label);
    if(entry.isYou && board.viewer?.isRepeat)participant.append(el('small','app-ranking__detail','Repeat attempt'));
    if(entry.kind==='ai' && entry.unanswered){const invalid=entry.failures?.invalid??0;participant.append(el('small','app-ranking__detail',invalid===entry.unanswered?`${invalid} invalid ${invalid===1?'answer':'answers'}`:`${entry.unanswered} missing ${entry.unanswered===1?'answer':'answers'}`));}
    tr.append(rank,participant,el('td','app-ranking__score',`${entry.correct} / ${entry.total}`),el('td','app-ranking__accuracy',`${Math.round(entry.correct/entry.total*100)}%`));
    if(entry.isYou)tr.setAttribute('aria-current','true');body.append(tr);
  }
  table.append(body);section.append(table);
  section.append(el('p','app-ranking__note','Equal scores share a rank. Human entries are anonymous first attempts.'));
  if(board.viewer?.isRepeat)section.append(el('p','app-ranking__note','This repeat is compared here; the shared leaderboard keeps your first attempt.'));
  if(board.models.length)section.append(el('p','app-ranking__note','We use selected leading models with reasoning disabled. Models requiring reasoning are excluded.'));
  const about=el('details','app-ranking__about');about.append(el('summary','','About these scores'));
  if(board.models.length)about.append(el('p','','AI models answer independently with reasoning disabled. People receive feedback between rounds.'));
  if(board.models.some(model=>model.unanswered))about.append(el('p','','Invalid or missing answers count as incorrect.'));
  for(const model of board.models)if(model.inputNotes)about.append(el('p','',`${model.name}: ${model.inputNotes}`));
  about.append(el('p','',`Question set ${board.datasetVersion} · Random guessing: 50%.`));section.append(about);
  return section;
}
