from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import mplhep as mh
from mplhep.comp import data_model

from fasthep_render.common import (
    auto_legend_ncol,
    find_dataset_axis_name,
    get_dataset_categories,
    label_experiment,
    resolve_color_for_dataset,
    resolve_label,
)
from fasthep_render.model import (
    AxesSpec,
    DatasetStyle,
    RenderOutcome,
    RenderSpec,
    RenderStatus,
)


def _is_stackable(name: str, spec: RenderSpec) -> bool:
    dm = spec.data_mc
    assert dm is not None

    # data is never stacked
    if name == dm.data:
        return False

    ds_style = (spec.style.datasets or {}).get(name, DatasetStyle())

    # explicit style wins
    if ds_style.stack is not None:
        return bool(ds_style.stack)

    # fallback to current data_mc semantics
    if name in dm.backgrounds:
        return True
    if name in dm.signals:
        return bool(dm.include_signals_in_stack)
    return False


def _stack_draw_order(spec: RenderSpec, legend_order: list[str]) -> list[str]:
    dm = spec.data_mc
    assert dm is not None

    stackable = [name for name in legend_order if _is_stackable(name, spec)]
    if dm.stack_order == "reverse_legend":
        return list(reversed(stackable))
    return stackable


def render_data_mc(
    h: Any,
    spec: RenderSpec,
    out_png: str,
    **_kw,
) -> RenderOutcome:
    """
    Renders a data/MC comparison plot using mplhep.

    Ordering semantics:
    - legend order is defined by data_mc.{data,signals,backgrounds}
    - stackable entries are determined from DatasetStyle.stack if set,
      otherwise from legacy data_mc semantics
    - stack draw order is derived from legend order using data_mc.stack_order
    """
    if spec.data_mc is None:
        msg = "RenderSpec.plot='data_mc' requires spec.data_mc to be set"
        raise ValueError(msg)

    dm = spec.data_mc
    h_sel = h

    ds_axis = find_dataset_axis_name(h_sel)
    if ds_axis is None:
        msg = "data_mc render requires a category axis named 'dataset' or 'dataset_name'"
        raise ValueError(msg)
    available = set(get_dataset_categories(h_sel))

    data_id = dm.data
    bkg_ids = list(dm.backgrounds or [])
    sig_ids = list(dm.signals or [])

    exp = (spec.style.experiment or "").strip()
    if exp and exp in mh.style.__style_aliases__:
        mh.style.use(exp)

    def get_ds_hist(ds: str) -> Any | None:
        if ds not in available:
            return None
        return h_sel[{ds_axis: ds}] if ds_axis else None

    def get_dataset_style(ds: str):
        return (spec.style.datasets or {}).get(ds)

    def is_stackable(ds: str) -> bool:
        # data is never stacked
        if ds == data_id:
            return False

        ds_style = get_dataset_style(ds)
        if ds_style is not None and ds_style.stack is not None:
            return bool(ds_style.stack)

        # fallback to current data_mc semantics
        if ds in bkg_ids:
            return True
        if ds in sig_ids:
            return bool(dm.include_signals_in_stack)
        return False

    # ------------------------------------------------------------
    # Primary legend order
    # ------------------------------------------------------------
    legend_order: list[str] = list(spec.style.datasets.keys())
    # if data_id:
    #     legend_order.append(data_id)
    # legend_order.extend(sig_ids)
    # legend_order.extend(bkg_ids)

    # keep only categories that exist in the histogram
    legend_order = [ds for ds in legend_order if ds in available]

    if data_id not in available:
        msg = f"data_mc: data dataset '{data_id}' not present in histogram categories: {sorted(available)}"
        raise ValueError(
            msg
        )

    # ------------------------------------------------------------
    # Build hist map in legend order
    # ------------------------------------------------------------
    hist_map: dict[str, Any] = {}
    label_map: dict[str, str] = {}
    color_map: dict[str, str | None] = {}

    mc_color_idx = 0
    for ds in legend_order:
        hh = get_ds_hist(ds)
        if hh is None:
            continue
        hist_map[ds] = hh
        label_map[ds] = resolve_label(spec, ds)

        is_data = ds == data_id
        color_map[ds] = resolve_color_for_dataset(
            spec,
            ds,
            is_data=is_data,
            mc_index=mc_color_idx if not is_data else 0,
        )
        if not is_data:
            mc_color_idx += 1

    h_data = hist_map[data_id]

    # ------------------------------------------------------------
    # Determine stack draw order from legend order
    # ------------------------------------------------------------
    stack_draw_order = _stack_draw_order(spec, legend_order)

    # entries in legend order that are not stacked (excluding data)
    overlay_order = [
        ds for ds in legend_order
        if ds != data_id and ds not in stack_draw_order
    ]

    # ------------------------------------------------------------
    # Figure / axes
    # ------------------------------------------------------------
    axes = spec.axes or AxesSpec()
    figsize = tuple(spec.figure.size)
    dpi = int(spec.figure.dpi)

    # ------------------------------------------------------------
    # Stacked mode
    # ------------------------------------------------------------
    if dm.stack:
        stacked_components = [hist_map[ds] for ds in stack_draw_order]
        stacked_labels = [label_map[ds] for ds in stack_draw_order]
        stacked_colors = [color_map[ds] for ds in stack_draw_order]

        fig, ax_main, ax_ratio = data_model(
            data_hist=h_data,
            stacked_components=stacked_components,
            stacked_labels=stacked_labels,
            stacked_colors=stacked_colors,
            xlabel=axes.x.label or axes.x.name,
            ylabel=axes.y.label or "Events",
        )
        fig.set_size_inches(figsize)
        fig.set_dpi(dpi)

        # draw non-stacked overlays (typically signals if stack=False)
        for ds in overlay_order:
            hh = hist_map[ds]
            histtype = dm.histtype_signal if ds in sig_ids else "step"
            mh.histplot(
                hh,
                ax=ax_main,
                label=label_map[ds],
                histtype=histtype,
                color=color_map[ds],
            )

    # ------------------------------------------------------------
    # Unstacked mode
    # ------------------------------------------------------------
    else:
        fig = plt.figure(figsize=figsize, dpi=dpi)
        ax_main = fig.add_subplot(1, 1, 1)
        ax_ratio = None

        for ds in overlay_order + stack_draw_order:
            hh = hist_map[ds]
            histtype = dm.histtype_signal if ds in sig_ids else "step"
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

    # ------------------------------------------------------------
    # Axis scale / limits
    # ------------------------------------------------------------
    if axes.y.scale == "log":
        ax_main.set_yscale("log")

    if axes.x.limits:
        ax_main.set_xlim(*axes.x.limits)
    if axes.y.limits:
        ax_main.set_ylim(*axes.y.limits)

    if ax_ratio is not None and dm.ratio:
        ax_ratio.set_ylabel(dm.ratio_ylabel)
        ax_ratio.set_ylim(*dm.ratio_ylim)

    # ------------------------------------------------------------
    # Legend
    # Keep legend order stable and user-facing, independent of draw order
    # ------------------------------------------------------------
    handles, labels = ax_main.get_legend_handles_labels()
    handle_by_label = {lab: hnd for hnd, lab in zip(handles, labels, strict=False)}

    ordered_labels = [label_map[ds] for ds in legend_order if ds in hist_map]
    ordered_handles = [handle_by_label[lab] for lab in ordered_labels if lab in handle_by_label]

    n_entries = len(ordered_handles)
    ncol = auto_legend_ncol(
        n_entries=n_entries,
        ncol=int(spec.legend.ncol) if spec.legend.ncol is not None else None,
        ncol_threshold=dm.legend_auto_ncol_threshold,
        max_ncol=dm.legend_max_ncol,
    )
    ax_main.legend(
        ordered_handles,
        ordered_labels[: len(ordered_handles)],
        loc=spec.legend.loc,
        ncol=ncol,
        frameon=spec.legend.frameon,
    )

    label_experiment(exp, ax=ax_main, data=True, lumi=spec.style.lumi)

    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)

    return RenderOutcome(
        status=RenderStatus.RENDERED,
        message=None,
        meta={"renderer": "data_mc", "output": out_png},
    )
