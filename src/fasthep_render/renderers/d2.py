from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fasthep_toolbench.command import CommandResult
from fasthep_toolbench.tools import run_registered_tool
from hepflow.model.issues import FlowIssue

from fasthep_render.model import RenderArtifact, RenderOutcome, RenderStatus
from fasthep_render.render_types import RenderCommonSpec, RenderTypeSpec


@dataclass(frozen=True)
class D2RenderParams:
    format: str | None = None
    layout: str | None = None
    theme: str | None = None


def parse_d2_params(spec_dict: dict[str, Any]) -> D2RenderParams:
    return D2RenderParams(**dict(spec_dict.get("d2") or {}))


def validate_d2_params(
    common: RenderCommonSpec,
    params: D2RenderParams,
    context: dict[str, Any],
) -> list[FlowIssue]:
    del common, params, context
    return []


def resolve_d2_input(
    common: RenderCommonSpec,
    params: D2RenderParams,
    context: dict[str, Any],
) -> dict[str, Any]:
    del common, params
    explicit_inputs = dict(context.get("explicit_inputs") or {})
    if explicit_inputs:
        return {"products": explicit_inputs}
    default_product = context.get("default_product")
    if default_product:
        return {"product": str(default_product), "path": str(default_product)}
    msg = "d2 renderer requires an explicit .d2 input file"
    raise ValueError(msg)


D2_RENDER_TYPE = RenderTypeSpec(
    parse_params=parse_d2_params,
    validate=validate_d2_params,
    resolve_input=resolve_d2_input,
)


def render_d2(
    product: dict[str, Any],
    common: RenderCommonSpec,
    params: D2RenderParams,
    ctx: dict[str, Any],
) -> RenderOutcome:
    del product, common
    input_path = _resolve_input_path(ctx)
    output_path = Path(ctx["output_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_format = params.format or _format_from_output(output_path)

    args = [str(input_path), str(output_path)]
    if params.layout:
        args.extend(["--layout", params.layout])
    if params.theme:
        args.extend(["--theme", params.theme])

    result = run_registered_tool("d2", args)
    if not isinstance(result, CommandResult):
        msg = f"d2 tool returned unsupported result: {type(result).__name__}"
        raise TypeError(msg)

    if result.exit_code == 127:
        return RenderOutcome(
            status=RenderStatus.SKIPPED,
            message=result.stderr or "d2 executable is not available",
            meta={
                "renderer": "d2",
                "input": str(input_path),
                "output": str(output_path),
                "exit_code": result.exit_code,
                "command": result.command,
            },
        )
    if result.exit_code != 0:
        msg = result.stderr or f"d2 exited with status {result.exit_code}"
        raise RuntimeError(msg)

    return RenderOutcome(
        status=RenderStatus.RENDERED,
        message=None,
        artifacts=[
            RenderArtifact(
                path=str(output_path),
                kind=output_format,
                role="main",
                label="D2 graph",
            )
        ],
        meta={
            "renderer": "d2",
            "input": str(input_path),
            "output": str(output_path),
            "format": output_format,
            "command": result.command,
        },
    )


def _resolve_input_path(ctx: dict[str, Any]) -> Path:
    product_paths = dict(ctx.get("product_paths") or {})
    for key in ("d2", "graph", "hist"):
        path = product_paths.get(key)
        if path is not None:
            return Path(path)
    msg = "d2 renderer requires a product path named 'd2' or 'graph'"
    raise ValueError(msg)


def _format_from_output(path: Path) -> str:
    suffix = path.suffix.lstrip(".")
    return suffix or "png"
