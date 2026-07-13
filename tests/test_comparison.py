from __future__ import annotations

import hist
import numpy as np
import pytest

from fasthep_render.renderers.comparison import _normalise_hist_area
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


def test_comparison_area_normalise_scales_copies_and_variances(tmp_path) -> None:
    axis = hist.axis.Regular(3, 0.0, 3.0, name="x")
    reference = hist.Hist(axis, storage=hist.storage.Weight())
    target = hist.Hist(axis, storage=hist.storage.Weight())
    reference.fill([0.5, 1.5], weight=[2.0, 3.0])
    target.fill([0.5, 2.5], weight=[4.0, 6.0])
    reference_values = reference.values().copy()
    reference_variances = reference.variances().copy()
    out = tmp_path / "area.png"

    result = run_comparison_render(
        {"reference": reference, "target": target},
        spec={
            "axes": {"x": {"name": "x", "label": "x"}, "y": {"name": "area"}},
            "comparison": {
                "reference": "reference",
                "target": "target",
                "normalise": "area",
            },
        },
        output_path=str(out),
    )
    scaled = _normalise_hist_area(reference, label="reference", warnings=[])
    density = reference.density()
    scale = np.divide(
        density,
        reference_values,
        out=np.zeros_like(density, dtype=float),
        where=reference_values != 0,
    )

    assert result.metadata["normalise"] == "area"
    assert np.isclose(np.sum(scaled.values()), 1.0)
    assert np.allclose(scaled.values(), density)
    assert np.allclose(scaled.variances(), reference_variances * scale**2)
    assert np.allclose(reference.values(), reference_values)
    assert np.allclose(reference.variances(), reference_variances)


def test_comparison_area_normalise_warns_on_zero_integral() -> None:
    h: hist.Hist = hist.Hist(hist.axis.Regular(3, 0.0, 3.0, name="x"))
    warnings: list[dict[str, object]] = []

    out = _normalise_hist_area(h, label="reference", warnings=warnings)

    assert out is h
    assert warnings == [
        {
            "code": "COMPARISON_AREA_NORMALISE_ZERO_INTEGRAL",
            "message": (
                "Skipped area normalisation for reference histogram because "
                "the visible-bin integral is zero"
            ),
            "histogram": "reference",
            "integral": 0.0,
        }
    ]


def test_comparison_area_normalise_rejects_negative_integral() -> None:
    h = hist.Hist(
        hist.axis.Regular(2, 0.0, 2.0, name="x"),
        storage=hist.storage.Weight(),
    )
    h.fill([0.5], weight=[-2.0])

    with pytest.raises(ValueError, match="negative visible-bin integral"):
        _normalise_hist_area(h, label="target", warnings=[])
