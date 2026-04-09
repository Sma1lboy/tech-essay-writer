"""Shared utilities for tech-essay-writer Python scripts."""

import json
import os
import random
import time
from datetime import datetime, timezone


def atomic_json_write(path, data):
    """Write dict to JSON via tmp file + os.rename (atomic write pattern)."""
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2)
    os.rename(tmp, path)


def read_json_file(path, default=None):
    """Read JSON file with fallback to default."""
    if default is None:
        default = {}
    if not os.path.isfile(path):
        return default
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return default


def timestamp_now():
    """Returns UTC ISO 8601 string like 2024-01-01T00:00:00Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def gen_id(prefix="src"):
    """Returns {prefix}-{timestamp}-{random 3 digits}."""
    return f"{prefix}-{int(time.time())}-{random.randint(100, 999)}"
