"""Write a tiny, invented Flow-style bundle that exercises UI states real runs lack.

SYNTHETIC: nothing here was produced by a real run. It has a recorded fallback, a node
without an implementation name (shown as `Not recorded`), a complete, a partial and an
unavailable artifact. Normalise it with `--synthetic NOTE` so the viewer labels it.
Usage: python make_synthetic_bundle.py OUTDIR
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def node(nid: str, role: str, impl: str | None, params: dict | None = None, meta: dict | None = None) -> dict:
    text = (
        f"GraphNode(id={nid!r}, role={role!r}, impl={impl!r}, params={params or {}!r}, "
        f"outputs={{}}, meta={meta or {}!r})"
    )
    return {"id": nid, "payload": text}


def write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, sort_keys=True) + "\n")


def main(out: Path) -> None:
    datasets = [
        {"name": "demo_data", "files": ["demo/data.root"], "nevents": "1000", "eventtype": "data"},
        {"name": "demo_mc", "files": ["demo/mc.root"], "nevents": "5000", "eventtype": "mc"},
    ]
    chain = ["stage.Select", "stage.Calibrate", "stage.Fill"]
    write(
        out / "graph/graph.json",
        {
            "nodes": [
                node("read.events", "source", "root_tree", {"datasets": datasets}),
                node("stage.Select", "transform", "demo.select"),
                node("stage.Calibrate", "transform", None),  # implementation not recorded
                node("stage.Fill", "transform", "demo.hist"),
            ],
            "edges": [
                {"source": a, "target": b, "output": "stream", "input_name": "stream"}
                for a, b in zip(["read.events", *chain], chain, strict=False)
            ],
        },
    )

    def execution(nid: str, resources: list[str]) -> dict:
        return {"node_id": nid, "operations": [{"inputs": {"resources": resources}, "outputs": {}}]}

    write(
        out / "artifacts/provenance/execution.json",
        {
            "version": "1.0",
            "run_id": "00000000-0000-4000-8000-000000000001",
            "software": {"demo": "0.0.0"},
            "execution": {"python_version": "3.0.0"},
            "partitions": [{"id": "p0"}, {"id": "p1"}],
            "executions": {
                "e1": execution("stage.Select", ["demo.lumimask"]),
                "e2": execution("stage.Calibrate", ["demo.jec"]),
            },
            "resources": {
                "demo.lumimask": {
                    "kind": "data_quality_mask",
                    "requested_era": "2022",
                    "selected": {"path": "demo/mask.json", "sha256": "0" * 64, "fallback": False},
                },
                "demo.jec": {
                    "kind": "correctionlib",
                    "requested_era": "2023",
                    "selected": {
                        "path": "demo/jec_2022.json.gz",
                        "sha256": "1" * 64,
                        "correction": "demo_jec",
                        "correction_version": 3,
                        "fallback": True,
                        "fallback_reason": "requested era 2023 not available; used 2022",
                    },
                },
            },
        },
    )
    write(
        out / "artifacts/provenance/manifest.json",
        {
            "version": "1.0",
            "records": [
                {
                    "artifact": "artifacts/histograms/Selected.pkl",
                    "kind": "histogram",
                    "node_id": "stage.Fill",
                    "record": "artifacts/provenance/records/artifact-synthetic.json",
                }
            ],
        },
    )
    write(
        out / "artifacts/histograms/manifest.json",
        {
            "histograms": [
                {"id": "Selected", "path": "artifacts/histograms/Selected.pkl", "producer": "stage.Fill"},
                {"id": "Calibrated", "path": "artifacts/histograms/Calibrated.pkl", "producer": "stage.Calibrate"},
                {"id": "Orphan", "path": "artifacts/histograms/Orphan.pkl", "producer": "stage.Removed"},
            ]
        },
    )


if __name__ == "__main__":
    main(Path(sys.argv[1]))
