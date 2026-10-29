"""Explicit synthetic unit-test data, never real benchmark observations."""

import base64
import copy
from pathlib import Path

from evals.core import file_digest, write_json


def cross_author_fixture(root):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    # A known 1px PNG is sufficient for byte-boundary tests; no image generation.
    image = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aJ1kAAAAASUVORK5CYII=")
    (root / "synthetic.png").write_bytes(image)
    sha = file_digest(root / "synthetic.png")
    pairs = []
    for number in range(3):
        pair = {"id": f"synthetic-pair-{number}"}
        for side in ["left", "right"]:
            suffix = "a" if side == "left" else "b"
            pair[side] = {"id": f"synthetic-{number}-{suffix}", "text": f"Synthetic content {number} {suffix}",
                          "displayText": f"Synthetic content {number} {suffix}",
                          "author": {"id": "synthetic-author-" + suffix, "name": "Synthetic " + suffix,
                                     "handle": "synthetic_" + suffix, "avatarAssetFile": "synthetic.png", "avatarSha256": sha},
                          "media": ([{"type": "photo", "assetFile": "synthetic.png", "sha256": sha, "width": 1, "height": 1}] if number == 1 else [])}
        pairs.append(pair)
    client = {"version": "0.5.0", "language": "en", "timing": {"roundMs": 15000, "revealMs": 2500},
              "humanProtocolId": "human-15s-visible-feedback-cross-author-education2-v4",
              "feedback": {"afterEveryRound": True, "autoAdvance": True, "metrics": ["replies", "reposts", "likes", "impressions"]},
              "display": {"authors": True, "avatars": True, "handles": True, "followerCounts": False, "engagement": False},
              "practice": pairs[:2], "pairs": pairs[2:]}
    bank = copy.deepcopy(client)
    bank.update(outcome="cumulative_snapshot_views", limitations=["Synthetic unit-test fixture, not a real collected observation."])
    for pair in bank["practice"] + bank["pairs"]:
        for side in ["left", "right"]:
            post = pair[side]
            post["engagement"] = {"replies": 12, "reposts": 34, "likes": 56, "impressions": 150000 if side == "left" else 300000}
            post.update(views=post["engagement"]["impressions"], url=f"https://x.com/{post['author']['handle']}/status/{post['id']}")
    write_json(root / "stimuli.client.json", client)
    write_json(root / "question-bank.server.json", bank)
    return root / "stimuli.client.json", root / "question-bank.server.json"
