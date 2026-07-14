from __future__ import annotations

import matplotlib as mpl

mpl.use("Agg")

import hist

from fasthep_render.hist.comparison import run_comparison_render
from fasthep_render.hist.hist1d import run_hist1d_render


def _hist1d() -> hist.Hist:
    h: hist.Hist = hist.Hist(hist.axis.Regular(5, 0, 5, name="x", label="x"))
    h.fill([0.5, 1.5, 1.5, 3.5])
    return h


def test_hist1d_render_writes_png(tmp_path) -> None:
    out = tmp_path / "hist1d.png"

    result = run_hist1d_render(
        _hist1d(),
        spec={"axes": {"x": {"name": "x", "label": "x"}, "y": {"name": "y"}}},
        output_path=str(out),
    )

    assert result.path == str(out)
    assert out.is_file()
    assert out.stat().st_size > 0


def test_comparison_render_writes_png(tmp_path) -> None:
    out = tmp_path / "comparison.png"

    result = run_comparison_render(
        {"reference": _hist1d(), "target": _hist1d()},
        spec={
            "axes": {"x": {"name": "x", "label": "x"}, "y": {"name": "y"}},
            "comparison": {
                "reference": "reference",
                "target": "target",
            },
        },
        output_path=str(out),
    )

    assert result.path == str(out)
    assert out.is_file()
    assert out.stat().st_size > 0
