"""Write runs.json for a directory of normalised runs (one folder per run)."""

import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
runs = [
    {"id": p.name, "label": p.name}
    for p in sorted(root.iterdir())
    if (p / "run-index.json").exists()
]
(root / "runs.json").write_text(json.dumps({"schema_version": 1, "runs": runs}, indent=1) + "\n")
