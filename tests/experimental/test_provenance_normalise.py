from __future__ import annotations

import importlib
import json
import warnings
from pathlib import Path

import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import fasthep_render.experimental as exp
    from fasthep_render.experimental.provenance.graph_repr import parse_graph_node
    from fasthep_render.experimental.provenance.groups import candidate_groups
    from fasthep_render.experimental.provenance.normalise import normalise
    from fasthep_render.experimental.provenance.sanitize import Sanitizer


def _node(nid: str, role: str = "transform", meta: str = "{}") -> dict:
    return {
        "id": nid,
        "payload": f"GraphNode(id='{nid}', role='{role}', impl='x', params={{}}, "
        f"outputs={{}}, meta={meta})",
    }


def test_experimental_import_warns() -> None:
    with pytest.warns(UserWarning, match="exploratory prototype"):
        importlib.reload(exp)


def test_parse_graph_node_is_literal_only() -> None:
    n = parse_graph_node("GraphNode(id='a', role='source', params={'k': [1, 2]})")
    assert n["params"] == {"k": [1, 2]}
    with pytest.raises(ValueError, match="GraphNode"):
        parse_graph_node("__import__('os').system('true')")


def test_sanitizer_removes_paths_and_identifiers() -> None:
    s = Sanitizer(bundle_root="/home/u/run", secrets=("myhost",))
    out = s.any(
        {"a": "/home/u/run/x/y.root", "b": "/home/u/other/z.json", "c": "myhost"}
    )
    assert out == {"a": "<bundle>/x/y.root", "b": "<path>/z.json", "c": "<redacted>"}


def test_groups_chain_region_variation() -> None:
    ids = ["a", "b", "c", "d", "e", "f", "g"]
    edges = [
        {"source": s, "target": t}
        for s, t in [
            ("a", "b"),
            ("b", "c"),
            ("b", "d"),
            ("c", "e"),
            ("d", "e"),
            ("e", "f"),
            ("f", "g"),
        ]
    ]
    groups = {g["id"]: g for g in candidate_groups(ids, edges, {"c": {"name": "v"}})}
    assert groups["region:b"]["merge_node"] == "e"
    assert set(groups["region:b"]["node_ids"]) == {"b", "c", "d"}
    assert groups["variation:v"]["origin"] == "source"
    assert groups["region:b"]["origin"] == "inferred"
    assert groups["chain:e"]["node_ids"] == ["e", "f", "g"]


def test_normalise_mini_bundle(tmp_path: Path) -> None:
    b = tmp_path / "run"
    (b / "graph").mkdir(parents=True)
    (b / "artifacts/provenance").mkdir(parents=True)
    (b / "artifacts/histograms").mkdir()
    (b / "graph/graph.json").write_text(
        json.dumps(
            {
                "nodes": [
                    _node("read.e", "source"),
                    _node("stage.h"),
                    _node("stage.x"),
                ],
                "edges": [
                    {
                        "source": "read.e",
                        "target": "stage.h",
                        "output": "s",
                        "input_name": "s",
                    },
                    {
                        "source": "read.e",
                        "target": "stage.x",
                        "output": "s",
                        "input_name": "s",
                    },
                ],
            }
        )
    )
    (b / "artifacts/provenance/execution.json").write_text(
        json.dumps(
            {
                "run_id": "r1",
                "execution": {"hostname": "box", "cwd": str(b)},
                "partitions": [],
            }
        )
    )
    (b / "artifacts/provenance/manifest.json").write_text(json.dumps({"records": []}))
    (b / "artifacts/histograms/manifest.json").write_text(
        json.dumps(
            {
                "histograms": [
                    {
                        "id": "h",
                        "path": "artifacts/histograms/h.pkl",
                        "producer": "stage.h",
                    },
                    {
                        "id": "m",
                        "path": "artifacts/histograms/m.pkl",
                        "producer": "stage.gone",
                    },
                ],
            }
        )
    )
    report = normalise(b, tmp_path / "out")
    assert report["leaks_found"] == []
    index = json.loads((tmp_path / "out/run-index.json").read_text())
    by_name = {a["name"]: a for a in index["artifacts"]}
    assert by_name["h"]["completeness"] == "partial"
    assert by_name["h"]["ancestor_count"] == 2  # stage.x is not an ancestor
    assert by_name["m"]["completeness"] == "unavailable"
    assert "graph_ref" not in by_name["m"]
    assert "box" not in json.dumps(index)


def test_resources_operations_and_dataset_group(tmp_path: Path) -> None:
    b = tmp_path / "run"
    for d in ("graph", "artifacts/provenance", "artifacts/histograms"):
        (b / d).mkdir(parents=True)
    datasets = [
        {
            "name": f"d{i}",
            "files": ["/home/u/f.root"],
            "nevents": "5",
            "eventtype": "mc",
        }
        for i in range(4)
    ]
    read = {
        "id": "read.e",
        "payload": f"GraphNode(id='read.e', role='source', impl='x', params={{'datasets': {datasets!r}}}, "
        "outputs={}, meta={})",
    }
    (b / "graph/graph.json").write_text(
        json.dumps(
            {
                "nodes": [read, _node("stage.h")],
                "edges": [
                    {
                        "source": "read.e",
                        "target": "stage.h",
                        "output": "s",
                        "input_name": "s",
                    }
                ],
            }
        )
    )
    (b / "artifacts/provenance/execution.json").write_text(
        json.dumps(
            {
                "run_id": "r1",
                "execution": {},
                "partitions": [],
                "executions": {
                    "e1": {
                        "node_id": "stage.h",
                        "operations": [
                            {"inputs": {"resources": ["r.x"]}, "outputs": {}}
                        ],
                    }
                },
                "resources": {
                    "r.x": {
                        "kind": "correctionlib",
                        "selected": {
                            "correction": "c",
                            "fallback": True,
                            "path": "/home/u/x.json",
                        },
                    },
                    "r.unused": {"kind": "correctionlib"},
                },
            }
        )
    )
    (b / "artifacts/provenance/manifest.json").write_text(json.dumps({"records": []}))
    (b / "artifacts/histograms/manifest.json").write_text(
        json.dumps(
            {"histograms": [{"id": "h", "path": "h.pkl", "producer": "stage.h"}]}
        )
    )
    normalise(b, tmp_path / "out")
    ref = json.loads((tmp_path / "out/run-index.json").read_text())["artifacts"][0][
        "graph_ref"
    ]
    graph = json.loads((tmp_path / "out" / ref).read_text())
    proc = {n["id"]: n for n in graph["nodes"] if n["kind"] == "processing"}
    assert proc["stage.h"]["resource_ids"] == ["r.x"]
    assert set(graph["resources"]) == {"r.x"}  # only resources used by ancestors
    assert graph["resources"]["r.x"]["fallback"] is True
    assert graph["resources"]["r.x"]["path"] == "<path>/x.json"
    group = next(g for g in graph["groups"] if g["kind"] == "datasets")
    assert len(group["node_ids"]) == 4
    details = json.loads(
        (tmp_path / "out" / ref.replace("graph", "details")).read_text()
    )
    assert details["nodes"]["stage.h"]["operations"][0]["inputs"]["resources"] == [
        "r.x"
    ]
