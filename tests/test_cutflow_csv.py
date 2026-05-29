from __future__ import annotations

import csv
from pathlib import Path

import pytest

from fasthep_render.impl.sinks.cutflow_csv import run_cutflow_csv_render


def test_cutflow_csv_renderer_writes_single_dataset_csv(tmp_path: Path) -> None:
    out = tmp_path / "cutflow.csv"

    result = run_cutflow_csv_render(
        {
            "dataset": "data",
            "cuts": [
                {"name": "All[0]", "n": 10, "sumw": 10.0},
                {"name": "All[1]", "n": 5, "sumw": 5.0},
            ],
        },
        spec={"op": "hep.render.cutflow_csv"},
        output_path=str(out),
    )

    with out.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert result.path == str(out)
    assert rows[0]["dataset"] == "data"
    assert rows[0]["name"] == "All[0]"
    assert rows[1]["efficiency"] == "0.5"


def test_cutflow_csv_renderer_writes_multi_dataset_csv(tmp_path: Path) -> None:
    out = tmp_path / "cutflow.csv"

    run_cutflow_csv_render(
        {
            "cutflows": [
                {"dataset": "data", "cuts": [{"name": "All[0]", "n": 10}]},
                {"dataset": "dy", "cuts": [{"name": "All[0]", "n": 20}]},
            ]
        },
        spec={"op": "hep.render.cutflow_csv"},
        output_path=str(out),
    )

    with out.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["dataset"] for row in rows] == ["data", "dy"]
    assert [row["n"] for row in rows] == ["10", "20"]


def test_cutflow_csv_renderer_rejects_invalid_cutflow(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="'cuts' list"):
        run_cutflow_csv_render(
            {"not": "a cutflow"},
            spec={"op": "hep.render.cutflow_csv"},
            output_path=str(tmp_path / "cutflow.csv"),
        )
