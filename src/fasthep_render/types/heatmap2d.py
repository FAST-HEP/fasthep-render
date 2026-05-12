from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hepflow.model.issues import FlowIssue
from hepflow.model.render_types import RenderCommonSpec, RenderTypeSpec
from fasthep_render.types.common import resolve_single_hist_input


@dataclass(frozen=True)
class Heatmap2DParams:
    per_dataset: bool = False
    cbar: bool = True
    max_cols: int | None = None


def parse_heatmap2d_params(spec_dict: dict[str, Any]) -> Heatmap2DParams:
    return Heatmap2DParams(**dict(spec_dict.get("heatmap2d") or {}))


def validate_heatmap2d_params(
    common: RenderCommonSpec,
    params: Heatmap2DParams,
    context: dict[str, Any],
) -> list[FlowIssue]:
    return []


HEATMAP2D_RENDER_TYPE = RenderTypeSpec(
    parse_params=parse_heatmap2d_params,
    validate=validate_heatmap2d_params,
    resolve_input=resolve_single_hist_input,
)