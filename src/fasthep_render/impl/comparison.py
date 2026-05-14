from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import mplhep as mh
from hepflow.model.render import RenderOutcome, RenderStatus
from hepflow.model.render_types import RenderCommonSpec
from mplhep.comp import comparison as mplhep_comparison

from fasthep_render.types.comparison import ComparisonParams


def render_comparison(
    product: dict[str, Any],
    common: RenderCommonSpec,
    params: ComparisonParams,
    ctx: dict[str, Any],
) -> RenderOutcome:
    h_ref = product["reference"]
    h_tgt = product["target"]
    out_path = ctx["output_path"]

    fig = plt.figure(figsize=tuple(common.figure.size), dpi=int(common.figure.dpi))
    ax = fig.add_subplot(1, 1, 1)

    try:
        mplhep_comparison(
            h_ref,
            h_tgt,
            ax=ax,
            xlabel=common.axes.x.label or common.axes.x.name,
            h1_label=params.reference_label,
            h2_label=params.target_label,
            comparison=params.comparison,
            comparison_ylabel=params.comparison_ylabel,
            comparison_ylim=params.comparison_ylim,
            h1_w2method=params.w2method,
            flow=params.flow,
        )
    except ModuleNotFoundError:
        mh.histplot(h_ref, ax=ax, label=params.reference_label, histtype="step")
        mh.histplot(h_tgt, ax=ax, label=params.target_label, histtype="step")
        ax.set_xlabel(common.axes.x.label or common.axes.x.name)
        ax.legend()

    if common.axes.x.limits:
        ax.set_xlim(*common.axes.x.limits)

    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)

    return RenderOutcome(
        status=RenderStatus.RENDERED,
        message=None,
        meta={"renderer": "comparison", "output": out_path},
    )
