from __future__ import annotations

import hist
import pytest

from conftest import DataMcBundle
from fasthep_render.hist.data_mc import run_data_mc_render


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


def test_data_mc_render_requires_configured_data_category(
    tmp_path, data_mc_bundle: DataMcBundle
) -> None:
    out = tmp_path / "missing_data.png"
    h_no_data: hist.Hist = hist.Hist(
        hist.axis.StrCategory(
            ["zjets", "ttbar", "signal"],
            name="dataset",
            label="Dataset",
        ),
        *data_mc_bundle.combined.axes[1:],
        storage=hist.storage.Weight(),
    )

    with pytest.raises(ValueError, match="data dataset 'data' not present"):
        run_data_mc_render(
            h_no_data,
            spec={
                "axes": {
                    "x": {"name": "mass", "label": "m(ll) [GeV]"},
                    "y": {"name": "events", "label": "Events"},
                },
                "style": {"experiment": None},
                "data_mc": {
                    "data": "data",
                    "backgrounds": ["zjets", "ttbar"],
                    "signals": ["signal"],
                },
            },
            output_path=str(out),
        )
