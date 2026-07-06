from __future__ import annotations

from typing import Any

from fasthep_render.api import render_path
from fasthep_render.model import RenderStatus

GRAPH_D2_RENDER_HOOK_SPEC = {
    "name": "fasthep.render.graph_d2",
    "kind": "compile_hook",
    "version": "1.0",
    "lifecycle": {"when": "after_compile"},
    "input": {"artifacts": ["graph_d2"]},
    "result": {"artifacts": ["graph_render"]},
}


def render_graph_d2_hook(ctx: Any, **params: Any) -> dict[str, Any]:
    del params
    graph_dir = ctx.build_paths.graph_dir()
    graph_d2 = graph_dir / "graph.d2"
    graph_png = graph_dir / "graph.png"

    if not graph_d2.is_file():
        return {
            "graph_render": {
                "status": RenderStatus.SKIPPED.value,
                "message": f"graph D2 file does not exist: {graph_d2}",
                "input": str(graph_d2),
                "output": str(graph_png),
            }
        }

    outcome = render_path(
        "d2",
        graph_d2,
        graph_png,
        plan_path=ctx.build_paths.compile_file("plan.yaml"),
    )
    return {
        "graph_render": {
            "status": outcome.status.value,
            "message": outcome.message,
            "input": str(graph_d2),
            "output": str(outcome.output_path),
            "meta": outcome.meta,
        }
    }
