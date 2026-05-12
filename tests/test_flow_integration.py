from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import hist

from hepflow.compiler.profiles import load_profile_config
from hepflow.model.plan import ExecutionNode, ExecutionPlan, PlanInputRef
from hepflow.runtime.engine import execute_plan_partition


def test_flow_executes_render_sink_from_profile(tmp_path) -> None:
    profile = load_profile_config("fasthep_render:registry", project_root=tmp_path)
    h = hist.Hist(hist.axis.Regular(5, 0, 5, name="x", label="x"))
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
    assert result.path == str(tmp_path / "run" / "artifacts" / "hist_plot.png")
    assert (tmp_path / "run" / "artifacts" / "hist_plot.png").is_file()
