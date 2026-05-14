from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import hist
import matplotlib as mpl
import numpy as np
import pytest

mpl.use("Agg")


@dataclass(frozen=True)
class DataMcBundle:
    data: hist.Hist
    backgrounds: dict[str, hist.Hist]
    signal: hist.Hist | None
    combined: hist.Hist


@pytest.fixture
def gaussian_hist1d() -> hist.Hist:
    rng = np.random.default_rng(1729)
    h: hist.Hist = hist.Hist(
        hist.axis.Regular(48, 60.0, 120.0, name="mass", label="m(ll) [GeV]")
    )
    h.fill(rng.normal(loc=91.2, scale=8.5, size=12_000))
    return h


@pytest.fixture
def gaussian_comparison_pair() -> dict[str, hist.Hist]:
    axis = hist.axis.Regular(48, 60.0, 120.0, name="mass", label="m(ll) [GeV]")
    nominal: hist.Hist = hist.Hist(axis)
    shifted: hist.Hist = hist.Hist(axis)
    rng = np.random.default_rng(1730)
    nominal.fill(rng.normal(loc=91.2, scale=8.5, size=12_000))
    shifted.fill(rng.normal(loc=92.4, scale=8.9, size=12_000))
    return {"reference": nominal, "target": shifted}


@pytest.fixture
def poisson_count_hist1d() -> hist.Hist:
    rng = np.random.default_rng(31415)
    h: hist.Hist = hist.Hist(
        hist.axis.Regular(40, 0.0, 200.0, name="pt", label="pT [GeV]")
    )
    h.fill(rng.gamma(shape=2.0, scale=24.0, size=8_000))
    counts = rng.poisson(h.values())
    out: hist.Hist = hist.Hist(*h.axes)
    out[...] = counts
    return out


@pytest.fixture
def weighted_hist1d() -> hist.Hist:
    rng = np.random.default_rng(2718)
    h: hist.Hist = hist.Hist(
        hist.axis.Regular(44, -4.0, 4.0, name="eta", label="eta"),
        storage=hist.storage.Weight(),
    )
    values = rng.normal(loc=0.0, scale=1.25, size=10_000)
    weights = rng.uniform(0.6, 1.4, size=values.size)
    h.fill(values, weight=weights)
    return h


@pytest.fixture
def dataset_axis_hist1d() -> hist.Hist:
    rng = np.random.default_rng(1618)
    h: hist.Hist = hist.Hist(
        hist.axis.StrCategory(
            ["data", "zjets", "ttbar", "signal"],
            name="dataset",
            label="Dataset",
        ),
        hist.axis.Regular(50, 60.0, 120.0, name="mass", label="m(ll) [GeV]"),
        storage=hist.storage.Weight(),
    )
    h.fill(dataset="zjets", mass=rng.normal(88.0, 12.0, 9_000), weight=1.1)
    h.fill(dataset="ttbar", mass=rng.normal(78.0, 18.0, 3_500), weight=0.7)
    h.fill(dataset="signal", mass=rng.normal(91.2, 2.4, 1_200), weight=0.18)
    h.fill(dataset="data", mass=rng.normal(87.5, 13.5, 12_500))
    return h


@pytest.fixture
def hist2d() -> hist.Hist:
    rng = np.random.default_rng(4242)
    h: hist.Hist = hist.Hist(
        hist.axis.Regular(32, 0.0, 180.0, name="pt", label="pT [GeV]"),
        hist.axis.Regular(28, -3.0, 3.0, name="eta", label="eta"),
    )
    pt = rng.gamma(shape=2.4, scale=26.0, size=18_000)
    eta = rng.normal(loc=0.0, scale=1.05, size=18_000)
    h.fill(pt=pt, eta=eta)
    return h


@pytest.fixture
def data_mc_bundle(dataset_axis_hist1d: hist.Hist) -> DataMcBundle:
    return DataMcBundle(
        data=cast(hist.Hist, dataset_axis_hist1d[{"dataset": "data"}]),
        backgrounds={
            "zjets": cast(hist.Hist, dataset_axis_hist1d[{"dataset": "zjets"}]),
            "ttbar": cast(hist.Hist, dataset_axis_hist1d[{"dataset": "ttbar"}]),
        },
        signal=cast(hist.Hist, dataset_axis_hist1d[{"dataset": "signal"}]),
        combined=dataset_axis_hist1d,
    )
