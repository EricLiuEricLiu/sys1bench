import { TIMING } from './benchmark.js';
import { preloadPairAssets, resolvePostMediaUrl, resolveAvatarUrl } from './media.js';
export { preloadPairAssets };

const clock = () => performance.now();

const postIcons = {
  x: '<path fill="currentColor" d="M18.244 2.25h3.308l-7.227 8.26L22.827 21.75h-6.657l-5.214-6.817-5.966 6.817H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231L18.244 2.25Zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77Z"/>',
  heart: '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78Z"/>',
  reply: '<path d="M20.8 11.3c0 4.5-3.9 8-8.8 8H5l-3.2 2v-6.6a7.5 7.5 0 0 1-1-3.4c0-4.5 3.9-8 8.8-8h2.4c4.9 0 8.8 3.5 8.8 8Z" transform="translate(1 0) scale(.94)"/>',
  repost: '<path d="m2 9 3-3 3 3M5 6v9a3 3 0 0 0 3 3h4"/><path d="m22 15-3 3-3-3M19 18V9a3 3 0 0 0-3-3h-4"/>',
  impressions: '<path d="M4 20V10"/><path d="M9 20V4"/><path d="M14 20V7"/><path d="M19 20V13"/>',
  link: '<path d="m9.5 14.5 5-5M7 15l-1.1 1.1a3.5 3.5 0 1 1-5-5L5 7a3.5 3.5 0 0 1 5 0m4 2 1.1-1.1a3.5 3.5 0 1 1 5 5L16 17a3.5 3.5 0 0 1-5 0" transform="translate(1 0)"/>',
};

function postIcon(name) {
  const icon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  icon.setAttribute('viewBox', '0 0 24 24');
  icon.setAttribute('fill', 'none');
  icon.setAttribute('stroke', name === 'x' ? 'none' : 'currentColor');
  icon.setAttribute('stroke-width', '1.7');
  icon.setAttribute('stroke-linecap', 'round');
  icon.setAttribute('stroke-linejoin', 'round');
  icon.setAttribute('aria-hidden', 'true');
  icon.innerHTML = postIcons[name];
  return icon;
}

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

export function renderProgress({ completed = 0, total = 15, current = false } = {}) {
  const progress = node('div', 'i-progress');
  progress.setAttribute('role', 'progressbar');
  progress.setAttribute('aria-label', 'Test progress');
  progress.setAttribute('aria-valuemin', '0');
  progress.setAttribute('aria-valuemax', String(total));
  progress.setAttribute('aria-valuenow', String(completed));
  for (let index = 0; index < total; index += 1) {
    const state = index < completed ? ' is-complete' : index === completed && current ? ' is-current' : '';
    const step = node('span', `i-progress__step${state}`);
    step.setAttribute('aria-hidden', 'true');
    progress.append(step);
  }
  return progress;
}

export function renderPostPair(pair, { assets, assetBaseUrl, resolveAsset, onChoose, engagement, selected, sourceLinks = false } = {}) {
  const row = node('div', 'i-pair');
  row.setAttribute('aria-label', 'Two X posts');
  for (const side of ['left', 'right']) {
    const stimulus = pair[side];
    const post = node('article', 'i-post');
    post.dataset.side = side;
    post.setAttribute('aria-label', `Post by ${stimulus.author?.name || 'unknown author'}`);
    if (onChoose) {
      post.setAttribute('role', 'button');
      post.setAttribute('aria-label', `Select post by ${stimulus.author?.name || 'unknown author'}`);
      post.tabIndex = 0;
      post.classList.add('i-post--selectable');
      post.addEventListener('click', () => onChoose(side));
      post.addEventListener('keydown', event => {
        if (!event.repeat && ['Enter', ' '].includes(event.key)) { event.preventDefault(); onChoose(side); }
      });
    }
    const header = node('div', 'i-post__header');
    const avatar = node('span', 'i-post__avatar');
    avatar.setAttribute('aria-hidden', 'true');
    const avatarImage = assets ? assets[side].avatar : null;
    const avatarSrc = resolveAvatarUrl(stimulus.author, { resolveAsset, side, post: stimulus });
    if (avatarImage) {
      avatarImage.alt = '';
      avatar.append(avatarImage);
    } else if (!assets && avatarSrc) {
      const image = document.createElement('img');
      image.alt = '';
      image.referrerPolicy = 'no-referrer';
      image.addEventListener('error', () => image.remove(), { once: true });
      image.src = avatarSrc;
      avatar.append(image);
    }
    const identity = node('div', 'i-post__identity');
    identity.append(node('span', 'i-post__name', stimulus.author?.name || 'Unknown author'));
    if (stimulus.author?.handle) identity.append(node('span', 'i-post__handle', `@${stimulus.author.handle.replace(/^@/, '')}`));
    const linkToSource = sourceLinks && /^https:\/\/(?:www\.)?(?:x\.com|twitter\.com)\//.test(stimulus.url ?? '');
    const mark = node(linkToSource ? 'a' : 'span', 'i-post__x');
    if (linkToSource) { mark.href=stimulus.url;mark.target='_blank';mark.rel='noopener noreferrer';mark.setAttribute('aria-label', `Open original post by ${stimulus.author?.name || 'author'} on X`); }
    mark.append(postIcon('x'));
    header.append(avatar, identity, mark);
    post.append(header);
    post.append(node('p', 'i-post__text', stimulus.displayText ?? stimulus.text));
    if (stimulus.media?.length) {
      const attachments = node('div', 'i-post__media');
      stimulus.media.forEach((media, index) => {
        const image = assets ? assets[side].images[index] : document.createElement('img');
        image.className = 'i-post__image';
        image.alt = media.alt || 'Attached image';
        if (!assets) {
          image.referrerPolicy = 'no-referrer';
          image.src = resolvePostMediaUrl(media, { assetBaseUrl, resolveAsset, side, post: stimulus, index });
        }
        if (media.width > 0 && media.height > 0) {
          image.width = media.width;
          image.height = media.height;
        }
        attachments.append(image);
      });
      post.append(attachments);
    }
    post.append(renderPostMetrics(engagement?.[side]));
    const item = node('div', 'i-pair__item');
    if (selected !== undefined) item.append(node('p', 'i-post__selection', selected === side ? 'You selected' : '\u00a0'));
    item.append(post);row.append(item);
  }
  return row;
}

const metricLabels = { replies: 'Replies', reposts: 'Reposts', likes: 'Likes', impressions: 'Impressions' };
const metricIcons = { replies: 'reply', reposts: 'repost', likes: 'heart', impressions: 'impressions' };
const compactCount = new Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 });

export function renderPostMetrics(engagement) {
  const actions = node('div', 'i-post__actions');
  actions.setAttribute('aria-label', engagement ? 'Captured engagement' : 'Engagement hidden until you answer');
  for (const [metric, label] of Object.entries(metricLabels)) {
    const action = node('span', `i-post__action i-post__action--${metric}`);
    action.dataset.metric = metric;
    action.append(postIcon(metricIcons[metric]));
    const value = engagement?.[metric];
    if (Number.isSafeInteger(value) && value >= 0) {
      action.append(node('span', 'i-post__count', compactCount.format(value)));
      action.title = `${value.toLocaleString('en')} ${label.toLowerCase()}`;
      action.setAttribute('aria-label', action.title);
    } else {
      action.setAttribute('aria-label', `${label} hidden`);
    }
    actions.append(action);
  }
  return actions;
}

export function renderBenchmarks({ accuracy = null, human = null, ai = null } = {}) {
  const table = node('table', 'i-benchmarks');
  const caption = node('caption', 'i-sr-only', 'Benchmark comparison');
  table.append(caption);
  const body = document.createElement('tbody');
  for (const [label, score, pending] of [
    ['You', accuracy, 'Complete the test'],
    ['Humans', human, 'Awaiting real runs'],
    ['AI', ai, 'Not evaluated yet'],
    ['Random guessing', 50, ''],
  ]) {
    const row = document.createElement('tr');
    const heading = node('th', '', label);
    heading.scope = 'row';
    const value = node('td', score === null ? 'i-benchmarks__pending' : 'i-mono', score === null ? pending : `${Math.round(score)}%`);
    row.append(heading, value);
    body.append(row);
  }
  table.append(body);
  return table;
}

export function createRoundController({
  mount,
  pair,
  roundMs = TIMING.roundMs,
  roundLabel = 'Practice',
  assetBaseUrl,
  resolveAsset,
  assetTimeoutMs = 12000,
  avatarTimeoutMs = 3000,
  onComplete = () => {},
  onInterrupt = () => {},
  onPhaseChange = () => {},
  onDisplay = () => {},
}) {
  if (!(mount instanceof HTMLElement)) throw new TypeError('mount must be an HTMLElement');
  if (!['left', 'right'].every(side => typeof (pair?.[side]?.displayText ?? pair?.[side]?.text) === 'string')) throw new TypeError('pair needs left/right displayText or text');
  if (!(roundMs > 0)) throw new TypeError('Round duration must be positive');
  let phase = 'idle';
  let deadline = 0;
  let exposedAt = 0;
  let observedMs = 0;
  let selected = null;
  let frameId = 0;
  let deadlineTimer = 0;
  let destroyed = false;
  let preparedAssets;
  let preparation;
  let startPromise;
  let startRequested = false;
  let paintResolve;
  const assetAbort = new AbortController();
  const content = node('div', 'i-round__content');
  const timer = node('div', 'i-timer');
  timer.setAttribute('aria-hidden', 'true');
  const remaining = node('span', 'i-timer__number', `${(roundMs / 1000).toFixed(1)}s`);
  timer.append(remaining);
  const track = node('div', 'i-timer__track');
  const fill = node('div', 'i-timer__fill');
  track.append(fill);
  const announcement = node('div', 'i-sr-only');
  announcement.setAttribute('role', 'status');
  announcement.setAttribute('aria-live', 'polite');
  mount.replaceChildren(node('p', 'i-eyebrow', roundLabel), node('h2', 'i-round__heading', 'Which post got more impressions?'), content, timer, track, announcement);
  mount.classList.add('i-scope', 'i-round');

  function clearTimers() {
    cancelAnimationFrame(frameId);
    clearTimeout(deadlineTimer);
    if (paintResolve) { paintResolve(false); paintResolve = null; }
  }
  function setPhase(next) {
    phase = next;
    mount.dataset.phase = phase;
    onPhaseChange(phase);
  }
  function showMessage(title, description) {
    const message = node('div', 'i-round__message');
    message.append(node('h3', '', title), node('p', '', description));
    content.replaceChildren(message);
    fill.style.transform = 'scaleX(0)';
    remaining.textContent = '—';
  }
  function finish(choice) {
    if (destroyed || phase !== 'active') return;
    const now = clock();
    if (now >= deadline) choice = null;
    observedMs = Math.max(0, now - exposedAt);
    selected = choice;
    clearTimers();
    setPhase('saving');
    if (destroyed) return;
    for (const post of content.querySelectorAll('.i-post')) {
      post.setAttribute('aria-disabled', 'true');
      post.removeAttribute('role');
      post.setAttribute('aria-label', `Post by ${pair[post.dataset.side].author?.name || 'unknown author'}`);
      post.classList.remove('i-post--selectable');
      post.tabIndex = -1;
      post.classList.toggle('is-selected', post.dataset.side === choice);
    }
    announcement.textContent = choice === null ? 'Time is up. Revealing counts.' : 'Choice saved. Revealing counts.';
    onComplete({ choice, responseMs: choice === null ? null : observedMs, observedMs, assetLoadMs: preparedAssets?.loadMs ?? 0, avatarFallbacks: preparedAssets?.avatarFallbacks ?? 0, contentImages: preparedAssets?.contentImages ?? 0, pairIds: { left: pair.left.id ?? null, right: pair.right.id ?? null } });
  }
  function reveal(feedback) {
    if (destroyed || phase !== 'saving') return false;
    for (const side of ['left', 'right']) {
      const engagement = feedback?.engagement?.[side];
      if (!Object.keys(metricLabels).every(key => Number.isSafeInteger(engagement?.[key]) && engagement[key] >= 0)) throw new TypeError('Verified engagement counts are required');
      const post = content.querySelector(`[data-side="${side}"]`);
      post.querySelector('.i-post__actions').replaceWith(renderPostMetrics(engagement));
      post.classList.toggle('is-winner', side === feedback.winner);
    }
    timer.classList.add('is-feedback');
    remaining.textContent = selected === null ? 'Time’s up' : feedback.correct ? 'Correct' : 'Wrong';
    timer.classList.toggle('is-correct', selected !== null && feedback.correct);
    timer.classList.toggle('is-wrong', selected !== null && !feedback.correct);
    fill.style.transform = 'scaleX(0)';
    announcement.textContent = `${remaining.textContent}. Counts revealed. The next pair starts shortly.`;
    setPhase('reveal');
    return true;
  }
  function updateTimer() {
    if (destroyed || phase !== 'active') return;
    const milliseconds = Math.max(0, deadline - clock());
    fill.style.transform = `scaleX(${Math.min(1, milliseconds / roundMs)})`;
    remaining.textContent = `${(Math.ceil(milliseconds / 100) / 10).toFixed(1)}s`;
    if (milliseconds === 0) { finish(null); return; }
    frameId = requestAnimationFrame(updateTimer);
  }
  function interrupt(reason, error) {
    if (destroyed || ['interrupted', 'saving', 'reveal'].includes(phase)) return;
    if (!error && phase !== 'active' && !startRequested) return;
    const interruptedPhase = phase;
    const seenMs = phase === 'active' ? clock() - exposedAt : observedMs;
    clearTimers();
    assetAbort.abort();
    setPhase('interrupted');
    if (destroyed) return;
    showMessage(error ? 'A post image couldn’t load.' : 'Round interrupted.', 'Please start a fresh round.');
    onInterrupt({ reason, phase: interruptedPhase, observedMs: seenMs, ...(error ? { errorCode: error.code || 'asset-error', assetKind: error.kind, side: error.side, assetIndex: error.index } : {}) });
  }
  function prepare() {
    if (destroyed || phase === 'interrupted') return Promise.resolve(null);
    if (preparedAssets) return Promise.resolve(preparedAssets);
    if (preparation) return preparation;
    setPhase('loading');
    if (destroyed) return Promise.resolve(null);
    showMessage('Loading posts…', 'Preparing images and avatars.');
    preparation = preloadPairAssets(pair, { assetBaseUrl, resolveAsset, timeoutMs: assetTimeoutMs, avatarTimeoutMs, signal: assetAbort.signal })
      .then(assets => {
        if (destroyed || phase === 'interrupted') return null;
        preparedAssets = assets;
        setPhase('ready');
        if (destroyed) return null;
        showMessage('Ready.', 'Select the post with more impressions.');
        return assets;
      })
      .catch(error => {
        if (!destroyed && phase !== 'interrupted') interrupt('asset-error', error);
        return null;
      });
    return preparation;
  }
  async function beginRound() {
    const assets = await prepare();
    if (!assets || destroyed || phase === 'interrupted') return false;
    if (document.hidden || !document.hasFocus()) { interrupt(document.hidden ? 'visibility' : 'blur'); return false; }
    content.style.visibility = 'hidden';
    content.replaceChildren(renderPostPair(pair, { assets, assetBaseUrl, resolveAsset, onChoose: finish }));
    return new Promise(resolve => {
      paintResolve = resolve;
      frameId = requestAnimationFrame(() => {
        paintResolve = null;
        if (destroyed || phase === 'interrupted') { resolve(false); return; }
        if (document.hidden || !document.hasFocus()) { interrupt(document.hidden ? 'visibility' : 'blur'); resolve(false); return; }
        if (onDisplay() === false || destroyed) { resolve(false); return; }
        content.style.visibility = '';
        announcement.textContent = `Select the post with more impressions. You have ${roundMs / 1000} seconds.`;
        exposedAt = clock();
        deadline = exposedAt + roundMs;
        setPhase('active');
        if (destroyed) { resolve(false); return; }
        fill.style.transform = 'scaleX(1)';
        remaining.textContent = `${(roundMs / 1000).toFixed(1)}s`;
        deadlineTimer = setTimeout(() => finish(null), roundMs);
        frameId = requestAnimationFrame(updateTimer);
        resolve(true);
      });
    });
  }
  function onKey(event) {
    if (event.repeat || phase !== 'active' || destroyed) return;
    const choice = event.key === 'ArrowLeft' ? 'left' : event.key === 'ArrowRight' ? 'right' : null;
    if (choice) { event.preventDefault(); finish(choice); }
  }
  const onVisibility = () => { if (document.hidden) interrupt('visibility'); };
  const onBlur = () => interrupt('blur');
  document.addEventListener('keydown', onKey);
  document.addEventListener('visibilitychange', onVisibility);
  window.addEventListener('blur', onBlur);
  showMessage('Ready.', `Select a post within ${roundMs / 1000} seconds.`);
  mount.dataset.phase = 'idle';
  return {
    prepare,
    start() {
      if (destroyed || !['idle', 'loading', 'ready'].includes(phase)) return Promise.resolve(false);
      if (startPromise) return startPromise;
      startRequested = true;
      startPromise = beginRound();
      return startPromise;
    },
    reveal,
    destroy() {
      destroyed = true;
      clearTimers();
      assetAbort.abort();
      content.replaceChildren();
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('blur', onBlur);
    },
    getState() { return { phase, deadline, observedMs, assetLoadMs: preparedAssets?.loadMs ?? null, avatarFallbacks: preparedAssets?.avatarFallbacks ?? null }; },
  };
}
