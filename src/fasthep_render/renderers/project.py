from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from importlib import resources
from typing import Any

import yaml
from hepflow.model.issues import FlowIssue, IssueLevel
from hepflow.utils import to_dict

from fasthep_render.dispatch import render_resolved
from fasthep_render.model import RenderOutcome
from fasthep_render.registry import resolve_render_registry
from fasthep_render.render_types import RenderCommonSpec, RenderTypeSpec
from fasthep_render.sinks._common import run_render_sink
from fasthep_render.types.common import resolve_single_hist_input

PROJECT_RENDER_SPEC = {
    "name": "hep.render.project",
    "kind": "sink",
    "version": "1.0",
    "params": {
        "spec": {"type": "mapping", "required": True},
        "out": {"type": "string", "required": False},
    },
    "result": {"kind": "artifact", "format": "png"},
}


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
    del common, context
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


def run_project_render(target: Any, **kwargs: Any):
    return run_render_sink(
        op="hep.render.project",
        render_type=PROJECT_RENDER_TYPE,
        handler=render_project_then,
        target=target,
        **kwargs,
    )


def render_project_then(
    product: dict[str, Any],
    common: RenderCommonSpec,
    params: ProjectParams,
    ctx: dict[str, Any],
) -> RenderOutcome:
    """
    Project a histogram onto the requested axis and pass the projected histogram
    to a downstream renderer described by ``params.then``.

    The downstream renderer must provide an explicit ``op`` field.
    """
    h = product["hist"]

    axis_name = params.axis
    if not axis_name:
        msg = "project renderer requires a projection axis"
        raise ValueError(msg)

    ax_names = [getattr(ax, "name", None) for ax in getattr(h, "axes", [])]
    if axis_name not in ax_names:
        msg = f"project renderer axis '{axis_name}' not found in histogram axes: {ax_names}"
        raise ValueError(
            msg
        )

    dataset_axis_name = None
    if "dataset" in ax_names:
        dataset_axis_name = "dataset"
    elif "dataset_name" in ax_names:
        dataset_axis_name = "dataset_name"

    # hist.project(...) keeps only the axes listed.
    keep_axes: list[str] = []
    if (
        params.keep_dataset
        and dataset_axis_name is not None
        and dataset_axis_name != axis_name
    ):
        keep_axes.append(dataset_axis_name)
    keep_axes.append(axis_name)

    h_proj = h.project(*keep_axes)

    if not isinstance(params.then, dict) or not params.then:
        msg = "project renderer requires a non-empty 'then' block"
        raise ValueError(msg)

    downstream_spec = deepcopy(params.then)
    downstream_op = downstream_spec.get("op")
    if not isinstance(downstream_op, str) or not downstream_op:
        msg = "project renderer downstream spec requires explicit 'op'"
        raise ValueError(msg)

    # Inherit common config only if not explicitly overridden downstream.
    downstream_spec.setdefault("figure", to_dict(common.figure))
    downstream_spec.setdefault("axes", to_dict(common.axes))
    downstream_spec.setdefault("legend", to_dict(common.legend))
    downstream_spec.setdefault("style", to_dict(common.style))
    downstream_spec.setdefault(
        "transforms",
        [to_dict(t) for t in (common.transforms or [])],
    )
    downstream_spec.setdefault("extensions", dict(common.extensions or {}))

    render_registry = ctx.get("render_registry") or resolve_render_registry(
        _packaged_render_registry()
    )
    entry = render_registry.renderers.get(downstream_op)
    if entry is None:
        msg = f"project renderer downstream op '{downstream_op}' is not registered"
        raise ValueError(
            msg
        )

    downstream_common = RenderCommonSpec.from_dict(downstream_spec)
    downstream_params = entry.spec.parse_params(downstream_spec)

    return render_resolved(
        product={"hist": h_proj},
        op=downstream_op,
        common=downstream_common,
        render_params=downstream_params,
        ctx=ctx,
        render_registry=render_registry,
    )


def _packaged_render_registry() -> dict[str, Any]:
    registry_file = resources.files("fasthep_render.profiles").joinpath(
        "registry.yaml"
    )
    with registry_file.open(encoding="utf-8") as handle:
        doc = yaml.safe_load(handle) or {}
    registry = doc.get("registry")
    if not isinstance(registry, dict):
        raise ValueError("fasthep_render profile registry is invalid")
    return registry
