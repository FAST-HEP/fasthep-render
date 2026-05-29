from __future__ import annotations

import hist

from fasthep_render.sinks.comparison import run_comparison_render


def test_comparison_render_writes_docs_ready_png(
    tmp_path, gaussian_comparison_pair: dict[str, hist.Hist]
) -> None:
    out = tmp_path / "comparison_mass.png"

    result = run_comparison_render(
        gaussian_comparison_pair,
        spec={
            "figure": {"size": (7.0, 5.0), "dpi": 120},
            "axes": {
                "x": {"name": "mass", "label": "Observable"},
                "y": {"name": "events", "label": "Events"},
            },
            "comparison": {
                "reference": "reference",
                "target": "target",
                "reference_label": "Nominal",
                "target_label": "Weighted",
                "comparison": "ratio",
                "comparison_ylabel": "Weighted / nominal",
            },
        },
        output_path=str(out),
    )

    assert result.path == str(out)
    assert out.is_file()
    assert out.stat().st_size > 0
