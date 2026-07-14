from __future__ import annotations

import contextlib
from dataclasses import dataclass
from typing import Any, Literal

import matplotlib.pyplot as plt
import mplhep as mh
from hepflow.model.issues import FlowIssue

from fasthep_render.api import run_render_sink
from fasthep_render.hist.common import (
    auto_legend_ncol,
    label_experiment,
    resolve_color_for_dataset,
    resolve_label,
)
from fasthep_render.hist.inputs import resolve_single_hist_input
from fasthep_render.model import RenderOutcome, RenderStatus
from fasthep_render.render_types import RenderCommonSpec, RenderTypeSpec

HIST1D_RENDER_SPEC = {
    "name": "hep.render.hist1d",
    "kind": "sink",
    "version": "1.0",
    "params": {
        "spec": {"type": "mapping", "required": False},
        "out": {"type": "string", "required": False},
    },
    "result": {"kind": "artifact", "format": "png"},
}


@dataclass(frozen=True)
class Hist1DParams:
    overlay: bool = True
    histtype: Literal["step", "fill", "errorbar"] = "step"
    sort_datasets: Literal["none", "data_first"] = "data_first"


def parse_hist1d_params(spec_dict: dict[str, Any]) -> Hist1DParams:
    return Hist1DParams(**dict(spec_dict.get("hist1d") or {}))


def validate_hist1d_params(
    common: RenderCommonSpec,
    params: Hist1DParams,
    context: dict[str, Any],
) -> list[FlowIssue]:
    del common, params, context
    return []


HIST1D_RENDER_TYPE = RenderTypeSpec(
    parse_params=parse_hist1d_params,
    validate=validate_hist1d_params,
    resolve_input=resolve_single_hist_input,
)


def run_hist1d_render(target: Any, **kwargs: Any):
    return run_render_sink(
        op="hep.render.hist1d",
        render_type=HIST1D_RENDER_TYPE,
        handler=render_hist1d,
        target=target,
        **kwargs,
    )


def _find_dataset_axis_name(h: Any) -> str | None:
    names = [getattr(ax, "name", None) for ax in getattr(h, "axes", [])]
    if "dataset" in names:
        return "dataset"
    if "dataset_name" in names:
        return "dataset_name"
    return None


def _find_physics_axis_name(h: Any, dataset_axis_name: str | None) -> str:
    names = [getattr(ax, "name", None) for ax in getattr(h, "axes", [])]
    physics = [n for n in names if n and n != dataset_axis_name]
    if len(physics) != 1:
        msg = f"hist1d renderer requires exactly one non-dataset axis, found {physics}"
        raise ValueError(
            msg
        )
    return physics[0]


def render_hist1d(
    product: dict[str, Any],
    common: RenderCommonSpec,
    params: Hist1DParams,
    ctx: dict[str, Any],
) -> RenderOutcome:
    h = product["hist"]
    out_path = ctx["output_path"]

    exp = (common.style.experiment or "").strip()
    if exp:
        with contextlib.suppress(Exception):
            mh.style.use(exp)

    dataset_axis_name = _find_dataset_axis_name(h)
    xname = _find_physics_axis_name(h, dataset_axis_name)

    fig, ax = plt.subplots(
        figsize=tuple(common.figure.size),
        dpi=int(common.figure.dpi),
    )

    if dataset_axis_name is None:
        mh.histplot(
            h,
            ax=ax,
            histtype=params.histtype,
        )
    else:
        datasets = list(h.axes[dataset_axis_name])

        if params.sort_datasets == "data_first" and "data" in datasets:
            datasets = ["data"] + [d for d in datasets if d != "data"]

        for i, ds in enumerate(datasets):
            h_ds = h[{dataset_axis_name: ds}]
            label = resolve_label(common, str(ds))
            color = resolve_color_for_dataset(
                common,
                str(ds),
                is_data=(str(ds) == "data"),
                mc_index=i,
            )
            mh.histplot(
                h_ds,
                ax=ax,
                label=label,
                histtype=params.histtype,
                color=color,
            )

        n_entries = len(datasets)
        ncol = auto_legend_ncol(
            n_entries=n_entries,
            ncol=int(common.legend.ncol) if common.legend.ncol is not None else None,
            ncol_threshold=5,
            max_ncol=4,
        )
        ax.legend(
            loc=common.legend.loc,
            ncol=ncol,
            frameon=common.legend.frameon,
        )

    ax.set_xlabel(common.axes.x.label or xname)
    ax.set_ylabel(common.axes.y.label or "Events")

    if common.axes.y.scale == "log":
        ax.set_yscale("log")

    if common.axes.x.limits:
        ax.set_xlim(*common.axes.x.limits)
    if common.axes.y.limits:
        ax.set_ylim(*common.axes.y.limits)

    label_experiment(exp, ax=ax, data=True, lumi=common.style.lumi)

    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)

    return RenderOutcome(
        status=RenderStatus.RENDERED,
        message=None,
        meta={"renderer": "hist1d", "output": out_path},
    )
