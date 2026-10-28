import { TIMING } from './benchmark.js';
import { preloadPairAssets, resolvePostMediaUrl, resolveAvatarUrl } from './media.js';
export { preloadPairAssets };

const clock = () => performance.now();

const postIcons = {
  x: '<path fill="currentColor" d="M18.244 2.25h3.308l-7.227 8.26L22.827 21.75h-6.657l-5.214-6.817-5.966 6.817H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231L18.244 2.25Zm-1.161 17.52h1.833L7.084 4.126H5.117L17.083 19.77Z"/>',
  heart: '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78L12 21.23l8.84-8.84a5.5 5.5 0 0 0 0-7.78Z"/>',
  reply: '<path d="M20.8 11.3c0 4.5-3.9 8-8.8 8H5l-3.2 2v-6.6a7.5 7.5 0 0 1-1-3.4c0-4.5 3.9-8 8.8-8h2.4c4.9 0 8.8 3.5 8.8 8Z" transform="translate(1 0) scale(.94)"/>',
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

export function renderPostPair(pair, { assets, assetBaseUrl, resolveAsset } = {}) {
  const row = node('div', 'i-pair');
  row.setAttribute('aria-label', 'Two X posts');
  for (const side of ['left', 'right']) {
    const stimulus = pair[side];
    const post = node('article', 'i-post');
    post.setAttribute('aria-label', `${side} post`);
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
    const mark = node('span', 'i-post__x');
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
    const actions = node('div', 'i-post__actions');
    actions.setAttribute('aria-hidden', 'true');
    for (const name of ['heart', 'reply', 'link']) {
      const action = node('span', `i-post__action i-post__action--${name}`);
      action.append(postIcon(name));
      actions.append(action);
    }
    post.append(actions);
    post.append(node('span', 'i-post__position', side === 'left' ? 'Left' : 'Right'));
    row.append(post);
  }
  return row;
}

export function renderChoices(onChoose) {
  const row = node('div', 'i-pair');
  row.setAttribute('role', 'group');
  row.setAttribute('aria-label', 'Which post gets more views?');
  for (const side of ['left', 'right']) {
    const button = node('button', 'i-choice');
    button.type = 'button';
    button.dataset.choice = side;
    button.setAttribute('aria-label', `${side === 'left' ? 'Left' : 'Right'} post gets more views`);
    button.append(node('span', 'i-choice__label', side === 'left' ? '← Left' : 'Right →'));
    button.append(node('span', 'i-choice__hint', side === 'left' ? 'Press ←' : 'Press →'));
    button.addEventListener('click', () => onChoose(side));
    row.append(button);
  }
  return row;
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

export function renderPracticeFeedback({ current = 1, total = 2, choice, winner, leftViews, rightViews, continueLabel, onContinue }) {
  if (!['left', 'right'].includes(winner)) throw new TypeError('Practice feedback requires a verified winner');
  const panel = node('div', 'i-practice-feedback');
  panel.setAttribute('role', 'status');
  panel.append(node('p', 'i-eyebrow', `Practice ${current} of ${total} · Unscored`));
  panel.append(node('h3', '', choice === null ? 'Time’s up.' : choice === winner ? 'Correct.' : 'Not this time.'));
  panel.append(node('p', '', `The ${winner} post had more views at collection.`));
  if ([leftViews, rightViews].every(value => Number.isSafeInteger(value) && value >= 0)) {
    panel.append(node('p', 'i-practice-feedback__counts', `Left: ${leftViews.toLocaleString()} views · Right: ${rightViews.toLocaleString()} views`));
  }
  panel.append(node('p', 'i-practice-feedback__note', current === 1 ? 'The posts disappear after six seconds. Then you have four seconds to choose.' : 'Practice doesn’t count toward your score. Scored answers are revealed at the end.'));
  if (onContinue) {
    const next = node('button', 'i-button', continueLabel || (current < total ? 'Next practice round →' : 'Finish practice →'));
    next.type = 'button';
    let continued = false;
    next.addEventListener('click', () => {
      if (continued) return;
      continued = true;
      next.disabled = true;
      onContinue();
    });
    panel.append(next);
  }
  return panel;
}

export function createRoundController({
  mount,
  pair,
  exposureMs = TIMING.exposureMs,
  choiceMs = TIMING.decisionMs,
  roundLabel = 'Practice',
  assetBaseUrl,
  resolveAsset,
  assetTimeoutMs = 12000,
  avatarTimeoutMs = 3000,
  onComplete = () => {},
  onInterrupt = () => {},
  onPhaseChange = () => {},
}) {
  if (!(mount instanceof HTMLElement)) throw new TypeError('mount must be an HTMLElement');
  if (!['left', 'right'].every(side => typeof (pair?.[side]?.displayText ?? pair?.[side]?.text) === 'string')) throw new TypeError('pair needs left/right displayText or text');
  if (!(exposureMs > 0) || !(choiceMs > 0)) throw new TypeError('Round durations must be positive');
  let phase = 'idle';
  let deadline = 0;
  let exposedAt = 0;
  let chosenAt = 0;
  let observedMs = 0;
  let frameId = 0;
  let deadlineTimer = 0;
  let destroyed = false;
  let preparedAssets;
  let preparation;
  let startPromise;
  let startRequested = false;
  let paintResolve;
  const assetAbort = new AbortController();
  let fill;
  let remaining;
  let instruction;
  let content;
  let announcement;

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

  function paintFrame() {
    mount.replaceChildren();
    mount.classList.add('i-scope', 'i-round');
    const topline = node('div', 'i-round__topline');
    topline.append(node('p', 'i-eyebrow', roundLabel));
    const timer = node('div', 'i-timer');
    timer.setAttribute('aria-hidden', 'true');
    const track = node('div', 'i-timer__track');
    fill = node('div', 'i-timer__fill');
    track.append(fill);
    remaining = node('span', 'i-timer__number', `${(exposureMs / 1000).toFixed(1)}s`);
    timer.append(remaining);
    const heading = node('h2', 'i-round__heading', 'Which post gets more views?');
    instruction = node('p', 'i-round__instruction', 'Get ready.');
    const phaseRow = node('div', 'i-round__phase');
    phaseRow.append(instruction, timer);
    content = node('div');
    const footer = node('div', 'i-round__bottomline');
    footer.append(node('span', '', 'Followers and engagement are hidden.'));
    footer.append(node('span', '', 'Trust your first impression.'));
    announcement = node('div', 'i-sr-only');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    mount.append(topline, heading, phaseRow, content, footer, track, announcement);
  }

  function showMessage(title, description) {
    content.style.visibility = '';
    const pairHeight = content.querySelector('.i-pair')?.getBoundingClientRect().height;
    const message = node('div', 'i-round__message');
    if (pairHeight) message.style.minHeight = `${pairHeight}px`;
    message.append(node('h3', '', title), node('p', '', description));
    content.replaceChildren(message);
    fill.style.transform = 'scaleX(0)';
    remaining.textContent = '—';
  }

  function finish(choice) {
    if (destroyed || phase !== 'choice') return;
    const now = clock();
    if (now >= deadline) choice = null;
    const responseMs = choice === null ? null : Math.max(0, now - chosenAt);
    clearTimers();
    setPhase('complete');
    if (destroyed) return;
    instruction.textContent = choice === null ? 'The answer window has closed.' : 'Keep that first impression.';
    showMessage(choice === null ? 'Time’s up.' : 'Choice recorded.', choice === null ? 'This round counts as unanswered.' : `${choice === 'left' ? 'Left' : 'Right'} post selected.`);
    onComplete({ choice, responseMs, observedMs, assetLoadMs: preparedAssets?.loadMs ?? 0, avatarFallbacks: preparedAssets?.avatarFallbacks ?? 0, contentImages: preparedAssets?.contentImages ?? 0, pairIds: { left: pair.left.id ?? null, right: pair.right.id ?? null } });
  }

  function updateTimer() {
    if (destroyed || !['exposure', 'choice'].includes(phase)) return;
    const duration = phase === 'exposure' ? exposureMs : choiceMs;
    const milliseconds = Math.max(0, deadline - clock());
    fill.style.transform = `scaleX(${Math.min(1, milliseconds / duration)})`;
    remaining.textContent = `${(Math.ceil(milliseconds / 100) / 10).toFixed(1)}s`;
    if (milliseconds === 0) {
      if (phase === 'exposure') showChoice();
      else finish(null);
      return;
    }
    frameId = requestAnimationFrame(updateTimer);
  }

  function showChoice() {
    if (destroyed || phase !== 'exposure') return;
    clearTimers();
    const now = clock();
    observedMs = now - exposedAt;
    chosenAt = now;
    deadline = now + choiceMs;
    const pairHeight = content.querySelector('.i-pair').getBoundingClientRect().height;
    const choices = renderChoices(finish);
    choices.style.minHeight = `${pairHeight}px`;
    // Replacing the posts prevents reading them during the answer window.
    content.replaceChildren(choices);
    instruction.textContent = 'Choose.';
    announcement.textContent = 'Posts hidden. Choose left or right now.';
    setPhase('choice');
    if (destroyed) return;
    fill.style.transform = 'scaleX(1)';
    remaining.textContent = `${(choiceMs / 1000).toFixed(1)}s`;
    deadlineTimer = setTimeout(() => finish(null), choiceMs);
    frameId = requestAnimationFrame(updateTimer);
  }

  function interrupt(reason, error) {
    if (destroyed || phase === 'interrupted' || phase === 'complete') return;
    if (!error && !['exposure', 'choice'].includes(phase) && !startRequested) return;
    const interruptedPhase = phase;
    const seenMs = phase === 'exposure' ? clock() - exposedAt : observedMs;
    clearTimers();
    assetAbort.abort();
    setPhase('interrupted');
    if (destroyed) return;
    instruction.textContent = error ? 'The timer did not start.' : 'A timed round needs your full attention.';
    showMessage(error ? 'A post image couldn’t load.' : 'Round interrupted.', error ? 'Start a fresh round after the images are available.' : 'Return to the test and start a fresh round.');
    onInterrupt({ reason, phase: interruptedPhase, observedMs: seenMs, ...(error ? { errorCode: error.code || 'asset-error', assetKind: error.kind, side: error.side, assetIndex: error.index } : {}) });
  }

  function prepare() {
    if (destroyed || phase === 'interrupted') return Promise.resolve(null);
    if (preparedAssets) return Promise.resolve(preparedAssets);
    if (preparation) return preparation;
    setPhase('loading');
    if (destroyed) return Promise.resolve(null);
    instruction.textContent = 'The timer starts after all images are ready.';
    showMessage('Loading posts…', 'Preparing images and avatars.');
    preparation = preloadPairAssets(pair, { assetBaseUrl, resolveAsset, timeoutMs: assetTimeoutMs, avatarTimeoutMs, signal: assetAbort.signal })
      .then(assets => {
        if (destroyed || phase === 'interrupted') return null;
        preparedAssets = assets;
        setPhase('ready');
        if (destroyed) return null;
        instruction.textContent = 'Get ready.';
        showMessage('Ready when you are.', 'Both posts are ready to show.');
        return assets;
      })
      .catch(error => {
        if (!destroyed && phase !== 'interrupted') interrupt('asset-error', error);
        return null;
      });
    return preparation;
  }

  async function beginExposure() {
    const assets = await prepare();
    if (!assets || destroyed || phase === 'interrupted') return false;
    if (document.hidden || !document.hasFocus()) {
      interrupt(document.hidden ? 'visibility' : 'blur');
      return false;
    }
    content.style.visibility = 'hidden';
    content.replaceChildren(renderPostPair(pair, { assets, assetBaseUrl, resolveAsset }));
    return new Promise(resolve => {
      paintResolve = resolve;
      frameId = requestAnimationFrame(() => {
        paintResolve = null;
        if (destroyed || phase === 'interrupted') { resolve(false); return; }
        if (document.hidden || !document.hasFocus()) {
          interrupt(document.hidden ? 'visibility' : 'blur');
          resolve(false);
          return;
        }
        content.style.visibility = '';
        instruction.textContent = 'Look.';
        announcement.textContent = `Read both posts. You have ${exposureMs / 1000} seconds.`;
        exposedAt = clock();
        deadline = exposedAt + exposureMs;
        setPhase('exposure');
        if (destroyed) { resolve(false); return; }
        deadlineTimer = setTimeout(showChoice, exposureMs);
        frameId = requestAnimationFrame(updateTimer);
        resolve(true);
      });
    });
  }

  function onKey(event) {
    if (event.repeat || phase !== 'choice' || destroyed) return;
    const choice = event.key === 'ArrowLeft' ? 'left' : event.key === 'ArrowRight' ? 'right' : null;
    if (choice) {
      event.preventDefault();
      finish(choice);
    }
  }

  const onVisibility = () => { if (document.hidden) interrupt('visibility'); };
  const onBlur = () => interrupt('blur');
  document.addEventListener('keydown', onKey);
  document.addEventListener('visibilitychange', onVisibility);
  window.addEventListener('blur', onBlur);
  paintFrame();
  showMessage('Ready when you are.', `The posts will disappear after ${exposureMs / 1000} seconds.`);
  mount.dataset.phase = 'idle';

  return {
    prepare,
    start() {
      if (destroyed || !['idle', 'loading', 'ready'].includes(phase)) return Promise.resolve(false);
      if (startPromise) return startPromise;
      startRequested = true;
      startPromise = beginExposure();
      return startPromise;
    },
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
