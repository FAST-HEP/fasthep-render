from __future__ import annotations

from typing import Any

from hepflow.model.render import RenderOutcome
from hepflow.model.render_types import RenderCommonSpec
from hepflow.registry.loaders import resolve_runtime_registry
from hepflow.registry.runtime import RuntimeRegistry

from fasthep_render.transforms import apply_render_transforms


def render_by_registry(
    product: dict[str, Any],
    params: dict[str, Any],
    ctx: dict[str, Any],
    *,
    runtime_registry: RuntimeRegistry | None = None,
) -> RenderOutcome:
    op = str(params.get("op") or "")
    spec_dict = dict(params.get("spec") or {})

    runtime_registry = runtime_registry or resolve_runtime_registry(
        (ctx.get("plan") or {}).get("registry") or {}
    )

    entry = runtime_registry.renderers.get(op)
    if entry is None:
        msg = f"Unknown renderer: {op}"
        raise ValueError(msg)

    common = RenderCommonSpec.from_dict(spec_dict)
    render_params = entry.spec.parse_params(spec_dict)

    return render_resolved(
        product=product,
        op=op,
        common=common,
        render_params=render_params,
        ctx=ctx,
        runtime_registry=runtime_registry,
    )


def render_resolved(
    *,
    product: dict[str, Any],
    op: str,
    common: RenderCommonSpec,
    render_params: Any,
    ctx: dict[str, Any],
    runtime_registry: RuntimeRegistry,
) -> RenderOutcome:
    entry = runtime_registry.renderers.get(op)
    if entry is None:
        msg = f"Unknown renderer: {op}"
        raise ValueError(msg)

    validation_ctx = dict(ctx.get("render_validation") or {})
    issues = entry.spec.validate(common, render_params, validation_ctx)
    errors = [i for i in issues if str(getattr(i, "level", "")).lower() == "error"]
    if errors:
        msg = f"Render validation failed for {op}: {errors}"
        raise ValueError(msg)

    product = apply_render_transforms(
        products=product,
        common=common,
        render_params=render_params,
        ctx=ctx,
    )

    return entry.handler(product, common, render_params, ctx)
