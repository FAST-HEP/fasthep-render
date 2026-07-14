from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Any, Literal

import matplotlib.pyplot as plt
import mplhep as mh
from hepflow.model.issues import FlowIssue, IssueLevel
from mplhep.comp import data_model

from fasthep_render.api import run_render_sink
from fasthep_render.hist.common import (
    auto_legend_ncol,
    find_dataset_axis_name,
    get_dataset_categories,
    label_experiment,
    resolve_color_for_dataset,
    resolve_label,
)
from fasthep_render.hist.inputs import resolve_single_hist_input
from fasthep_render.model import RenderOutcome, RenderStatus
from fasthep_render.render_types import RenderCommonSpec, RenderTypeSpec

DATA_MC_RENDER_SPEC = {
    "name": "hep.render.data_mc",
    "kind": "sink",
    "version": "1.0",
    "params": {
        "spec": {"type": "mapping", "required": False},
        "out": {"type": "string", "required": False},
    },
    "result": {"kind": "artifact", "format": "png"},
}


@dataclass(frozen=True)
class DataMcParams:
    data: str = "data"
    backgrounds: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)

    include_signals_in_stack: bool = True
    show_mc_uncertainty: bool = True
    stack: bool = True
    stack_order: Literal["legend", "reverse_legend"] = "reverse_legend"
    ratio: bool = True

    histtype_mc: Literal["fill", "step", "bar"] = "fill"
    histtype_signal: Literal["step", "fill", "bar"] = "step"

    legend_auto_ncol_threshold: int = 5
    legend_max_ncol: int = 4

    ratio_ylim: tuple[float, float] = (0.5, 1.5)
    ratio_ylabel: str = "Data/MC"


def parse_data_mc_params(spec_dict: dict[str, Any]) -> DataMcParams:
    return DataMcParams(**dict(spec_dict.get("data_mc") or {}))


def validate_data_mc_params(
    common: RenderCommonSpec,
    params: DataMcParams,
    context: dict[str, Any],
) -> list[FlowIssue]:
    del common
    issues: list[FlowIssue] = []

    available = set(context.get("available_datasets") or [])
    needed = [params.data, *list(params.backgrounds), *list(params.signals)]
    missing = sorted(x for x in needed if x not in available)

    if missing:
        issues.append(
            FlowIssue(
                level=IssueLevel.ERROR,
                code="RENDER_SPEC_MISSING_DATASETS",
                message="data_mc renderer references datasets not available after transforms",
                meta={"missing": missing, "available": sorted(available)},
            )
        )
    return issues


DATA_MC_RENDER_TYPE = RenderTypeSpec(
    parse_params=parse_data_mc_params,
    validate=validate_data_mc_params,
    resolve_input=resolve_single_hist_input,
)


def run_data_mc_render(target: Any, **kwargs: Any):
    return run_render_sink(
        op="hep.render.data_mc",
        render_type=DATA_MC_RENDER_TYPE,
        handler=render_data_mc,
        target=target,
        **kwargs,
    )


def render_data_mc(
    product: dict[str, Any],
    common: RenderCommonSpec,
    params: DataMcParams,
    ctx: dict[str, Any],
) -> RenderOutcome:
    h = product["hist"]
    out_png = ctx["output_path"]

    ds_axis = find_dataset_axis_name(h)
    if ds_axis is None:
        msg = "data_mc render requires a category axis named 'dataset' or 'dataset_name'"
        raise ValueError(msg)
    available = set(get_dataset_categories(h))

    data_id = params.data
    bkg_ids = list(params.backgrounds or [])
    sig_ids = list(params.signals or [])

    exp = (common.style.experiment or "").strip()
    if exp:
        with contextlib.suppress(Exception):
            mh.style.use(exp)

    def get_ds_hist(ds: str) -> Any | None:
        if ds not in available:
            return None
        return h[{ds_axis: ds}] if ds_axis else None

    def get_dataset_style(ds: str):
        return (common.style.datasets or {}).get(ds)

    def is_stackable(ds: str) -> bool:
        if ds == data_id:
            return False

        ds_style = get_dataset_style(ds)
        if ds_style is not None and ds_style.stack is not None:
            return bool(ds_style.stack)

        if ds in bkg_ids:
            return True
        if ds in sig_ids:
            return bool(params.include_signals_in_stack)
        return False

    legend_order: list[str] = []
    if data_id:
        legend_order.append(data_id)
    legend_order.extend(sig_ids)
    legend_order.extend(bkg_ids)
    legend_order = [ds for ds in legend_order if ds in available]

    if data_id not in available:
        msg = f"data_mc: data dataset '{data_id}' not present in histogram categories: {sorted(available)}"
        raise ValueError(
            msg
        )

    hist_map: dict[str, Any] = {}
    label_map: dict[str, str] = {}
    color_map: dict[str, str | None] = {}

    mc_color_idx = 0
    for ds in legend_order:
        hh = get_ds_hist(ds)
        if hh is None:
            continue
        hist_map[ds] = hh
        label_map[ds] = resolve_label(common, ds)

        is_data = ds == data_id
        color_map[ds] = resolve_color_for_dataset(
            common,
            ds,
            is_data=is_data,
            mc_index=mc_color_idx if not is_data else 0,
        )
        if not is_data:
            mc_color_idx += 1

    h_data = hist_map[data_id]

    stack_draw_order = [ds for ds in legend_order if is_stackable(ds)]
    if params.stack and params.stack_order == "reverse_legend":
        stack_draw_order = list(reversed(stack_draw_order))

    overlay_order = [
        ds for ds in legend_order
        if ds != data_id and ds not in stack_draw_order
    ]

    figsize = tuple(common.figure.size)
    dpi = int(common.figure.dpi)

    if params.stack:
        stacked_components = [hist_map[ds] for ds in stack_draw_order]
        stacked_labels = [label_map[ds] for ds in stack_draw_order]
        stacked_colors = [color_map[ds] for ds in stack_draw_order]

        fig, ax_main, ax_ratio = data_model(
            data_hist=h_data,
            stacked_components=stacked_components,
            stacked_labels=stacked_labels,
            stacked_colors=stacked_colors,
            xlabel=common.axes.x.label or common.axes.x.name,
            ylabel=common.axes.y.label or "Events",
        )
        fig.set_size_inches(figsize)
        fig.set_dpi(dpi)

        for ds in overlay_order:
            hh = hist_map[ds]
            histtype = params.histtype_signal if ds in sig_ids else "step"
            mh.histplot(
                hh,
                ax=ax_main,
                label=label_map[ds],
                histtype=histtype,
                color=color_map[ds],
            )
    else:
        fig = plt.figure(figsize=figsize, dpi=dpi)
        ax_main = fig.add_subplot(1, 1, 1)
        ax_ratio = None

        for ds in overlay_order + stack_draw_order:
            hh = hist_map[ds]
            histtype = params.histtype_signal if ds in sig_ids else "step"
            mh.histplot(
                hh,
                ax=ax_main,
                label=label_map[ds],
                histtype=histtype,
                color=color_map[ds],
            )

        mh.histplot(
            h_data,
            ax=ax_main,
            label=label_map[data_id],
            histtype="errorbar",
            color=color_map[data_id] or "black",
        )

    if common.axes.y.scale == "log":
        ax_main.set_yscale("log")

    if common.axes.x.limits:
        ax_main.set_xlim(*common.axes.x.limits)
    if common.axes.y.limits:
        ax_main.set_ylim(*common.axes.y.limits)

    if ax_ratio is not None and params.ratio:
        ax_ratio.set_ylabel(params.ratio_ylabel)
        ax_ratio.set_ylim(*params.ratio_ylim)

    handles, labels = ax_main.get_legend_handles_labels()
    handle_by_label = {lab: hnd for hnd, lab in zip(handles, labels, strict=False)}

    ordered_labels = [label_map[ds] for ds in legend_order if ds in hist_map]
    ordered_handles = [handle_by_label[lab] for lab in ordered_labels if lab in handle_by_label]

    n_entries = len(ordered_handles)
    ncol = auto_legend_ncol(
        n_entries=n_entries,
        ncol=int(common.legend.ncol) if common.legend.ncol is not None else None,
        ncol_threshold=params.legend_auto_ncol_threshold,
        max_ncol=params.legend_max_ncol,
    )
    ax_main.legend(
        ordered_handles,
        ordered_labels[: len(ordered_handles)],
        loc=common.legend.loc,
        ncol=ncol,
        frameon=common.legend.frameon,
    )

    label_experiment(exp, ax=ax_main, data=True, lumi=common.style.lumi)

    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)

    return RenderOutcome(
        status=RenderStatus.RENDERED,
        message=None,
        meta={"renderer": "data_mc", "output": out_png},
    )
