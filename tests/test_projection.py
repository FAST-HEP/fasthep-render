from __future__ import annotations

import hist
from hepflow.compiler.profiles import load_profile_config

from fasthep_render.hist.project import run_project_render


def test_project_render_writes_projected_histogram_png(
    tmp_path, hist2d: hist.Hist
) -> None:
    out = tmp_path / "projected_pt.png"
    profile = load_profile_config("fasthep_render:registry", project_root=tmp_path)

    result = run_project_render(
        hist2d,
        spec={
            "figure": {"size": (7.0, 5.0), "dpi": 120},
            "axes": {
                "x": {"name": "pt", "label": "pT [GeV]"},
                "y": {"name": "events", "label": "Events"},
            },
            "project": {
                "axis": "pt",
                "then": {
                    "op": "hep.render.hist1d",
                    "axes": {
                        "x": {"name": "pt", "label": "pT [GeV]"},
                        "y": {"name": "events", "label": "Events"},
                    },
                    "hist1d": {"histtype": "step"},
                },
            },
        },
        output_path=str(out),
        ctx={"plan": {"registry": profile["registry"]}},
    )

    assert result.path == str(out)
    assert out.is_file()
    assert out.stat().st_size > 0
