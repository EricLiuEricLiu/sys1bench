"""Documented API image normalization; original captured inputs stay immutable."""

from pathlib import Path

from .assets import local_blob
from .core import load_json, require

JEV_INPUTS = Path(__file__).parent / "fixtures/cross-author-v0.6.0/jev-avatar-inputs"


def submitted_images(request, config):
    transformed, evidence = [], []
    entries = None
    policy = config.get("image_preprocessing")
    for original in request.get("images", []):
        image = original
        if policy and original["ref"].endswith(".avatar") and (original["width"], original["height"]) == (48, 48):
            if entries is None:
                entries = {e["source_sha256"]: e for e in load_json(JEV_INPUTS / "manifest.json")["entries"]}
            require(original["sha256"] in entries, "No registered Jev avatar transform for captured source bytes")
            entry = entries[original["sha256"]]
            image = {"ref": original["ref"], **local_blob(JEV_INPUTS, entry["assetFile"], entry["sha256"])}
        if policy:
            require(280 <= image["width"] <= 1568 and 280 <= image["height"] <= 1568, "Jev input image dimensions must be within 280..1568 pixels")
        transformed.append(image)
        evidence.append({"ref": image["ref"], "source_sha256": original["sha256"], "submitted_sha256": image["sha256"],
                         "width": image["width"], "height": image["height"], "policy": policy or "original-captured-bytes"})
    return transformed, evidence
