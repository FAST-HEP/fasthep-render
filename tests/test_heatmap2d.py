from __future__ import annotations

import hist

from fasthep_render.sinks.heatmap2d import run_heatmap2d_render


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
