from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import matplotlib.pyplot as plt
import mplhep as mh
from hepflow.model.issues import FlowIssue, IssueLevel
from mplhep.comp import comparison as mplhep_comparison

from fasthep_render.model import RenderOutcome, RenderStatus
from fasthep_render.render_types import RenderCommonSpec, RenderTypeSpec
from fasthep_render.sinks._common import run_render_sink

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
