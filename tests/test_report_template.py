from __future__ import annotations

from pathlib import Path

import pytest

from fasthep_render.reports.template import run_report_template


def test_report_template_renders_markdown_and_html(tmp_path: Path) -> None:
    markdown_path = tmp_path / "reports" / "provenance.md"
    html_path = tmp_path / "reports" / "provenance.html"

    outputs = run_report_template(
        report_context=_context(),
        source="provenance",
        template="hep.provenance.default",
        outputs=[
            {"path": str(markdown_path), "format": "markdown"},
            {"path": str(html_path), "format": "html"},
        ],
        ctx={
            "report_templates": {
                "hep.provenance.default": {
                    "path": "fasthep_render/templates/reports/provenance.md.j2",
                    "source": "provenance",
                    "formats": ["markdown", "html"],
                }
            }
        },
    )

    assert [output.format for output in outputs] == ["markdown", "html"]
    markdown = markdown_path.read_text(encoding="utf-8")
    html = html_path.read_text(encoding="utf-8")
    assert "# Provenance Report" in markdown
    assert "cms.pileup.2024" in markdown
    assert "<html" in html
    assert "Provenance Report" in html


def test_report_template_resolves_relative_to_author(tmp_path: Path) -> None:
    template = tmp_path / "local-report.md.j2"
    template.write_text("# Local report\n\nRun: {{ run.id }}\n", encoding="utf-8")
    output = tmp_path / "reports" / "local.md"

    run_report_template(
        report_context=_context(),
        source="provenance",
        template="local-report.md.j2",
        outputs=[{"path": str(output), "format": "markdown"}],
        ctx={"author_dir": str(tmp_path)},
    )

    assert output.read_text(encoding="utf-8") == "# Local report\n\nRun: run-1\n"


def test_report_template_rejects_unknown_template(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="was not registered"):
        run_report_template(
            report_context=_context(),
            source="provenance",
            template="missing.md.j2",
            outputs=[{"path": str(tmp_path / "out.md"), "format": "markdown"}],
            ctx={"author_dir": str(tmp_path)},
        )


def _context() -> dict:
    return {
        "run": {
            "id": "run-1",
            "workflow": {"graph": "graph/graph.json", "plan": "compile/plan.yaml"},
            "summary": {"summary_path": "run_summary.yaml"},
        },
        "software_versions": {"fasthep-flow": "0.1"},
        "environment": {"host": "worker"},
        "resources": [
            {
                "id": "cms.pileup.2024",
                "requested_era": "RunIII2024Summer24",
                "selected_era": "2023_Summer23",
                "fallback": True,
                "correction": "Collisions2023",
            }
        ],
        "executions": [
            {
                "node_id": "stage.PileupWeights",
                "impl": "chip.pileup_weights",
                "role": "transform",
                "dataset": "dy",
                "partition": "events__dy__0",
                "operations": [
                    {
                        "inputs": {
                            "symbols": ["Pileup_nTrueInt"],
                            "resources": ["cms.pileup.2024"],
                        },
                        "outputs": {"symbols": ["weight_pu_nominal"]},
                    }
                ],
            }
        ],
        "artifacts": [
            {
                "path": "artifacts/files/out.root",
                "kind": "root_tree",
                "node_id": "write.FilterChannel.0",
            }
        ],
        "warnings": [],
    }
