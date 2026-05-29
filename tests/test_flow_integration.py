from __future__ import annotations

import matplotlib as mpl

mpl.use("Agg")

import hist
from hepflow.compiler.profiles import load_profile_config
from hepflow.model.plan import ExecutionNode, ExecutionPlan, PlanInputRef
from hepflow.runtime.engine import execute_plan_partition


def test_flow_executes_render_sink_from_profile(tmp_path) -> None:
    profile = load_profile_config("fasthep_render:registry", project_root=tmp_path)
    h: hist.Hist = hist.Hist(hist.axis.Regular(5, 0, 5, name="x", label="x"))
    h.fill([0.5, 1.5, 1.5, 3.5])
    plan = ExecutionPlan(registry=profile["registry"])
    plan.add_node(
        ExecutionNode(
            id="render.Hist.0",
            graph_node_id="render.Hist.0",
            role="sink",
            impl="hep.render.hist1d",
            inputs=[PlanInputRef("stage.Hist", "hist", "target")],
            params={
                "when": "partition",
                "out": "hist_plot",
                "spec": {
                    "axes": {"x": {"name": "x", "label": "x"}, "y": {"name": "y"}}
                },
            },
            outputs={"artifact": "artifact"},
            meta={"stage_id": "render.Hist.0"},
        )
    )

    value_store = execute_plan_partition(
        plan,
        ctx={"outdir": str(tmp_path / "run")},
        initial_values={("stage.Hist", "hist"): h},
    )

    result = value_store[("render.Hist.0", "artifact")]
    assert result.path.endswith("/artifacts/hist_plot.png") or result.path.endswith(
        "/artifacts/plots/hist_plot.png"
    )
    assert result.path.endswith("hist_plot.png")
    assert (tmp_path / "run" / "artifacts" / "hist_plot.png").is_file() or (
        tmp_path / "run" / "artifacts" / "plots" / "hist_plot.png"
    ).is_file()


def test_flow_project_render_uses_runtime_renderer_registry(
    tmp_path,
    dataset_axis_hist1d: hist.Hist,
) -> None:
    profile = load_profile_config("fasthep_render:registry", project_root=tmp_path)
    plan = ExecutionPlan(registry=profile["registry"])
    plan.add_node(
        ExecutionNode(
            id="render.Project.0",
            graph_node_id="render.Project.0",
            role="sink",
            impl="hep.render.project",
            inputs=[PlanInputRef("stage.Hist2D", "hist", "target")],
            params={
                "when": "partition",
                "out": "projected_pt",
                "spec": {
                    "axes": {
                        "x": {"name": "mass", "label": "m(ll) [GeV]"},
                        "y": {"name": "events", "label": "Events"},
                    },
                    "project": {
                        "axis": "mass",
                        "then": {
                            "op": "hep.render.data_mc",
                            "data_mc": {
                                "data": "data",
                                "backgrounds": ["zjets", "ttbar"],
                                "signals": ["signal"],
                                "include_signals_in_stack": False,
                            },
                        },
                    },
                },
            },
            outputs={"artifact": "artifact"},
            meta={"stage_id": "render.Project.0"},
        )
    )

    value_store = execute_plan_partition(
        plan,
        ctx={
            "outdir": str(tmp_path / "run"),
            "render_validation": {
                "available_datasets": ["data", "zjets", "ttbar", "signal"]
            },
        },
        initial_values={("stage.Hist2D", "hist"): dataset_axis_hist1d},
    )

    result = value_store[("render.Project.0", "artifact")]
    assert result.path.endswith("/artifacts/projected_pt.png") or result.path.endswith(
        "/artifacts/plots/projected_pt.png"
    )
    assert result.path.endswith("projected_pt.png")
    assert (tmp_path / "run" / "artifacts" / "projected_pt.png").is_file() or (
        tmp_path / "run" / "artifacts" / "plots" / "projected_pt.png"
    ).is_file()
