from __future__ import annotations

from typing import Any

from fasthep_render.model import RenderOutcome
from fasthep_render.registry import RenderRegistry, resolve_render_registry
from fasthep_render.render_types import RenderCommonSpec
from fasthep_render.transforms import apply_render_transforms


def render_by_registry(
    product: dict[str, Any],
    params: dict[str, Any],
    ctx: dict[str, Any],
    *,
    render_registry: RenderRegistry | None = None,
) -> RenderOutcome:
    op = str(params.get("op") or "")
    spec_dict = dict(params.get("spec") or {})

    render_registry = (
        render_registry
        or ctx.get("render_registry")
        or resolve_render_registry()
    )

    entry = render_registry.renderers.get(op)
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
        render_registry=render_registry,
    )


def render_resolved(
    *,
    product: dict[str, Any],
    op: str,
    common: RenderCommonSpec,
    render_params: Any,
    ctx: dict[str, Any],
    render_registry: RenderRegistry,
) -> RenderOutcome:
    entry = render_registry.renderers.get(op)
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
