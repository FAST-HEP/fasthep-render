from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

from hepflow.model.io import OutputResult
from jinja2 import Environment, StrictUndefined
from markdown_it import MarkdownIt

SCHEMA_VALIDATION_RENDER_SPEC = {
    "name": "hep.render.schema_validation",
    "kind": "sink",
    "version": "1.0",
    "params": {
        "spec": {"type": "mapping", "required": False},
        "outputs": {"type": "list", "required": False},
    },
    "result": {"kind": "artifact", "formats": ["markdown", "html"]},
}


def run_schema_validation_render(
    target: dict[str, Any],
    *,
    spec: dict[str, Any] | None = None,
    outputs: list[dict[str, str]] | None = None,
    ctx: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
    **_: Any,
) -> list[OutputResult]:
    ctx = dict(ctx or {})
    meta = dict(meta or {})
    spec = dict(spec or {})
    configured_outputs = list(outputs or spec.get("outputs") or [])
    if not configured_outputs:
        raise ValueError("hep.render.schema_validation requires outputs")

    render_model = prepare_schema_validation_context(
        target,
        labels=dict(spec.get("comparisons") or {}),
        note=str(spec.get("note") or ""),
        input_products=dict(ctx.get("input_products") or {}),
    )
    template_text = _load_template(str(spec.get("template") or ""))
    markdown = _render_markdown(template_text, render_model)
    outdir = Path(str(ctx.get("outdir") or "."))
    rendered: list[OutputResult] = []
    for output in configured_outputs:
        output_path = _output_path(output, outdir)
        output_format = str(output["format"]).lower()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_format in {"markdown", "md"}:
            content = markdown
            final_format = "markdown"
        elif output_format == "html":
            content = _markdown_to_html(markdown)
            final_format = "html"
        else:
            raise ValueError(
                "hep.render.schema_validation supports markdown and html outputs, "
                f"got {output_format!r}"
            )
        output_path.write_text(content, encoding="utf-8")
        rendered.append(
            OutputResult(
                kind="artifact",
                path=str(output_path),
                format=final_format,
                metadata={
                    "artifact_kind": f"schema_validation_{final_format}",
                    "writer_manifest": {
                        "kind": f"schema_validation_{final_format}",
                        "node_id": str(meta.get("node_id") or ""),
                        "path": _relative_to_outdir(output_path, outdir),
                        "path_type": "relative_to_outdir",
                        "inputs": list(render_model.get("input_products") or []),
                    },
                },
            )
        )
    return rendered


def prepare_schema_validation_context(
    raw: dict[str, Any],
    *,
    labels: dict[str, Any] | None = None,
    note: str = "",
    input_products: dict[str, Any] | None = None,
) -> dict[str, Any]:
    labels = dict(labels or {})
    comparisons = []
    for comparison_id, comparison in raw.items():
        if not isinstance(comparison, dict):
            raise ValueError(
                "schema validation report inputs must be schema-comparison objects"
            )
        label_cfg = dict(labels.get(comparison_id) or {})
        comparisons.append(
            _comparison_context(
                str(comparison_id),
                comparison,
                label_cfg=label_cfg,
            )
        )

    return {
        "title": "Schema Validation Report",
        "note": note,
        "comparisons": comparisons,
        "input_products": _input_products(input_products or {}),
    }


def _comparison_context(
    comparison_id: str,
    comparison: dict[str, Any],
    *,
    label_cfg: dict[str, Any],
) -> dict[str, Any]:
    summary = dict(comparison.get("summary") or {})
    common_fields = list(comparison.get("common_fields") or [])
    compatible_fields = list(comparison.get("compatible_fields") or [])
    only_in_reference = list(comparison.get("only_in_reference") or [])
    only_in_target = list(comparison.get("only_in_target") or [])
    type_mismatches = list(comparison.get("type_mismatches") or [])
    shape_mismatches = list(comparison.get("shape_mismatches") or [])

    reference_count = _count(summary, "reference_fields", None)
    target_count = _count(summary, "target_fields", None)
    common_count = _count(summary, "common_fields", len(common_fields))
    compatible_count = _count(summary, "compatible_fields", len(compatible_fields))
    incompatible_count = max(common_count - compatible_count, 0)
    missing_count = _count(summary, "only_in_reference", len(only_in_reference))
    additional_count = _count(summary, "only_in_target", len(only_in_target))

    return {
        "id": comparison_id,
        "label": str(label_cfg.get("label") or comparison_id),
        "name": str(label_cfg.get("name") or comparison_id),
        "reference": str(comparison.get("reference") or ""),
        "target": str(comparison.get("target") or ""),
        "reference_label": str(label_cfg.get("reference_label") or "Legacy"),
        "target_label": str(label_cfg.get("target_label") or "FAST-HEP"),
        "counts": {
            "reference": reference_count,
            "target": target_count,
            "common": common_count,
            "compatible": compatible_count,
            "incompatible": incompatible_count,
            "only_in_reference": missing_count,
            "only_in_target": additional_count,
        },
        "ratios": {
            "common_over_reference": _ratio(common_count, reference_count),
            "compatible_over_common": _ratio(compatible_count, common_count),
        },
        "only_in_reference": [str(field) for field in only_in_reference],
        "only_in_target": [str(field) for field in only_in_target],
        "incompatible_fields": _incompatible_fields(
            type_mismatches=type_mismatches,
            shape_mismatches=shape_mismatches,
        ),
        "compatible_count": compatible_count,
    }


def _incompatible_fields(
    *,
    type_mismatches: list[Any],
    shape_mismatches: list[Any],
) -> list[dict[str, str]]:
    fields: dict[str, dict[str, str]] = {}
    for item in type_mismatches:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field") or "")
        if not field:
            continue
        entry = fields.setdefault(field, {"field": field})
        if item.get("reference") is not None:
            entry["reference_type"] = str(item["reference"])
        if item.get("target") is not None:
            entry["target_type"] = str(item["target"])
    for item in shape_mismatches:
        if not isinstance(item, dict):
            continue
        field = str(item.get("field") or "")
        if not field:
            continue
        entry = fields.setdefault(field, {"field": field})
        if item.get("reference") is not None:
            entry["reference_shape"] = str(item["reference"])
        if item.get("target") is not None:
            entry["target_shape"] = str(item["target"])
    return [fields[field] for field in sorted(fields)]


def _input_products(raw: dict[str, Any]) -> list[dict[str, str]]:
    products = []
    for name, product_raw in raw.items():
        if not isinstance(product_raw, dict):
            continue
        product = dict(product_raw)
        products.append(
            {
                "name": str(name),
                "node_id": str(product.get("node_id") or ""),
                "port": str(product.get("port") or ""),
                "path": str(product.get("path") or ""),
                "kind": str(product.get("kind") or ""),
            }
        )
    return products


def _count(summary: dict[str, Any], key: str, fallback: int | None) -> int:
    value = summary.get(key)
    if value is None:
        return int(fallback or 0)
    return int(value)


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    if denominator <= 0:
        return {"value": None, "label": "n/a"}
    value = numerator / denominator
    return {"value": value, "label": f"{value:.1%}"}


def _load_template(template: str) -> str:
    if template:
        candidate = Path(template)
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
    resource = resources.files("fasthep_render").joinpath(
        "templates",
        "reports",
        "schema_validation.md.j2",
    )
    return resource.read_text(encoding="utf-8")


def _render_markdown(template_text: str, context: dict[str, Any]) -> str:
    env = Environment(undefined=StrictUndefined, autoescape=False)
    return env.from_string(template_text).render(**context).rstrip() + "\n"


def _markdown_to_html(markdown: str) -> str:
    body = MarkdownIt("commonmark").enable("table").render(markdown)
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        "  <title>FAST-HEP Schema Validation Report</title>\n"
        "</head>\n"
        "<body>\n"
        f"{body}"
        "</body>\n"
        "</html>\n"
    )


def _output_path(output: dict[str, str], outdir: Path) -> Path:
    path = Path(str(output["path"]))
    if path.is_absolute():
        return path
    return outdir / path


def _relative_to_outdir(path: Path, outdir: Path) -> str:
    try:
        return path.resolve().relative_to(outdir.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


__all__ = [
    "SCHEMA_VALIDATION_RENDER_SPEC",
    "prepare_schema_validation_context",
    "run_schema_validation_render",
]
