from __future__ import annotations

from copy import deepcopy
from typing import Any

from hepflow.model.render import RenderOutcome
from hepflow.model.render_types import RenderCommonSpec
from hepflow.registry.loaders import resolve_runtime_registry
from hepflow.utils import to_dict

from fasthep_render.dispatch import render_resolved
from fasthep_render.types.project import ProjectParams


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

    runtime_registry = ctx.get("runtime_registry") or resolve_runtime_registry(
        (ctx.get("plan") or {}).get("registry") or {}
    )
    entry = runtime_registry.renderers.get(downstream_op)
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
        runtime_registry=runtime_registry,
    )
