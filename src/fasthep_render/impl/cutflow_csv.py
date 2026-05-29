from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from hepflow.model.render import RenderOutcome, RenderStatus
from hepflow.model.render_types import RenderCommonSpec

from fasthep_render.types.cutflow_csv import CutflowCsvParams

FIELD_ORDER = [
    "dataset",
    "name",
    "n",
    "sumw",
    "sumw2",
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
    if isinstance(value, dict) and isinstance(value.get("cutflows"), list):
        rows: list[dict[str, Any]] = []
        for item in value["cutflows"]:
            rows.extend(_single_cutflow_rows(item, include_dataset=include_dataset))
        return rows
    return _single_cutflow_rows(value, include_dataset=include_dataset)


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
