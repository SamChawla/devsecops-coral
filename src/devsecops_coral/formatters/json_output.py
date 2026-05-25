"""JSON output formatters."""

from __future__ import annotations

import json
from typing import Any


def to_json(data: Any) -> str:
    """Serialize data to a JSON string for stdout."""
    return json.dumps(data, indent=2, default=str)
