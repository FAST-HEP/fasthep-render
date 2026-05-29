from __future__ import annotations

import csv
from pathlib import Path

import pytest

from fasthep_render.impl.sinks.cutflow_csv import run_cutflow_csv_render


def test_cutflow_csv_renderer_writes_single_dataset_csv(tmp_path: Path) -> None:
    out = tmp_path / "cutflow.csv"

    result = run_cutflow_csv_render(
        _cutflow_graph(
            datasets=["data"],
            nodes=[
                ("All[0]", "All", "NIsoMuon >= 2", {"data": (20.5, 10.5, 20, 10)}),
                ("All[1]", "All", "Muon_Pt > 25", {"data": (10.5, 5.5, 10, 5)}),
            ],
        ),
        spec={"op": "hep.render.cutflow_csv"},
        output_path=str(out),
    )

    with out.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert result.path == str(out)
    assert rows[0]["dataset"] == "data"
    assert rows[0]["selection"] == "All"
    assert rows[0]["cut"] == "NIsoMuon >= 2"
    assert rows[0]["n_in"] == "20.5"
    assert rows[0]["n_out"] == "10.5"
    assert rows[0]["n_unweighted_in"] == "20"
    assert rows[0]["n_unweighted_out"] == "10"
    assert rows[1]["efficiency"] == "0.5"


def test_cutflow_csv_renderer_writes_multi_dataset_csv(tmp_path: Path) -> None:
    out = tmp_path / "cutflow.csv"

    run_cutflow_csv_render(
        _cutflow_graph(
            datasets=["data", "dy"],
            nodes=[
                (
                    "All[0]",
                    "All",
                    "NIsoMuon >= 2",
                    {"data": (20.0, 10.0, 20, 10), "dy": (40.5, 20.5, 40, 20)},
                )
            ],
        ),
        spec={"op": "hep.render.cutflow_csv"},
        output_path=str(out),
    )

    with out.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["dataset"] for row in rows] == ["data", "dy"]
    assert "default" not in {row["dataset"] for row in rows}
    assert [row["n_out"] for row in rows] == ["10.0", "20.5"]
    assert [row["n_unweighted_out"] for row in rows] == ["10", "20"]


def test_cutflow_csv_renderer_rejects_invalid_cutflow(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="'cuts' list"):
        run_cutflow_csv_render(
            {"not": "a cutflow"},
            spec={"op": "hep.render.cutflow_csv"},
            output_path=str(tmp_path / "cutflow.csv"),
        )


def test_cutflow_csv_renderer_rejects_invalid_canonical_cutflow(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="canonical cutflow 'nodes'"):
        run_cutflow_csv_render(
            {"kind": "cutflow", "datasets": ["data"]},
            spec={"op": "hep.render.cutflow_csv"},
            output_path=str(tmp_path / "cutflow.csv"),
        )


def _cutflow_graph(
    *,
    datasets: list[str],
    nodes: list[tuple[str, str, str, dict[str, tuple[float, float, int, int]]]],
) -> dict[str, object]:
    return {
        "version": "1.0",
        "kind": "cutflow",
        "producer": "stage.EventSelection",
        "datasets": datasets,
        "nodes": [
            {
                "id": node_id,
                "selection": selection,
                "index": index,
                "label": label,
                "expr": label,
                "kind": "expression",
                "parents": [],
                "stats": {
                    dataset: {
                        "n_in": n_in,
                        "n_out": n_out,
                        "n_unweighted_in": n_unweighted_in,
                        "n_unweighted_out": n_unweighted_out,
                        "sumw_in": float(n_in),
                        "sumw_out": float(n_out),
                        "sumw2_in": float(n_unweighted_in),
                        "sumw2_out": float(n_unweighted_out),
                    }
                    for dataset, (
                        n_in,
                        n_out,
                        n_unweighted_in,
                        n_unweighted_out,
                    ) in stats.items()
                },
            }
            for index, (node_id, selection, label, stats) in enumerate(nodes)
        ],
        "edges": [],
    }
