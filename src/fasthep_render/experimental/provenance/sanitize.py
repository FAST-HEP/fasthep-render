"""Sanitization of machine-specific values (user, host, absolute paths)."""

from __future__ import annotations

import json
import re
from typing import Any

# Absolute paths below these roots are machine specific.
_PATH = re.compile(
    r"(?<![\w.])/(?:home|Users|afs|eos|tmp|var|root|cvmfs|scratch|data|work)"
    r"(?:/[^\s'\",:;()\[\]{}]+)+"
)
_REDACTED = "<path>"


class Sanitizer:
    """Replaces machine-specific strings; records which rules fired."""

    def __init__(self, *, bundle_root: str, secrets: tuple[str, ...] = ()) -> None:
        self.bundle_root = bundle_root.rstrip("/")
        # Longest first so a host name is not eaten by a shorter fragment.
        self.secrets = tuple(sorted({s for s in secrets if s}, key=len, reverse=True))
        self.counts: dict[str, int] = {}

    def _hit(self, rule: str) -> None:
        self.counts[rule] = self.counts.get(rule, 0) + 1

    def text(self, value: str) -> str:
        if self.bundle_root and self.bundle_root in value:
            value = value.replace(self.bundle_root, "<bundle>")
            self._hit("bundle_root")

        def _path(match: re.Match[str]) -> str:
            self._hit("absolute_path")
            return f"{_REDACTED}/{match.group(0).rsplit('/', 1)[-1]}"

        value = _PATH.sub(_path, value)
        for secret in self.secrets:
            if secret in value:
                value = value.replace(secret, "<redacted>")
                self._hit("identifier")
        return value

    def any(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, dict):
            return {self.text(str(k)): self.any(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [self.any(v) for v in value]
        return value


def find_leaks(
    value: Any, needles: tuple[str, ...] = ("/home/", "/Users/")
) -> list[str]:
    """Return the needles still present in ``value`` (used by the fixture guard)."""
    text = json.dumps(value)
    return [n for n in needles if n in text]
