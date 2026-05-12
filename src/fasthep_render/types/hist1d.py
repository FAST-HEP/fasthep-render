from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from hepflow.model.issues import FlowIssue
from hepflow.model.render_types import RenderCommonSpec, RenderTypeSpec
from fasthep_render.types.common import resolve_single_hist_input


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
    return []


HIST1D_RENDER_TYPE = RenderTypeSpec(
    parse_params=parse_hist1d_params,
    validate=validate_hist1d_params,
    resolve_input=resolve_single_hist_input,
)
