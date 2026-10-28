const assetError = (code, message, details = {}) => Object.assign(new Error(message), { code, ...details });

export function resolvePostMediaUrl(media, { assetBaseUrl, resolveAsset, side, post, index } = {}) {
  if (resolveAsset) return resolveAsset(media, { kind: 'content', side, post, index });
  if (assetBaseUrl && media.assetFile) return new URL(media.assetFile, assetBaseUrl).href;
  return media.url;
}

export function resolveAvatarUrl(author, { resolveAsset, side, post } = {}) {
  return resolveAsset ? resolveAsset(author, { kind: 'avatar', side, post }) : author?.avatarUrl;
}

function decodeImage(src, { timeoutMs, signal }) {
  return new Promise((resolve, reject) => {
    if (!src || typeof src !== 'string') {
      reject(assetError('missing-image', 'An image URL is missing.'));
      return;
    }
    const image = new Image();
    image.decoding = 'async';
    image.loading = 'eager';
    image.referrerPolicy = 'no-referrer';
    image.fetchPriority = 'high';
    let settled = false;
    let decoding = false;
    let timer;
    function finish(error) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      image.onload = null;
      image.onerror = null;
      signal?.removeEventListener('abort', abort);
      if (error) {
        image.removeAttribute('src');
        reject(error);
      } else resolve(image);
    }
    function abort() { finish(assetError('aborted', 'Image preparation was cancelled.')); }
    image.onerror = () => finish(assetError('image-load-failed', 'An image could not load.'));
    image.onload = async () => {
      if (settled || decoding) return;
      decoding = true;
      try {
        if (image.decode) await image.decode();
        if (!image.naturalWidth || !image.naturalHeight) throw new Error('Empty image');
        finish();
      } catch { finish(assetError('image-decode-failed', 'An image could not decode.')); }
    };
    signal?.addEventListener('abort', abort, { once: true });
    if (signal?.aborted) { abort(); return; }
    timer = setTimeout(() => finish(assetError('image-timeout', 'An image took too long to load.')), timeoutMs);
    image.src = src;
  });
}

export async function preloadPairAssets(pair, {
  assetBaseUrl,
  resolveAsset,
  timeoutMs = 12000,
  avatarTimeoutMs = 3000,
  signal,
} = {}) {
  if (!(timeoutMs > 0) || !(avatarTimeoutMs > 0)) throw new TypeError('Asset timeouts must be positive');
  const started = performance.now();
  const group = new AbortController();
  const abort = () => group.abort();
  signal?.addEventListener('abort', abort, { once: true });
  if (signal?.aborted) group.abort();
  const result = { left: null, right: null, contentImages: 0, avatarFallbacks: 0, loadMs: 0 };
  try {
    await Promise.all(['left', 'right'].map(async side => {
      const post = pair?.[side];
      if (!post || typeof (post.displayText ?? post.text) !== 'string') throw assetError('invalid-post', 'A post has no display text.', { kind: 'content', side });
      const media = post.media ?? [];
      if (!Array.isArray(media) || media.some(item => item.type !== 'photo')) throw assetError('unsupported-media', 'This renderer requires photo attachments.', { kind: 'content', side });
      const avatarSrc = resolveAvatarUrl(post.author, { resolveAsset, side, post });
      const avatarTask = avatarSrc ? decodeImage(avatarSrc, { timeoutMs: avatarTimeoutMs, signal: group.signal }).catch(error => {
        if (group.signal.aborted) throw error;
        result.avatarFallbacks += 1;
        return null;
      }) : Promise.resolve(null).then(() => { result.avatarFallbacks += 1; return null; });
      const mediaTask = Promise.all(media.map(async (item, index) => {
        try {
          const src = resolvePostMediaUrl(item, { assetBaseUrl, resolveAsset, side, post, index });
          const image = await decodeImage(src, { timeoutMs, signal: group.signal });
          result.contentImages += 1;
          return image;
        } catch (error) {
          throw Object.assign(error, { kind: 'content', side, index });
        }
      }));
      const [avatar, images] = await Promise.all([avatarTask, mediaTask]);
      result[side] = { avatar, images };
    }));
    result.loadMs = performance.now() - started;
    return result;
  } catch (error) {
    group.abort();
    throw error;
  } finally {
    signal?.removeEventListener('abort', abort);
  }
}
