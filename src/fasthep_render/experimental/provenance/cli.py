"""``python -m fasthep_render.experimental.provenance.cli BUNDLE OUT``."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .normalise import normalise


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("bundle", type=Path, help="Flow run output directory")
    p.add_argument("out", type=Path, help="directory for the viewer JSON")
    p.add_argument(
        "--no-sanitize",
        action="store_true",
        help="keep machine-specific values; only for gitignored local output",
    )
    args = p.parse_args(argv)
    report = normalise(args.bundle, args.out, sanitize=not args.no_sanitize)
    print(json.dumps(report["measurements"], indent=1))  # noqa: T201
    return 1 if report["leaks_found"] and not args.no_sanitize else 0


if __name__ == "__main__":
    raise SystemExit(main())
