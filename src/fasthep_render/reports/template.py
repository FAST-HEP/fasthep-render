from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

from hepflow.model.io import OutputResult
from jinja2 import Environment, StrictUndefined
from markdown_it import MarkdownIt

REPORT_TEMPLATE_SPEC = {
    "name": "hep.report.template",
    "kind": "sink",
    "version": "0.1",
    "params": {
        "source": {"type": "string", "required": True},
        "template": {"type": "string", "required": False},
        "outputs": {"type": "list", "required": True},
    },
    "result": {"kind": "artifact"},
}


def run_report_template(
    *,
    report_context: dict[str, Any],
    source: str,
    template: str | None = None,
    outputs: list[dict[str, str]] | None = None,
    ctx: dict[str, Any] | None = None,
    **_: Any,
) -> list[OutputResult]:
    """Render a structured report context through a Markdown Jinja template."""
    ctx = dict(ctx or {})
    outputs = list(outputs or [])
    if not outputs:
        raise ValueError("hep.report.template requires at least one output")

    template_id = template or _default_template_for_source(source)
    template_text = _load_template(
        template_id,
        source=source,
        registry=dict(ctx.get("report_templates") or {}),
        workflow_dir=ctx.get("workflow_dir"),
    )
    markdown = _render_markdown(template_text, report_context)

    rendered: list[OutputResult] = []
    for output in outputs:
        output_path = Path(str(output["path"]))
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
                "hep.report.template supports output formats markdown and html, "
                f"got {output_format!r}"
            )
        output_path.write_text(content, encoding="utf-8")
        rendered.append(
            OutputResult(
                kind="artifact",
                path=str(output_path),
                format=final_format,
                metadata={
                    "sink": "hep.report.template",
                    "source": source,
                    "template": template_id,
                },
            )
        )
    return rendered


def _default_template_for_source(source: str) -> str:
    if source == "provenance":
        return "hep.provenance.default"
    raise ValueError(f"No default report template for source {source!r}")


def _load_template(
    template: str,
    *,
    source: str,
    registry: dict[str, Any],
    workflow_dir: Any,
) -> str:
    entry = registry.get(template)
    if isinstance(entry, dict):
        entry_source = entry.get("source")
        if entry_source is not None and str(entry_source) != source:
            raise ValueError(
                f"Report template {template!r} is registered for source "
                f"{entry_source!r}, not {source!r}"
            )
        path = str(entry.get("path") or "")
        if not path:
            raise ValueError(f"Report template {template!r} has no path")
        return _read_template_path(path)

    if isinstance(workflow_dir, str) and workflow_dir.strip():
        candidate = Path(workflow_dir) / template
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")

    raise ValueError(
        f"Report template {template!r} was not registered and was not found "
        "relative to workflow.yaml"
    )


def _read_template_path(path: str) -> str:
    candidate = Path(path)
    if candidate.is_absolute() or candidate.exists():
        return candidate.read_text(encoding="utf-8")
    parts = Path(path).parts
    if parts and parts[0] == "fasthep_render":
        resource = resources.files("fasthep_render").joinpath(*parts[1:])
        return resource.read_text(encoding="utf-8")
    if candidate.exists():
        return candidate.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Report template file not found: {path}")


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
        "  <title>FAST-HEP Report</title>\n"
        "</head>\n"
        "<body>\n"
        f"{body}"
        "</body>\n"
        "</html>\n"
    )


__all__ = ["REPORT_TEMPLATE_SPEC", "run_report_template"]
