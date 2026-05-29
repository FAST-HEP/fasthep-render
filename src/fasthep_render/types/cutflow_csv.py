from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hepflow.model.issues import FlowIssue
from hepflow.model.render_types import RenderCommonSpec, RenderTypeSpec


@dataclass(frozen=True)
class CutflowCsvParams:
    include_dataset: bool = True


def parse_cutflow_csv_params(spec_dict: dict[str, Any]) -> CutflowCsvParams:
    return CutflowCsvParams(**dict(spec_dict.get("cutflow_csv") or {}))


def validate_cutflow_csv_params(
    common: RenderCommonSpec,
    params: CutflowCsvParams,
    context: dict[str, Any],
) -> list[FlowIssue]:
    return []


def resolve_cutflow_input(
    common: RenderCommonSpec,
    params: CutflowCsvParams,
    context: dict[str, Any],
) -> dict[str, Any]:
    explicit_inputs = dict(context.get("explicit_inputs") or {})
    default_product = context.get("default_product")
    if explicit_inputs:
        return {"products": explicit_inputs}
    if not default_product:
        msg = "No default cutflow product available for renderer input resolution"
        raise ValueError(msg)
    return {
        "product": str(default_product),
        "level": "global",
        "path": f"{default_product}.json",
    }


CUTFLOW_CSV_RENDER_TYPE = RenderTypeSpec(
    parse_params=parse_cutflow_csv_params,
    validate=validate_cutflow_csv_params,
    resolve_input=resolve_cutflow_input,
)
