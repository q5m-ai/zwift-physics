"""Small, strict serialization utilities; no network or credential handling."""
from __future__ import annotations
import hashlib
import json
import math
import os
import tempfile
from pathlib import Path


def number(value, label="value", *, strings=False):
    if isinstance(value, bool) or not isinstance(value, (int, float, str) if strings else (int, float)):
        raise ValueError(f"{label} must be a finite number")
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _constant(_):
    raise ValueError("Non-finite JSON constants are not supported")


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON keys are not supported")
        result[key] = value
    return result


def loads(text):
    return json.loads(text, parse_constant=_constant, object_pairs_hook=_object,
                      parse_float=lambda text: number(text, "JSON number", strings=True))


def load(path):
    return loads(Path(path).read_text(encoding="utf-8"))


def digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def save(path, value):
    """Atomic replacement of a task-owned JSON artifact, never partial JSON."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="." + path.name + ".", delete=False) as f:
            name = f.name
            f.write(payload)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if name is not None and os.path.exists(name):
            os.unlink(name)
