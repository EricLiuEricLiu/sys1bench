"""Explicit local Gateway-key loading; no interpolation or secret output."""

import os
from pathlib import Path

from .core import require


def load_gateway_env(path):
    """Load only AI_GATEWAY_API_KEY from a user-selected uncommitted env file."""
    if os.environ.get("AI_GATEWAY_API_KEY"):
        return True
    values = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:].strip()
        name, separator, value = line.partition("=")
        if not separator or name.strip() != "AI_GATEWAY_API_KEY":
            continue
        value = value.strip()
        if value[:1] in {"'", '"'}:
            require(len(value) >= 2 and value[-1] == value[0], "Invalid quoted Gateway key in local env file")
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].strip()
        require(value and not any(c.isspace() for c in value), "Missing or invalid Gateway key in local env file")
        values.append(value)
    require(len(values) == 1, "Local env file must contain exactly one nonempty AI_GATEWAY_API_KEY")
    os.environ["AI_GATEWAY_API_KEY"] = values[0]
    return True
