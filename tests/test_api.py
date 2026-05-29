from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import hist
import pytest
import yaml
from hepflow.model.render import RenderOutcome as FlowRenderOutcome
from hepflow.model.render import RenderStatus
from hepflow.utils import write_pickle

import fasthep_render.api as render_api
from fasthep_render.api import render_spec_file


def test_render_spec_file_resolves_op_from_impl(
    tmp_path: Path,
    gaussian_hist1d: hist.Hist,
) -> None:
    spec = _write_spec(tmp_path, impl="hep.render.hist1d")
    product = tmp_path / "hist.pkl"
    out = tmp_path / "plot.png"
    write_pickle(gaussian_hist1d, product)

    outcome = render_spec_file(spec, product=product, out=out)

    assert outcome.status == RenderStatus.RENDERED
    assert outcome.output_path == out
    assert out.is_file()


def test_render_spec_file_resolves_op_from_nested_spec(
    tmp_path: Path,
    gaussian_hist1d: hist.Hist,
) -> None:
    spec = _write_spec(tmp_path, include_impl=False)
    product = tmp_path / "hist.pkl"
    out = tmp_path / "plot.png"
    write_pickle(gaussian_hist1d, product)

    outcome = render_spec_file(spec, product=product, out=out)

    assert outcome.status == RenderStatus.RENDERED
    assert out.is_file()


def test_render_spec_file_requires_product(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path)

    with pytest.raises(ValueError, match="explicit product path"):
        render_spec_file(spec)


def test_render_spec_file_reports_missing_product_path(tmp_path: Path) -> None:
    spec = _write_spec(tmp_path)

    with pytest.raises(ValueError, match="product path does not exist"):
        render_spec_file(spec, product=tmp_path / "missing.pkl")


def test_render_spec_file_loads_explicit_product_path(
    tmp_path: Path,
    gaussian_hist1d: hist.Hist,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _write_spec(tmp_path)
    product = tmp_path / "hist.pkl"
    out = tmp_path / "plot.png"
    write_pickle(gaussian_hist1d, product)
    seen: dict[str, Any] = {}

    def fake_render_resolved(**kwargs: Any) -> FlowRenderOutcome:
        seen.update(kwargs)
        return FlowRenderOutcome(
            status=RenderStatus.RENDERED,
            meta={"output": str(out)},
        )

    monkeypatch.setattr(render_api, "render_resolved", fake_render_resolved)

    outcome = render_spec_file(spec, product=product, out=out)

    assert outcome.product_paths == {"hist": product}
    assert seen["product"]["hist"].axes[0].name == "mass"


def test_render_spec_file_out_override_wins(
    tmp_path: Path,
    gaussian_hist1d: hist.Hist,
) -> None:
    spec_output = tmp_path / "from-spec.png"
    spec = _write_spec(tmp_path, out=str(spec_output))
    product = tmp_path / "hist.pkl"
    override = tmp_path / "override.png"
    write_pickle(gaussian_hist1d, product)

    outcome = render_spec_file(spec, product=product, out=override)

    assert outcome.output_path == override
    assert override.is_file()
    assert not spec_output.exists()


def test_render_spec_file_rejects_invalid_spec(tmp_path: Path) -> None:
    spec = tmp_path / "render.yaml"
    spec.write_text(yaml.safe_dump(["not", "a", "mapping"]), encoding="utf-8")

    with pytest.raises(ValueError, match="YAML mapping"):
        render_spec_file(spec, product=tmp_path / "missing.pkl")


def test_render_spec_file_accepts_plan_path(
    tmp_path: Path,
    gaussian_hist1d: hist.Hist,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = _write_spec(tmp_path)
    product = tmp_path / "hist.pkl"
    plan = tmp_path / "plan.yaml"
    out = tmp_path / "plot.png"
    write_pickle(gaussian_hist1d, product)
    plan.write_text("registry: {}\n", encoding="utf-8")
    seen: dict[str, Any] = {}

    def fake_render_resolved(**kwargs: Any) -> FlowRenderOutcome:
        seen.update(kwargs)
        return FlowRenderOutcome(
            status=RenderStatus.RENDERED,
            meta={"output": str(out)},
        )

    monkeypatch.setattr(render_api, "render_resolved", fake_render_resolved)

    render_spec_file(spec, product=product, out=out, plan_path=plan)

    assert seen["ctx"]["plan_path"] == str(plan)
    assert seen["ctx"]["plan"] == {"registry": {}}


def test_render_spec_file_renders_cutflow_json_product(tmp_path: Path) -> None:
    spec = tmp_path / "render_cutflow.yaml"
    product = tmp_path / "EventSelection.json"
    out = tmp_path / "EventSelection.csv"
    spec.write_text(
        yaml.safe_dump(
            {
                "node_id": "render.EventSelection.0",
                "impl": "hep.render.cutflow_csv",
                "out": "EventSelection.csv",
                "product": {
                    "kind": "cutflow",
                    "path": "artifacts/cutflows/EventSelection.json",
                },
                "spec": {"op": "hep.render.cutflow_csv"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    product.write_text(
        json.dumps(
            {
                "version": "1.0",
                "kind": "cutflow",
                "producer": "stage.EventSelection",
                "datasets": ["data"],
                "nodes": [
                    {
                        "id": "All[0]",
                        "selection": "All",
                        "index": 0,
                        "label": "NIsoMuon >= 2",
                        "expr": "NIsoMuon >= 2",
                        "kind": "expression",
                        "parents": [],
                        "stats": {
                            "data": {
                                "n_in": 8,
                                "n_out": 4,
                                "sumw_in": 8.0,
                                "sumw_out": 4.0,
                                "sumw2_in": 8.0,
                                "sumw2_out": 4.0,
                            }
                        },
                    }
                ],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )

    outcome = render_spec_file(spec, product=product, out=out)

    assert outcome.status == RenderStatus.RENDERED
    assert "All,NIsoMuon >= 2,data,8,4" in out.read_text(encoding="utf-8")


def _write_spec(
    tmp_path: Path,
    *,
    impl: str = "hep.render.hist1d",
    include_impl: bool = True,
    out: str = "plot.png",
) -> Path:
    doc: dict[str, Any] = {
        "node_id": "render.test.0",
        "out": out,
        "spec": {
            "op": "hep.render.hist1d",
            "axes": {
                "x": {"name": "mass", "label": "m"},
                "y": {"name": "events", "label": "Events"},
            },
        },
    }
    if include_impl:
        doc["impl"] = impl
    path = tmp_path / "render.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return path
