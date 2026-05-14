from __future__ import annotations

from math import ceil
from typing import Any

import mplhep as mh
from hepflow.model.render_types import RenderCommonSpec


def auto_legend_ncol(
    n_entries: int, ncol: int | None = None, ncol_threshold: int = 5, max_ncol=4
) -> int:
    """
    Determines number of columns for a legend

    If `ncol` is set, use ncol.
    If `n_entries` is below the threshold `ncol_threshold` - return 1
    Otherwise produce a wide legend with less columns than `max_ncol`
    """
    if ncol is not None:
        return ncol
    if n_entries <= ncol_threshold:
        return 1
    # simple heuristic: 2 rows if possible, capped
    ncol = ceil(n_entries / 2)
    return min(ncol, max_ncol)


def find_dataset_axis_name(h: Any) -> str:
    for ax in getattr(h, "axes", []):
        if getattr(ax, "name", None) in ("dataset", "dataset_name"):
            return str(ax.name)
    msg = "data_mc render requires a category axis named 'dataset' or 'dataset_name'"
    raise ValueError(
        msg
    )


def resolve_color_for_dataset(
    spec: RenderCommonSpec, ds: str, *, is_data: bool, mc_index: int
) -> str:
    ds_style = (spec.style.datasets or {}).get(ds)
    if ds_style and ds_style.color:
        return ds_style.color
    if is_data:
        return "black"
    cyc = spec.style.color_cycle or []
    if not cyc:
        return None  # let mplhep/mpl choose
    return cyc[mc_index % len(cyc)]


def resolve_label(spec: RenderCommonSpec, ds: str) -> str:
    ds_style = (spec.style.datasets or {}).get(ds)
    if ds_style and ds_style.label:
        return ds_style.label
    return ds


def label_experiment(
    experiment: str, *, ax: Any, data: bool, lumi: float | None = None
) -> None:
    exp = (experiment or "").strip().lower()
    if exp == "cms":
        mh.cms.label(data=data, lumi=lumi, ax=ax)
    elif exp == "atlas":
        mh.atlas.label(data=data, lumi=lumi, ax=ax)
    else:
        # unknown experiment: no label
        return


def get_dataset_categories(h: Any) -> list[str]:
    for ax in getattr(h, "axes", []):
        if getattr(ax, "name", None) in ("dataset", "dataset_name"):
            try:
                return list(ax)
            except Exception:
                return []
    return []
