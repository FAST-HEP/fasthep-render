from __future__ import annotations

from pathlib import Path
from typing import Any

from hepflow.model.io import OutputResult
from hepflow.model.render import RenderOutcome, RenderStatus
from hepflow.model.render_types import RenderCommonSpec, RenderTypeSpec


def run_render_sink(
    *,
    op: str,
    render_type: RenderTypeSpec,
    handler,
    target: Any,
    spec: dict[str, Any] | None = None,
    output_path: str,
    output_dir: str | None = None,
    ctx: dict[str, Any] | None = None,
    **_: Any,
) -> OutputResult:
    ctx = dict(ctx or {})
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if output_dir is not None:
        ctx["output_dir"] = output_dir
    ctx["output_path"] = output_path

    product = target if isinstance(target, dict) else {"hist": target}
    spec_dict = dict(spec or {})
    common = RenderCommonSpec.from_dict(spec_dict)
    params = render_type.parse_params(spec_dict)
    issues = render_type.validate(
        common,
        params,
        dict(ctx.get("render_validation") or {}),
    )
    errors = [issue for issue in issues if str(getattr(issue, "level", "")).lower() == "error"]
    if errors:
        raise ValueError(f"Render validation failed for {op}: {errors}")

    outcome: RenderOutcome = handler(product, common, params, ctx)
    if outcome.status not in {RenderStatus.RENDERED, RenderStatus.SKIPPED}:
        raise RuntimeError(outcome.message or f"Render sink {op} failed")

    path = str(outcome.meta.get("output") or output_path)
    return OutputResult(
        kind="artifact",
        path=path,
        format=Path(path).suffix.lstrip(".") or "png",
        metadata={
            "sink": op,
            "render_status": outcome.status.value,
            **dict(outcome.meta or {}),
        },
    )
