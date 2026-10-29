import { api } from './api.js';
import { renderRanking } from './ranking.js';
import { el, actionLink, installEnterShortcut, lastResultUrl } from './ui.js';
const root=document.querySelector('#leaderboard');installEnterShortcut();
const actions=document.querySelector('#leaderboard-actions');
const previous=lastResultUrl();
if(previous)actions.append(actionLink('Back to your result',previous,{primary:true}));
actions.append(actionLink('Take the test','/?view=test',{secondary:Boolean(previous),primary:!previous}));
try {
  const data=await api('/api/leaderboard');root.replaceChildren(renderRanking(data,{heading:false}));
} catch {root.replaceChildren(el('p','app-note','The leaderboard is temporarily unavailable. Please try again.'));}
