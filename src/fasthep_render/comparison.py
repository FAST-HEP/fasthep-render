from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import mplhep as mh

from fasthep_render.model import RenderArtifact, RenderOutcome, RenderSpec, RenderStatus


def _strip_dataset_axis_for_comparison(h):
    ax_names = [getattr(ax, "name", None) for ax in getattr(h, "axes", [])]
    if "dataset" in ax_names:
        keep = [n for n in ax_names if n != "dataset"]
        return h.project(*keep)
    if "dataset_name" in ax_names:
        keep = [n for n in ax_names if n != "dataset_name"]
        return h.project(*keep)
    return h


def render_comparison(
    products: dict[str, Any],
    spec: RenderSpec,
    out_path: str,
    input_paths: dict[str, str] | None = None,
) -> RenderOutcome:
    if spec.plot != "comparison" or spec.comparison is None:
        msg = "render_comparison requires RenderSpec(plot='comparison')"
        raise ValueError(msg)

    cmp = spec.comparison

    h1 = _strip_dataset_axis_for_comparison(products["reference"])
    h2 = _strip_dataset_axis_for_comparison(products["target"])
    if h1 is None or h2 is None:
        msg = "render_comparison requires products['reference'] and products['target']"
        raise ValueError(
            msg
        )

    figsize = tuple(spec.figure.size)
    dpi = int(spec.figure.dpi)

    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

    mh.comp.comparison(
        h1,
        h2,
        ax=ax,
        xlabel=(spec.axes.x.label if spec.axes and spec.axes.x else None) or "",
        h1_label=cmp.reference_label,
        h2_label=cmp.target_label,
        comparison=cmp.comparison,
        comparison_ylabel=cmp.comparison_ylabel,
        comparison_ylim=cmp.comparison_ylim,
        w2method=cmp.w2method,
        flow=cmp.flow,
    )

    # Main y-axis styling
    # if spec.axes and spec.axes.y:
    #     if spec.axes.y.label:
    #         ax.set_ylabel(spec.axes.y.label)
    #     if spec.axes.y.scale:
    #         ax.set_yscale(spec.axes.y.scale)
    #     if spec.axes.y.limits:
    #         ax.set_ylim(*spec.axes.y.limits)

    if spec.axes and spec.axes.x and spec.axes.x.limits:
        ax.set_xlim(*spec.axes.x.limits)

    # Legend
    if spec.legend:
        handles, _labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(
                loc=spec.legend.loc,
                ncol=spec.legend.ncol or 1,
                frameon=spec.legend.frameon,
                fontsize=spec.legend.fontsize,
            )

    # Experiment label
    if spec.style and spec.style.experiment:
        exp = spec.style.experiment.lower()
        if exp == "cms":
            mh.cms.label(
                data=False, lumi=spec.style.lumi, label=spec.style.label, ax=ax
            )
        elif exp == "atlas":
            mh.atlas.label(
                data=False, lumi=spec.style.lumi, label=spec.style.label, ax=ax
            )

    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)

    return RenderOutcome(
        status=RenderStatus.RENDERED,
        message=None,
        artifacts=[RenderArtifact(path=out_path, kind="png")],
        meta={
            "inputs": input_paths or {},
            "plot": "comparison",
            "comparison": cmp.comparison,
        },
    )
