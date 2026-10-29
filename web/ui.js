export const el = (tag, cls, text) => { const n=document.createElement(tag); if(cls)n.className=cls; if(text!=null)n.textContent=text; return n; };
export function shortcutLabel(target, label, shortcut='Enter') { target.append(el('span','',label),el('kbd','i-key',shortcut)); return target; }
export function button(label, action, {secondary=false, primary=true}={}) {
  const n=shortcutLabel(el('button',`i-button${secondary?' i-button--secondary':''}`),label); n.type='button';
  if(primary){n.dataset.shortcut='Enter';n.setAttribute('aria-keyshortcuts','Enter');}
  n.addEventListener('click',()=>{if(n.disabled)return;n.disabled=true;Promise.resolve().then(action).catch(error=>{n.disabled=false;window.dispatchEvent(new CustomEvent('app-error',{detail:error}));});});
  return n;
}
export function actionLink(label, href, {secondary=false, primary=false, shortcut='Enter'}={}) {
  const n=shortcutLabel(el('a',`i-button${secondary?' i-button--secondary':''}`),label,shortcut); n.href=href; if(primary){n.dataset.shortcut=shortcut;n.setAttribute('aria-keyshortcuts',shortcut);} return n;
}
export function frame(root,kicker,title,copy) {
  root.replaceChildren();root.className='app-shell';
  const header=el('header','app-header'); const home=el('a','app-brand','System 1 Bench');home.href='/';header.append(home,el('span','app-mono','INTERNET INSTINCT'));
  const main=el('main','app-main');main.tabIndex=-1;main.id='test-main';
  if(kicker)main.append(el('p','app-kicker',kicker));if(title)main.append(el('h1','app-title',title));if(copy)main.append(el('p','app-body',copy));root.append(header,main);return main;
}
export function installKeyboardShortcuts() {
  document.addEventListener('keydown',event=>{
    if(event.repeat||event.defaultPrevented||event.metaKey||event.ctrlKey||event.altKey)return;
    if(event.target.closest?.('input,textarea,select,[contenteditable]:not([contenteditable="false"])'))return;
    if(event.key==='Enter'&&event.target.closest?.('a,button,summary,[role="button"]'))return;
    const target=[...document.querySelectorAll('[data-shortcut]:not(:disabled)')].find(node=>node.dataset.shortcut.toLowerCase()===event.key.toLowerCase());
    if(target){event.preventDefault();target.click();}
  });
}
export function warningIcon() {
  const wrap=el('div','app-warning');wrap.setAttribute('aria-hidden','true');
  wrap.innerHTML='<svg viewBox="0 0 64 64" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M28.6 9.8 5.7 49.4A4 4 0 0 0 9.2 55h45.6a4 4 0 0 0 3.5-5.6L35.4 9.8a4 4 0 0 0-6.8 0Z"/><path d="M32 23v14m0 9h.01"/></svg>';return wrap;
}
export function postSkeleton() {
  const post=el('div','i-post-skeleton');post.setAttribute('aria-hidden','true');
  post.innerHTML='<div class="i-post-skeleton__header"><span class="i-post-skeleton__avatar"></span><span class="i-post-skeleton__identity"><span></span><span></span></span><span class="i-post-skeleton__mark"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26L22.827 21.75h-6.657l-5.214-6.817-5.966 6.817H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231L18.244 2.25Zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77Z"/></svg></span></div><div class="i-post-skeleton__lines"><span></span><span></span><span></span></div><div class="i-post-skeleton__actions"><span></span><span></span><span></span><span></span></div>';return post;
}
export function resultUrl(id) { if(!/^[a-f0-9-]{36}$/.test(id??''))throw new Error('Result not found.');return `/results?run=${id}`; }
export function rememberResult(id) { try{sessionStorage.setItem('s1b:last-result',resultUrl(id));}catch{} }
export function lastResultUrl() { try{const value=sessionStorage.getItem('s1b:last-result');return /^\/results\?run=[a-f0-9-]{36}$/.test(value??'')?value:null;}catch{return null;} }
