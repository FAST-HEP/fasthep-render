from __future__ import annotations

from math import ceil, sqrt
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import mplhep as mh
from hepflow.model.render import RenderOutcome, RenderStatus
from hepflow.model.render_types import RenderCommonSpec

from fasthep_render.types.heatmap2d import Heatmap2DParams


def render_heatmap2d(
    product: dict[str, Any],
    common: RenderCommonSpec,
    params: Heatmap2DParams,
    ctx: dict[str, Any],
) -> RenderOutcome:

    h = product["hist"]
    out_path = ctx["output_path"]
    output_dir = ctx.get("output_dir")
    if output_dir is None:
        output_dir = str(Path(out_path).with_suffix(""))

    # Resolve axes
    xname = common.axes.x.name
    yname = common.axes.y.name
    if not (xname and yname):
        msg = "heatmap2d renderer requires axes.x.name and axes.y.name"
        raise ValueError(msg)

    ax_names = [getattr(ax, "name", None) for ax in getattr(h, "axes", [])]
    ds_axis = (
        "dataset"
        if "dataset" in ax_names
        else ("dataset_name" if "dataset_name" in ax_names else None)
    )

    # No dataset axis: just render the projected 2D histogram directly
    if ds_axis is None:
        fig, ax = plt.subplots(
            figsize=tuple(common.figure.size),
            dpi=int(common.figure.dpi),
        )
        mh.hist2dplot(h.project(xname, yname), ax=ax)
        ax.set_xlabel(common.axes.x.label or xname)
        ax.set_ylabel(common.axes.y.label or yname)

        fig.savefig(out_path, bbox_inches="tight")
        plt.close(fig)
        return RenderOutcome(
            status=RenderStatus.RENDERED,
            message=None,
            meta={"output": out_path},
        )

    datasets = list(h.axes[ds_axis])

    if not datasets:
        return RenderOutcome(
            status=RenderStatus.SKIPPED,
            message="No dataset categories in histogram",
            meta={"output": out_path},
        )

    # Per-dataset output directory
    if params.per_dataset:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        written: list[str] = []
        for ds in datasets:
            h_ds = h[{ds_axis: ds}].project(xname, yname)

            fig, ax = plt.subplots(
                figsize=tuple(common.figure.size),
                dpi=int(common.figure.dpi),
            )
            mh.hist2dplot(h_ds, ax=ax)
            ax.set_title(str(ds))
            ax.set_xlabel(common.axes.x.label or xname)
            ax.set_ylabel(common.axes.y.label or yname)

            ds_file = out_dir / f"{ds}.png"
            fig.savefig(ds_file, bbox_inches="tight")
            plt.close(fig)
            written.append(str(ds_file))

        return RenderOutcome(
            status=RenderStatus.RENDERED,
            message=None,
            meta={
                "output_dir": str(out_dir),
                "outputs": written,
                "count": len(written),
            },
        )

    # Combined grid plot
    n = len(datasets)
    ncols = params.max_cols or ceil(sqrt(n))
    ncols = max(1, min(ncols, n))
    nrows = (n + ncols - 1) // ncols

    # Reorder to have data first if present
    if "data" in datasets:
        datasets = ["data"] + [d for d in datasets if d != "data"]

    fig, axes = plt.subplots(
        nrows=nrows,
        ncols=ncols,
        figsize=tuple(common.figure.size),
        dpi=int(common.figure.dpi),
    )
    axes = axes.reshape(-1) if hasattr(axes, "reshape") else [axes]

    for i, ax in enumerate(axes[:n]):
        row = i // ncols
        col = i % ncols

        if row != nrows - 1:
            ax.set_xticklabels([])
        if col != 0:
            ax.set_yticklabels([])

    for i, ds in enumerate(datasets):
        ax = axes[i]
        h_ds = h[{ds_axis: ds}].project(xname, yname)
        mh.hist2dplot(h_ds, ax=ax)
        ax.set_title(str(ds))
        ax.set_xlabel("")
        ax.set_ylabel("")

    # Hide unused axes
    for j in range(n, len(axes)):
        axes[j].axis("off")

    fig.subplots_adjust(wspace=0.55, hspace=0.35)
    fig.supxlabel(common.axes.x.label or xname)
    fig.supylabel(common.axes.y.label or yname)

    fig.savefig(
        out_path if str(out_path).endswith(".png") else f"{out_path}.png",
        bbox_inches="tight",
    )
    plt.close(fig)

    return RenderOutcome(
        status=RenderStatus.RENDERED,
        message=None,
        meta={"output": out_path},
    )
