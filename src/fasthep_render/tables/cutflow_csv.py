from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hepflow.model.issues import FlowIssue

from fasthep_render.api import run_render_sink
from fasthep_render.model import RenderOutcome, RenderStatus
from fasthep_render.render_types import RenderCommonSpec, RenderTypeSpec

CUTFLOW_CSV_RENDER_SPEC = {
    "name": "hep.render.cutflow_csv",
    "kind": "sink",
    "version": "1.0",
    "params": {
        "spec": {"type": "mapping", "required": False},
        "out": {"type": "string", "required": False},
    },
    "result": {"kind": "artifact", "format": "csv"},
}


@dataclass(frozen=True)
class CutflowCsvParams:
    include_dataset: bool = True


def parse_cutflow_csv_params(spec_dict: dict[str, Any]) -> CutflowCsvParams:
    return CutflowCsvParams(**dict(spec_dict.get("cutflow_csv") or {}))


def validate_cutflow_csv_params(
    common: RenderCommonSpec,
    params: CutflowCsvParams,
    context: dict[str, Any],
) -> list[FlowIssue]:
    del common, params, context
    return []


def resolve_cutflow_input(
    common: RenderCommonSpec,
    params: CutflowCsvParams,
    context: dict[str, Any],
) -> dict[str, Any]:
    del common, params
    explicit_inputs = dict(context.get("explicit_inputs") or {})
    default_product = context.get("default_product")
    if explicit_inputs:
        return {"products": explicit_inputs}
    if not default_product:
        msg = "No default cutflow product available for renderer input resolution"
        raise ValueError(msg)
    return {
        "product": str(default_product),
        "level": "global",
        "path": f"{default_product}.json",
    }


CUTFLOW_CSV_RENDER_TYPE = RenderTypeSpec(
    parse_params=parse_cutflow_csv_params,
    validate=validate_cutflow_csv_params,
    resolve_input=resolve_cutflow_input,
)


def run_cutflow_csv_render(target: Any, **kwargs: Any):
    return run_render_sink(
        op="hep.render.cutflow_csv",
        render_type=CUTFLOW_CSV_RENDER_TYPE,
        handler=render_cutflow_csv,
        target=target,
        **kwargs,
    )


FIELD_ORDER = [
    "selection",
    "cut",
    "dataset",
    "n_in",
    "n_out",
    "n_unweighted_in",
    "n_unweighted_out",
    "sumw_in",
    "sumw_out",
    "sumw2_in",
    "sumw2_out",
    "efficiency",
]


def render_cutflow_csv(
    product: dict[str, Any],
    common: RenderCommonSpec,
    params: CutflowCsvParams,
    ctx: dict[str, Any],
) -> RenderOutcome:
    del common
    cutflow = _resolve_cutflow_product(product)
    rows = _cutflow_rows(cutflow, include_dataset=params.include_dataset)
    if not rows:
        msg = "cutflow_csv renderer requires at least one cutflow row"
        raise ValueError(msg)

    out_path = Path(ctx["output_path"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _fieldnames(rows)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return RenderOutcome(
        status=RenderStatus.RENDERED,
        message=None,
        meta={"renderer": "cutflow_csv", "output": str(out_path)},
    )


def _resolve_cutflow_product(product: dict[str, Any]) -> Any:
    if "cutflow" in product:
        return product["cutflow"]
    if "hist" in product:
        return product["hist"]
    return product


def _cutflow_rows(value: Any, *, include_dataset: bool) -> list[dict[str, Any]]:
    if isinstance(value, dict) and value.get("kind") == "cutflow":
        return _graph_cutflow_rows(value, include_dataset=include_dataset)
    if isinstance(value, dict) and isinstance(value.get("cutflows"), list):
        rows: list[dict[str, Any]] = []
        for item in value["cutflows"]:
            rows.extend(_single_cutflow_rows(item, include_dataset=include_dataset))
        return rows
    return _single_cutflow_rows(value, include_dataset=include_dataset)


def _graph_cutflow_rows(value: dict[str, Any], *, include_dataset: bool) -> list[dict[str, Any]]:
    nodes = value.get("nodes")
    if not isinstance(nodes, list):
        msg = "cutflow_csv renderer requires canonical cutflow 'nodes'"
        raise ValueError(msg)

    datasets = value.get("datasets")
    if not isinstance(datasets, list):
        datasets = []

    rows: list[dict[str, Any]] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        stats_by_dataset = node.get("stats")
        if not isinstance(stats_by_dataset, dict):
            continue
        dataset_names = [str(item) for item in datasets] or sorted(stats_by_dataset)
        for dataset in dataset_names:
            stats = stats_by_dataset.get(dataset)
            if not isinstance(stats, dict):
                continue
            row = {
                "selection": node.get("selection", ""),
                "cut": node.get("label", node.get("id", "")),
                "n_in": float(stats.get("n_in", 0.0)),
                "n_out": float(stats.get("n_out", 0.0)),
                "n_unweighted_in": int(stats.get("n_unweighted_in", 0)),
                "n_unweighted_out": int(stats.get("n_unweighted_out", 0)),
                "sumw_in": float(stats.get("sumw_in", 0.0)),
                "sumw_out": float(stats.get("sumw_out", 0.0)),
                "sumw2_in": float(stats.get("sumw2_in", 0.0)),
                "sumw2_out": float(stats.get("sumw2_out", 0.0)),
            }
            if include_dataset:
                row["dataset"] = dataset
            if row["n_unweighted_in"]:
                row["efficiency"] = row["n_unweighted_out"] / row["n_unweighted_in"]
            rows.append(row)
    return rows


def _single_cutflow_rows(value: Any, *, include_dataset: bool) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        msg = "cutflow_csv renderer requires a cutflow mapping"
        raise ValueError(msg)
    cuts = value.get("cuts")
    if not isinstance(cuts, list):
        msg = "cutflow_csv renderer requires a 'cuts' list"
        raise ValueError(msg)

    dataset = value.get("dataset")
    rows: list[dict[str, Any]] = []
    previous_n: float | None = None
    for cut in cuts:
        if not isinstance(cut, dict):
            continue
        row = dict(cut)
        if include_dataset and dataset is not None:
            row.setdefault("dataset", dataset)
        if "efficiency" not in row and previous_n is not None and previous_n != 0:
            row["efficiency"] = float(row.get("n", 0)) / previous_n
        previous_n = float(row.get("n", 0))
        rows.append(row)
    return rows


def _fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    available = {key for row in rows for key in row}
    ordered = [field for field in FIELD_ORDER if field in available]
    ordered.extend(sorted(available - set(ordered)))
    return ordered
