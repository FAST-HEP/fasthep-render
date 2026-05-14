from __future__ import annotations

from conftest import DataMcBundle
from fasthep_render.impl.sinks.data_mc import run_data_mc_render


def test_data_mc_render_writes_stacked_png(
    tmp_path, data_mc_bundle: DataMcBundle
) -> None:
    out = tmp_path / "data_mc_mass.png"

    result = run_data_mc_render(
        data_mc_bundle.combined,
        spec={
            "figure": {"size": (7.0, 6.0), "dpi": 120},
            "axes": {
                "x": {"name": "mass", "label": "m(ll) [GeV]"},
                "y": {"name": "events", "label": "Events"},
            },
            "legend": {"loc": "upper right", "frameon": False},
            "style": {
                "experiment": None,
                "datasets": {
                    "data": {"label": "Observed", "kind": "data", "color": "black"},
                    "signal": {
                        "label": "Narrow signal",
                        "kind": "signal",
                        "color": "#d62728",
                        "stack": False,
                    },
                    "zjets": {
                        "label": "Z+jets",
                        "kind": "background",
                        "color": "#4e79a7",
                    },
                    "ttbar": {
                        "label": "ttbar",
                        "kind": "background",
                        "color": "#f28e2b",
                    },
                },
            },
            "data_mc": {
                "data": "data",
                "backgrounds": ["zjets", "ttbar"],
                "signals": ["signal"],
                "include_signals_in_stack": False,
                "stack": True,
                "ratio": True,
            },
        },
        output_path=str(out),
    )

    assert result.path == str(out)
    assert out.is_file()
    assert out.stat().st_size > 0
