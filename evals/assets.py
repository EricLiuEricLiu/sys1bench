"""Capture once, then verify and inline original PNG/JPEG bytes without URLs."""

import base64
import hashlib
import struct
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from .legacy_core import file_digest, load_json, require, write_json

MAX_IMAGE_BYTES = 8 * 1024 * 1024


def image_info(raw):
    require(isinstance(raw, bytes) and 0 < len(raw) <= MAX_IMAGE_BYTES, "Invalid image byte length")
    if raw.startswith(b"\x89PNG\r\n\x1a\n") and len(raw) >= 33 and raw[12:16] == b"IHDR":
        width, height = struct.unpack(">II", raw[16:24])
        mime = "image/png"
    elif raw.startswith(b"\xff\xd8") and b"\xff\xd9" in raw[2:]:
        pos, width, height = 2, None, None
        while pos + 4 <= len(raw):
            require(raw[pos] == 255, "Malformed JPEG marker")
            while pos < len(raw) and raw[pos] == 255:
                pos += 1
            marker = raw[pos]
            pos += 1
            if marker in {0x01, *range(0xD0, 0xD9)}:
                continue
            require(pos + 2 <= len(raw), "Truncated JPEG segment")
            size = int.from_bytes(raw[pos:pos + 2], "big")
            require(size >= 2 and pos + size <= len(raw), "Invalid JPEG segment")
            if marker in {0xC0, 0xC1, 0xC2}:
                require(size >= 8, "Invalid JPEG frame")
                height, width = struct.unpack(">HH", raw[pos + 3:pos + 7])
                break
            if marker == 0xDA:
                break
            pos += size
        require(width is not None and height is not None, "JPEG frame dimensions missing")
        mime = "image/jpeg"
    else:
        raise ValueError("Expected captured PNG/JPEG; no transcoding or silent image fallback")
    require(width > 0 and height > 0 and width * height <= 100_000_000, "Invalid image dimensions")
    return {"mime_type": mime, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw), "width": width, "height": height}


def image_blob(raw):
    return {**image_info(raw), "data_base64": base64.b64encode(raw).decode("ascii")}


def validate_blob(blob):
    require(isinstance(blob, dict) and set(blob) == {"mime_type", "sha256", "size_bytes", "width", "height", "data_base64"}, "Unexpected image fields")
    require(isinstance(blob["data_base64"], str) and len(blob["data_base64"]) <= MAX_IMAGE_BYTES * 4 // 3 + 8, "Invalid image encoding size")
    try:
        raw = base64.b64decode(blob["data_base64"], validate=True)
    except (ValueError, TypeError):
        raise ValueError("Invalid base64 image") from None
    require(image_info(raw) == {k: v for k, v in blob.items() if k != "data_base64"}, "Image bytes/hash/dimensions mismatch")
    return blob


def local_blob(root, name, sha256):
    root = Path(root).resolve()
    require(isinstance(name, str) and name and not Path(name).is_absolute(), "Expected relative asset path")
    path = (root / name).resolve()
    require(path.is_relative_to(root), "Asset escapes dataset directory")
    require(isinstance(sha256, str) and len(sha256) == 64 and file_digest(path) == sha256, "Captured image hash mismatch")
    return image_blob(path.read_bytes())


def avatar_index(manifest_path, stimuli_path):
    manifest = load_json(manifest_path)
    require(manifest["schema_version"] == "avatar-capture-v1", "Unknown avatar capture schema")
    require(manifest["source_stimuli_sha256"] == file_digest(stimuli_path), "Avatar capture belongs to different stimuli bytes")
    index = {}
    for entry in manifest["entries"]:
        require(entry["url"] not in index, "Duplicate captured avatar URL")
        index[entry["url"]] = local_blob(Path(manifest_path).parent, entry["assetFile"], entry["sha256"])
    return index


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def capture_avatars(stimuli_path, out):
    """Explicit free image downloads only; prepare/run never invoke this function."""
    from .runner import now
    data = load_json(stimuli_path)
    require(data.get("version") == "0.3.0" and isinstance(data.get("practice"), list) and len(data["practice"]) == 2, "Capture requires actual 0.3.0 two-practice dataset")
    urls = sorted({p[s]["author"]["avatarUrl"] for p in data["practice"] + data["pairs"] for s in ["left", "right"]})
    require(0 < len(urls) <= 34, "Unexpected avatar count")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    manifest = {"schema_version": "avatar-capture-v1", "source_stimuli_sha256": file_digest(stimuli_path), "captured_at": now(), "entries": []}
    opener = urllib.request.build_opener(NoRedirect())
    for url in urls:
        parsed = urlparse(url)
        require(parsed.scheme == "https" and parsed.hostname == "pbs.twimg.com" and parsed.username is None and parsed.password is None, "Only HTTPS pbs.twimg.com avatar sources are allowed")
        req = urllib.request.Request(url, headers={"User-Agent": "System1Bench-offline-asset-capture/2.0"})
        with opener.open(req, timeout=20) as response:
            raw = response.read(MAX_IMAGE_BYTES + 1)
        info = image_info(raw)
        suffix = ".png" if info["mime_type"] == "image/png" else ".jpg"
        name = info["sha256"] + suffix
        (out / name).write_bytes(raw)
        manifest["entries"].append({"url": url, "assetFile": name, **info})
        write_json(out / "avatar-manifest.private.json", manifest)
    return manifest
