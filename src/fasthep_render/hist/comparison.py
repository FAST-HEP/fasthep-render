from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import matplotlib.pyplot as plt
import mplhep as mh
import numpy as np
from hepflow.model.issues import FlowIssue, IssueLevel
from matplotlib.gridspec import GridSpec
from mplhep.comp import comparison as mplhep_comparison

from fasthep_render.api import run_render_sink
from fasthep_render.model import RenderOutcome, RenderStatus
from fasthep_render.render_types import RenderCommonSpec, RenderTypeSpec

COMPARISON_RENDER_SPEC = {
    "name": "hep.render.comparison",
    "kind": "sink",
    "version": "1.0",
    "params": {
        "spec": {"type": "mapping", "required": False},
        "out": {"type": "string", "required": False},
    },
    "result": {"kind": "artifact", "format": "png"},
}


@dataclass(frozen=True)
class ComparisonParams:
    reference: str
    target: str

    reference_label: str = "reference"
    target_label: str = "target"

    comparison: Literal[
        "ratio",
        "split_ratio",
        "pull",
        "difference",
        "relative_difference",
        "efficiency",
        "asymmetry",
    ] = "ratio"

    comparison_ylabel: str | None = None
    comparison_ylim: tuple[float, float] | None = None

    w2method: Literal["sqrt", "poisson"] = "sqrt"
    flow: Literal["hint", "show", "none"] = "hint"
    normalise: Literal["area"] | None = None
    reference_color: str = "black"
    target_color: str = "red"
    reference_histtype: str = "errorbar"
    target_histtype: str = "step"


def parse_comparison_params(spec_dict: dict[str, Any]) -> ComparisonParams:
    return ComparisonParams(**dict(spec_dict.get("comparison") or {}))


def validate_comparison_params(
    common: RenderCommonSpec,
    params: ComparisonParams,
    context: dict[str, Any],
) -> list[FlowIssue]:
    del common
    issues: list[FlowIssue] = []

    available_products = set(context.get("available_products") or [])
    missing = [
        p for p in [params.reference, params.target] if p not in available_products
    ]
    if missing:
        issues.append(
            FlowIssue(
                level=IssueLevel.ERROR,
                code="RENDER_COMPARISON_PRODUCTS_MISSING",
                message="comparison renderer references products not available in plan",
                meta={
                    "missing": missing,
                    "available_products": sorted(available_products),
                },
            )
        )
    return issues


def resolve_comparison_input(
    common: RenderCommonSpec,
    params: ComparisonParams,
    context: dict[str, Any],
) -> dict[str, Any]:
    del common, context
    return {
        "products": {
            "reference": params.reference,
            "target": params.target,
        }
    }


COMPARISON_RENDER_TYPE = RenderTypeSpec(
    parse_params=parse_comparison_params,
    validate=validate_comparison_params,
    resolve_input=resolve_comparison_input,
)


def run_comparison_render(target: Any, **kwargs: Any):
    return run_render_sink(
        op="hep.render.comparison",
        render_type=COMPARISON_RENDER_TYPE,
        handler=render_comparison,
        target=target,
        **kwargs,
    )


def render_comparison(
    product: dict[str, Any],
    common: RenderCommonSpec,
    params: ComparisonParams,
    ctx: dict[str, Any],
) -> RenderOutcome:
    h_ref = product["reference"]
    h_tgt = product["target"]
    out_path = ctx["output_path"]
    warnings: list[dict[str, Any]] = []

    h_ref, h_tgt = _normalise_for_comparison(
        h_ref,
        h_tgt,
        normalise=params.normalise,
        warnings=warnings,
    )

    fig = plt.figure(figsize=tuple(common.figure.size), dpi=int(common.figure.dpi))
    grid = GridSpec(2, 1, figure=fig, height_ratios=[3, 1], hspace=0.06)
    ax_main = fig.add_subplot(grid[0])
    ax_comp = fig.add_subplot(grid[1], sharex=ax_main)

    try:
        mh.histplot(
            h_ref,
            ax=ax_main,
            label=params.reference_label,
            histtype=params.reference_histtype,
            color=params.reference_color,
            yerr=True,
            w2method=params.w2method,
            flow=params.flow,
        )
        mh.histplot(
            h_tgt,
            ax=ax_main,
            label=params.target_label,
            histtype=params.target_histtype,
            color=params.target_color,
            flow=params.flow,
        )
        ax_main.set_ylabel(common.axes.y.label or common.axes.y.name or "")
        ax_main.legend()
        ax_main.tick_params(labelbottom=False)

        mplhep_comparison(
            h_ref,
            h_tgt,
            ax=ax_comp,
            xlabel=common.axes.x.label or common.axes.x.name,
            h1_label=params.reference_label,
            h2_label=params.target_label,
            comparison=params.comparison,
            comparison_ylabel=params.comparison_ylabel,
            comparison_ylim=params.comparison_ylim,
            h1_w2method=params.w2method,
            flow=params.flow,
            color=params.reference_color,
        )
    except ModuleNotFoundError:
        mh.histplot(
            h_ref,
            ax=ax_main,
            label=params.reference_label,
            histtype=params.reference_histtype,
            color=params.reference_color,
        )
        mh.histplot(
            h_tgt,
            ax=ax_main,
            label=params.target_label,
            histtype=params.target_histtype,
            color=params.target_color,
        )
        ax_comp.set_xlabel(common.axes.x.label or common.axes.x.name)
        ax_main.legend()

    if common.axes.x.limits:
        ax_main.set_xlim(*common.axes.x.limits)

    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)

    return RenderOutcome(
        status=RenderStatus.RENDERED,
        message=None,
        meta={
            "renderer": "comparison",
            "output": out_path,
            "normalise": params.normalise,
            "warnings": warnings,
        },
    )


def _normalise_for_comparison(
    h_ref: Any,
    h_tgt: Any,
    *,
    normalise: str | None,
    warnings: list[dict[str, Any]],
) -> tuple[Any, Any]:
    if normalise is None:
        return h_ref, h_tgt
    if normalise != "area":
        raise ValueError(f"Unsupported comparison normalise option: {normalise!r}")
    return (
        _normalise_hist_area(h_ref, label="reference", warnings=warnings),
        _normalise_hist_area(h_tgt, label="target", warnings=warnings),
    )


def _normalise_hist_area(
    histogram: Any,
    *,
    label: str,
    warnings: list[dict[str, Any]],
) -> Any:
    values = np.asarray(histogram.values(flow=False), dtype=float)
    integral = float(np.sum(values))
    if integral < 0:
        raise ValueError(
            f"Cannot apply normalise='area' to {label} histogram with "
            f"negative visible-bin integral {integral}"
        )
    if integral == 0:
        warnings.append(
            {
                "code": "COMPARISON_AREA_NORMALISE_ZERO_INTEGRAL",
                "message": (
                    f"Skipped area normalisation for {label} histogram because "
                    "the visible-bin integral is zero"
                ),
                "histogram": label,
                "integral": integral,
            }
        )
        return histogram

    density_obj = histogram.density()
    if hasattr(density_obj, "values") and hasattr(density_obj, "copy"):
        return density_obj.copy()

    density = np.asarray(density_obj, dtype=float)
    scale = np.divide(
        density,
        values,
        out=np.zeros_like(density, dtype=float),
        where=values != 0,
    )

    scaled = histogram.copy()
    view = scaled.view(flow=False)
    if hasattr(view, "value"):
        view.value = density
        variances = np.asarray(histogram.variances(flow=False), dtype=float)
        view.variance = variances * scale**2
    else:
        view[...] = density
    return scaled


__all__ = [
    "COMPARISON_RENDER_SPEC",
    "COMPARISON_RENDER_TYPE",
    "ComparisonParams",
    "render_comparison",
    "run_comparison_render",
]
