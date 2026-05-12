from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hepflow.model.issues import FlowIssue, IssueLevel
from hepflow.model.render_types import RenderCommonSpec, RenderTypeSpec
from fasthep_render.types.common import resolve_single_hist_input


@dataclass(frozen=True)
class ProjectParams:
    axis: str
    keep_dataset: bool = True
    then: dict[str, Any] | None = None


def parse_project_params(spec_dict: dict[str, Any]) -> ProjectParams:
    return ProjectParams(**dict(spec_dict.get("project") or {}))


def validate_project_params(
    common: RenderCommonSpec,
    params: ProjectParams,
    context: dict[str, Any],
) -> list[FlowIssue]:
    issues: list[FlowIssue] = []
    if not params.axis:
        issues.append(
            FlowIssue(
                level=IssueLevel.ERROR,
                code="RENDER_PROJECT_AXIS_MISSING",
                message="project renderer requires a projection axis",
                meta={},
            )
        )
    return issues


PROJECT_RENDER_TYPE = RenderTypeSpec(
    parse_params=parse_project_params,
    validate=validate_project_params,
    resolve_input=resolve_single_hist_input,
)