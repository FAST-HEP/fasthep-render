from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from hepflow.model.issues import FlowIssue, IssueLevel
from hepflow.model.render_types import RenderCommonSpec, RenderTypeSpec


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
