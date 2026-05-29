from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any

import yaml
from hepflow.model.render import RenderStatus
from hepflow.model.render_types import RenderCommonSpec
from hepflow.registry.loaders import resolve_runtime_registry
from hepflow.utils import read_json, read_pickle, read_yaml

from fasthep_render.dispatch import render_resolved


@dataclass(frozen=True, slots=True)
class RenderOutcome:
    spec_path: Path
    output_path: Path
    product_paths: dict[str, Path]
    status: RenderStatus
    message: str | None
    meta: dict[str, Any]


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
    product_paths = _normalize_product_paths(product=product, products=products)
    if not product_paths:
        raise ValueError("render spec execution requires an explicit product path")
    missing_products = [path for path in product_paths.values() if not path.is_file()]
    if missing_products:
        missing = ", ".join(str(path) for path in missing_products)
        raise ValueError(f"product path does not exist: {missing}")

    output_path = _resolve_output_path(spec_doc, out=out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    product_values = {name: _load_product(path) for name, path in product_paths.items()}

    plan = read_yaml(plan_path) if plan_path is not None else None
    runtime_registry = resolve_runtime_registry(_render_registry_config())
    entry = runtime_registry.renderers.get(render_op)
    if entry is None:
        raise ValueError(f"Unknown renderer: {render_op}")

    ctx = {
        "spec_path": str(spec_file),
        "product_paths": {name: str(path) for name, path in product_paths.items()},
        "output_path": str(output_path),
        "output_dir": str(output_path.parent),
        "plan_path": str(plan_path) if plan_path is not None else None,
        "plan": plan or {},
        "runtime_registry": runtime_registry,
    }
    common = RenderCommonSpec.from_dict(render_spec)
    render_params = entry.spec.parse_params(render_spec)
    outcome = render_resolved(
        product=product_values,
        op=render_op,
        common=common,
        render_params=render_params,
        ctx=ctx,
        runtime_registry=runtime_registry,
    )

    return RenderOutcome(
        spec_path=spec_file,
        output_path=Path(outcome.meta.get("output") or output_path),
        product_paths=product_paths,
        status=outcome.status,
        message=outcome.message,
        meta=dict(outcome.meta or {}),
    )


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
