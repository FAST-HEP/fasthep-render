from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from hepflow.model.io import OutputResult
from hepflow.utils import read_json, read_pickle, read_yaml

from fasthep_render.dispatch import render_resolved
from fasthep_render.model import RenderOutcome as RenderHandlerOutcome
from fasthep_render.model import RenderStatus
from fasthep_render.registry import resolve_render_registry
from fasthep_render.render_types import RenderCommonSpec, RenderTypeSpec


@dataclass(frozen=True, slots=True)
class RenderOutcome:
    spec_path: Path | None
    output_path: Path
    product_paths: dict[str, Path]
    status: RenderStatus
    message: str | None
    meta: dict[str, Any]


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
    """Run a registered render sink through the public Render API boundary."""
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
    errors = [
        issue for issue in issues
        if str(getattr(issue, "level", "")).lower() == "error"
    ]
    if errors:
        msg = f"Render validation failed for {op}: {errors}"
        raise ValueError(msg)

    outcome: RenderHandlerOutcome = handler(product, common, params, ctx)
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


def render_spec_file(
    spec_path: str | Path,
    *,
    product: str | Path | None = None,
    products: Mapping[str, str | Path] | None = None,
    out: str | Path | None = None,
    plan_path: str | Path | None = None,
) -> RenderOutcome:
    """Render a saved render spec from explicit product files."""
    spec_file = Path(spec_path)
    spec_doc = _load_render_spec(spec_file)
    render_spec = _render_spec_payload(spec_doc)
    render_op = _render_op(spec_doc, render_spec)
    return _render_paths(
        render_op=render_op,
        render_spec=render_spec,
        product=product,
        products=products,
        output_path=_resolve_output_path(spec_doc, out=out),
        spec_path=spec_file,
        plan_path=plan_path,
    )


def render_path(
    renderer: str,
    input_path: str | Path,
    output_path: str | Path,
    *,
    params: Mapping[str, Any] | None = None,
    plan_path: str | Path | None = None,
) -> RenderOutcome:
    """Render one input path to one output path through the renderer registry."""
    render_spec = _render_path_spec(renderer, params=params)
    return _render_paths(
        render_op=renderer,
        render_spec=render_spec,
        products={renderer: input_path},
        output_path=Path(output_path),
        spec_path=None,
        plan_path=plan_path,
    )


def _render_paths(
    *,
    render_op: str,
    render_spec: dict[str, Any],
    output_path: Path,
    spec_path: Path | None,
    product: str | Path | None = None,
    products: Mapping[str, str | Path] | None = None,
    plan_path: str | Path | None = None,
) -> RenderOutcome:
    product_paths = _normalize_product_paths(product=product, products=products)
    if not product_paths:
        raise ValueError("render execution requires an explicit product path")
    missing_products = [path for path in product_paths.values() if not path.is_file()]
    if missing_products:
        missing = ", ".join(str(path) for path in missing_products)
        raise ValueError(f"product path does not exist: {missing}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    product_values = {name: _load_product(path) for name, path in product_paths.items()}

    plan = read_yaml(plan_path) if plan_path is not None else None
    render_registry = resolve_render_registry(_render_registry_config())
    entry = render_registry.renderers.get(render_op)
    if entry is None:
        raise ValueError(f"Unknown renderer: {render_op}")

    ctx = {
        "product_paths": {name: str(path) for name, path in product_paths.items()},
        "output_path": str(output_path),
        "output_dir": str(output_path.parent),
        "plan_path": str(plan_path) if plan_path is not None else None,
        "plan": plan or {},
        "render_registry": render_registry,
    }
    if spec_path is not None:
        ctx["spec_path"] = str(spec_path)
    common = RenderCommonSpec.from_dict(render_spec)
    render_params = entry.spec.parse_params(render_spec)
    outcome = render_resolved(
        product=product_values,
        op=render_op,
        common=common,
        render_params=render_params,
        ctx=ctx,
        render_registry=render_registry,
    )

    return RenderOutcome(
        spec_path=spec_path,
        output_path=Path(outcome.meta.get("output") or output_path),
        product_paths=product_paths,
        status=outcome.status,
        message=outcome.message,
        meta=dict(outcome.meta or {}),
    )


def _render_path_spec(
    renderer: str,
    *,
    params: Mapping[str, Any] | None,
) -> dict[str, Any]:
    spec = dict(params or {})
    if "op" in spec:
        return spec
    render_params = dict(spec)
    return {"op": renderer, renderer: render_params}


def _load_render_spec(spec_path: Path) -> dict[str, Any]:
    try:
        doc = read_yaml(spec_path)
    except FileNotFoundError:
        raise
    except Exception as exc:
        raise ValueError(f"Invalid render spec YAML: {spec_path}") from exc
    if not isinstance(doc, dict):
        raise ValueError("render spec must be a YAML mapping")
    return doc


def _render_spec_payload(doc: dict[str, Any]) -> dict[str, Any]:
    spec = doc.get("spec")
    if not isinstance(spec, dict):
        raise ValueError("render spec must define a mapping field 'spec'")
    return dict(spec)


def _render_op(doc: dict[str, Any], spec: dict[str, Any]) -> str:
    op = doc.get("impl") or spec.get("op")
    if not isinstance(op, str) or not op:
        raise ValueError("render spec must define top-level 'impl' or nested 'spec.op'")
    return op


def _normalize_product_paths(
    *,
    product: str | Path | None,
    products: Mapping[str, str | Path] | None,
) -> dict[str, Path]:
    normalized = {name: Path(path) for name, path in dict(products or {}).items()}
    if product is not None:
        normalized.setdefault("hist", Path(product))
    return normalized


def _load_product(path: Path) -> Any:
    if path.suffix == ".json":
        return read_json(path)
    if path.suffix == ".d2":
        return path.read_text(encoding="utf-8")
    return read_pickle(path)


def _resolve_output_path(
    doc: dict[str, Any],
    *,
    out: str | Path | None,
) -> Path:
    value = out if out is not None else doc.get("out")
    if value is None:
        raise ValueError("render spec requires --out or top-level 'out'")
    if not isinstance(value, str | Path):
        raise ValueError("render spec output path must be a string path")
    return Path(value)


def _render_registry_config() -> dict[str, Any]:
    registry_file = resources.files("fasthep_render.profiles").joinpath(
        "registry.yaml"
    )
    with registry_file.open(encoding="utf-8") as handle:
        doc = yaml.safe_load(handle) or {}
    registry = doc.get("registry")
    if not isinstance(registry, dict):
        raise ValueError("fasthep_render profile registry is invalid")
    return registry
