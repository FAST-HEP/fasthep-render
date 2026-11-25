from __future__ import annotations

from pathlib import Path

import hist

from fasthep_render.hist.heatmap2d import run_heatmap2d_render


def test_heatmap2d_render_writes_png(tmp_path, hist2d: hist.Hist) -> None:
    out = tmp_path / "heatmap2d_pt_eta.png"

    result = run_heatmap2d_render(
        hist2d,
        spec={
            "figure": {"size": (7.0, 5.0), "dpi": 120},
            "axes": {
                "x": {"name": "pt", "label": "pT [GeV]"},
                "y": {"name": "eta", "label": "eta"},
            },
            "heatmap2d": {"per_dataset": False, "cbar": True},
        },
        output_path=str(out),
    )

    assert result.path == str(out)
    assert out.is_file()
    assert out.stat().st_size > 0


def _per_dataset_spec(*, per_dataset: bool = True) -> dict:
    return {
        "figure": {"size": (4.0, 3.0), "dpi": 50},
        "axes": {"x": {"name": "pt", "label": "pT"}, "y": {"name": "eta", "label": "eta"}},
        "heatmap2d": {"per_dataset": per_dataset, "cbar": False},
    }


def _dataset_hist2d(datasets: list[str]) -> hist.Hist:
    h: hist.Hist = hist.Hist(
        hist.axis.StrCategory(datasets, name="dataset", growth=True),
        hist.axis.Regular(4, 0.0, 4.0, name="pt"),
        hist.axis.Regular(4, -2.0, 2.0, name="eta"),
    )
    for dataset in datasets:
        h.fill(dataset=dataset, pt=[1.0, 2.0], eta=[0.5, -0.5])
    return h


def test_per_dataset_heatmap_reports_one_result_per_file(tmp_path) -> None:
    out = tmp_path / "plots" / "heat.png"

    results = run_heatmap2d_render(
        _dataset_hist2d(["a", "b", "c"]),
        spec=_per_dataset_spec(),
        output_path=str(out),
    )

    assert isinstance(results, list)
    paths = [Path(result.path) for result in results]
    assert {path.name for path in paths} == {"a.png", "b.png", "c.png"}
    assert all(path.is_file() for path in paths)
    assert all(path.parent == tmp_path / "plots" / "heat" for path in paths)
    assert not out.exists()


def test_heatmap_without_dataset_categories_reports_no_file(tmp_path) -> None:
    out = tmp_path / "plots" / "heat.png"

    results = run_heatmap2d_render(
        _dataset_hist2d([]),
        spec=_per_dataset_spec(),
        output_path=str(out),
    )

    assert results == []
    assert not out.exists()
