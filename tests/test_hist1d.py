from __future__ import annotations

from pathlib import Path
from typing import Any

import hist
import pytest

from fasthep_render.hist import hist1d as hist1d_module
from fasthep_render.hist.hist1d import run_hist1d_render


def _dataset_hist(datasets: list[str]) -> hist.Hist:
    h: hist.Hist = hist.Hist(
        hist.axis.StrCategory(datasets, name="dataset", label="Dataset"),
        hist.axis.Regular(5, 0.0, 5.0, name="x", label="x"),
    )
    for i, ds in enumerate(datasets):
        h.fill(dataset=ds, x=[0.5 + i % 4])
    return h


def _plain_hist() -> hist.Hist:
    h: hist.Hist = hist.Hist(hist.axis.Regular(5, 0.0, 5.0, name="x", label="x"))
    h.fill([0.5, 1.5])
    return h


def _spec(**extra: Any) -> dict[str, Any]:
    spec = {
        "figure": {"size": [4, 3], "dpi": 80},
        "axes": {"x": {"name": "x", "label": "x"}, "y": {"name": "events"}},
        "style": {"experiment": "CMS"},
    }
    spec.update(extra)
    return spec


@pytest.mark.parametrize(
    ("histogram", "expected_data"),
    [
        (_dataset_hist(["data", "mc"]), True),
        (_dataset_hist(["signal", "background"]), False),
        (_plain_hist(), False),
    ],
)
def test_hist1d_experiment_label_data_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    histogram: hist.Hist,
    expected_data: bool,
) -> None:
    calls: list[bool] = []

    def fake_label_experiment(
        experiment: str, *, ax: Any, data: bool, lumi: float | None = None
    ) -> None:
        del experiment, ax, lumi
        calls.append(data)

    monkeypatch.setattr(hist1d_module, "label_experiment", fake_label_experiment)

    run_hist1d_render(
        histogram,
        spec=_spec(),
        output_path=str(tmp_path / "hist1d.png"),
    )

    assert calls == [expected_data]


def test_hist1d_mc_auto_colours_do_not_shift_when_data_is_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    colors_with_data = _histplot_colors(
        tmp_path / "with_data.png",
        monkeypatch,
        _dataset_hist(["data", "zjets", "ttbar"]),
    )
    colors_without_data = _histplot_colors(
        tmp_path / "without_data.png",
        monkeypatch,
        _dataset_hist(["zjets", "ttbar"]),
    )

    assert colors_with_data["zjets"] == colors_without_data["zjets"] == "#111111"
    assert colors_with_data["ttbar"] == colors_without_data["ttbar"] == "#222222"


def test_hist1d_explicit_dataset_colours_take_precedence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    colors = _histplot_colors(
        tmp_path / "explicit.png",
        monkeypatch,
        _dataset_hist(["zjets", "ttbar"]),
        datasets={
            "zjets": {"color": "gold", "label": "Z+jets"},
            "ttbar": {"color": "navy", "label": "ttbar"},
        },
    )

    assert colors["Z+jets"] == "gold"
    assert colors["ttbar"] == "navy"


def _histplot_colors(
    output_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    histogram: hist.Hist,
    *,
    datasets: dict[str, dict[str, str]] | None = None,
) -> dict[str, str | None]:
    calls: list[tuple[str, str | None]] = []

    def fake_histplot(*args: Any, **kwargs: Any) -> None:
        del args
        label = kwargs.get("label")
        if label is not None:
            calls.append((str(label), kwargs.get("color")))

    monkeypatch.setattr(hist1d_module.mh, "histplot", fake_histplot)
    monkeypatch.setattr(hist1d_module, "label_experiment", lambda *args, **kwargs: None)
    monkeypatch.setattr(hist1d_module.plt.Axes, "legend", lambda *args, **kwargs: None)

    run_hist1d_render(
        histogram,
        spec=_spec(
            style={
                "experiment": "CMS",
                "color_cycle": ["#111111", "#222222"],
                "datasets": datasets or {},
            },
        ),
        output_path=str(output_path),
    )

    return dict(calls)
