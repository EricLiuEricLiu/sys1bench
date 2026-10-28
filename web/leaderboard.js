const root=document.querySelector('#leaderboard');
const node=(tag,text,cls)=>{const n=document.createElement(tag);n.textContent=text;if(cls)n.className=cls;return n;};
try {
  const response=await fetch('/api/leaderboard'); if(!response.ok)throw new Error('Could not load results.');
  const data=await response.json(); root.replaceChildren();
  root.append(node('h2','Humans','i-round__heading'),node('p',data.humans.count?`${data.humans.count} first attempts · ${Math.round(data.humans.accuracy*100)}% average accuracy`:'No completed attempts yet. Be the first.','app-note'));
  if(data.humans.count) {
    for(const entry of data.humans.distribution) { const row=node('div','','app-benchmark'); row.append(node('span',`${entry.correct} / 15`),node('span',`${entry.count} ${entry.count===1?'attempt':'attempts'}`)); root.append(row); }
  }
  root.append(node('h2','AI models','i-round__heading'),node('p','Model evaluations are being prepared. Results will appear after real runs.','app-note'),node('p',`Question set ${data.datasetVersion} · Random guessing: 50%`,'app-fine'));
} catch(e) { root.replaceChildren(node('p','The leaderboard is temporarily unavailable. Please try again.','app-note')); }
