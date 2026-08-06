from __future__ import annotations

import json
from pathlib import Path

from fasthep_render.reports.schema_validation import (
    prepare_schema_validation_context,
    run_schema_validation_render,
)


def test_schema_validation_context_derives_counts_ratios_and_details() -> None:
    context = prepare_schema_validation_context(
        {"mc": _comparison()},
        labels={
            "mc": {
                "label": "MC",
                "name": "CompareMCSchemas",
                "reference_label": "Legacy MC",
                "target_label": "FAST-HEP MC",
            }
        },
    )

    comparison = context["comparisons"][0]
    assert comparison["label"] == "MC"
    assert comparison["name"] == "CompareMCSchemas"
    assert comparison["reference_label"] == "Legacy MC"
    assert comparison["target_label"] == "FAST-HEP MC"
    assert comparison["counts"] == {
        "reference": 5,
        "target": 5,
        "common": 3,
        "compatible": 1,
        "incompatible": 2,
        "only_in_reference": 2,
        "only_in_target": 2,
    }
    assert comparison["ratios"]["common_over_reference"]["label"] == "60.0%"
    assert comparison["ratios"]["compatible_over_common"]["label"] == "33.3%"
    assert comparison["only_in_reference"] == ["legacy_only_a", "legacy_only_b"]
    assert comparison["only_in_target"] == ["fasthep_only_a", "fasthep_only_b"]
    assert comparison["incompatible_fields"] == [
        {
            "field": "shape_diff",
            "reference_shape": "scalar",
            "target_shape": "jagged",
        },
        {
            "field": "type_diff",
            "reference_type": "int32",
            "target_type": "float",
        },
    ]


def test_schema_validation_context_handles_zero_denominators() -> None:
    context = prepare_schema_validation_context({"data": _empty_comparison()})
    comparison = context["comparisons"][0]

    assert comparison["ratios"]["common_over_reference"]["label"] == "n/a"
    assert comparison["ratios"]["compatible_over_common"]["label"] == "n/a"
    assert comparison["counts"]["incompatible"] == 0


def test_schema_validation_render_writes_markdown_html_and_manifest_metadata(
    tmp_path: Path,
) -> None:
    markdown = tmp_path / "reports" / "schema-validation.md"
    html = tmp_path / "reports" / "schema-validation.html"

    outputs = run_schema_validation_render(
        {
            "mc": {
                **_comparison(),
                "_product": {
                    "node_id": "stage.CompareMCSchemas",
                    "port": "comparison",
                    "kind": "schema_comparison",
                    "path": "artifacts/comparisons/CompareMCSchemas.json",
                },
            },
            "data": _empty_comparison(),
        },
        spec={
            "comparisons": {
                "mc": {"label": "MC"},
                "data": {"label": "Data"},
            },
            "outputs": [
                {"path": "reports/schema-validation.md", "format": "markdown"},
                {"path": "reports/schema-validation.html", "format": "html"},
            ],
        },
        ctx={"outdir": str(tmp_path)},
        meta={"node_id": "render.SchemaValidationReport.0"},
    )

    assert [output.format for output in outputs] == ["markdown", "html"]
    report = markdown.read_text(encoding="utf-8")
    html_text = html.read_text(encoding="utf-8")
    assert "# Schema Validation Report" in report
    assert "reference = legacy" in report
    assert "target = FAST-HEP" in report
    assert "not equivalent productions" in report
    assert "| MC | 3 | 1 | 2 | 2 | 2 |" in report
    assert "`legacy_only_a`" in report
    assert "`legacy_only_b`" in report
    assert "`fasthep_only_a`" in report
    assert "`fasthep_only_b`" in report
    assert "| `type_diff` | int32 | float |  |  |" in report
    assert "No fields are missing from FAST-HEP." in report
    assert "No additional fields are present in FAST-HEP." in report
    assert "No common fields are incompatible." in report
    assert "shared" not in report
    assert "<html" in html_text
    assert "Schema Validation Report" in html_text
    manifest = outputs[0].metadata["writer_manifest"]
    assert manifest["path"] == "reports/schema-validation.md"
    assert manifest["inputs"] == [
        {
            "name": "mc",
            "node_id": "stage.CompareMCSchemas",
            "port": "comparison",
            "path": "artifacts/comparisons/CompareMCSchemas.json",
            "kind": "schema_comparison",
        }
    ]


def test_schema_validation_render_does_not_mutate_comparison_product(tmp_path: Path) -> None:
    comparison = _comparison()
    before = json.loads(json.dumps(comparison, sort_keys=True))

    run_schema_validation_render(
        {"mc": comparison},
        spec={
            "outputs": [
                {"path": "reports/schema-validation.md", "format": "markdown"},
            ],
        },
        ctx={"outdir": str(tmp_path)},
    )

    assert comparison == before


def _comparison() -> dict:
    return {
        "kind": "schema_comparison",
        "reference": "legacy_mc",
        "target": "fasthep_mc",
        "reference_dataset": "legacy_mc",
        "target_dataset": "fasthep_mc",
        "common_fields": ["shape_diff", "shared", "type_diff"],
        "compatible_fields": ["shared"],
        "only_in_reference": ["legacy_only_a", "legacy_only_b"],
        "only_in_target": ["fasthep_only_a", "fasthep_only_b"],
        "type_mismatches": [
            {"field": "type_diff", "reference": "int32", "target": "float"}
        ],
        "shape_mismatches": [
            {"field": "shape_diff", "reference": "scalar", "target": "jagged"}
        ],
        "summary": {
            "reference_fields": 5,
            "target_fields": 5,
            "common_fields": 3,
            "compatible_fields": 1,
            "only_in_reference": 2,
            "only_in_target": 2,
        },
    }


def _empty_comparison() -> dict:
    return {
        "kind": "schema_comparison",
        "reference": "legacy_data",
        "target": "fasthep_data",
        "common_fields": [],
        "compatible_fields": [],
        "only_in_reference": [],
        "only_in_target": [],
        "type_mismatches": [],
        "shape_mismatches": [],
        "summary": {
            "reference_fields": 0,
            "target_fields": 0,
            "common_fields": 0,
            "compatible_fields": 0,
            "only_in_reference": 0,
            "only_in_target": 0,
        },
    }
