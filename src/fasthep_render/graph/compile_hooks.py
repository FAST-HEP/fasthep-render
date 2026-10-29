from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

from hepflow.build_layout import BuildPaths

from fasthep_render.api import render_path
from fasthep_render.model import RenderStatus

# Rendering a large graph.d2 to SVG takes minutes (a 487 KB graph took about 4 minutes),
# so the compile hook skips graphs above this size (typical graphs are below 10 kB);
# `fasthep render graph` renders them.
DEFAULT_MAX_D2_BYTES = 50_000

GRAPH_D2_RENDER_HOOK_SPEC = {
    "name": "fasthep.render.graph_d2",
    "kind": "compile_hook",
    "version": "1.0",
    "lifecycle": {"when": "after_compile"},
    "input": {"artifacts": ["graph_d2"]},
    "result": {"artifacts": ["graph_render"]},
}


def render_graph_d2_hook(ctx: Any, **params: Any) -> dict[str, Any]:
    max_bytes = int(params.get("max_d2_bytes", DEFAULT_MAX_D2_BYTES))
    return {
        "graph_render": render_compile_graph(ctx.build_paths.root, max_bytes=max_bytes)
    }


def render_compile_graph(
    build_root: str | Path, *, max_bytes: int | None = None
) -> dict[str, Any]:
    """Render ``graph/graph.d2`` of a compile output directory to ``graph/graph.svg``.

    With ``max_bytes``, a larger graph is skipped with a warning naming the command that
    renders it.
    """
    build_paths = BuildPaths(root=Path(build_root))
    graph_dir = build_paths.graph_dir()
    graph_d2 = graph_dir / "graph.d2"
    graph_svg = graph_dir / "graph.svg"

    if not graph_d2.is_file():
        return _skipped(
            f"graph D2 file does not exist: {graph_d2}", graph_d2, graph_svg
        )

    size = graph_d2.stat().st_size
    if max_bytes is not None and size > max_bytes:
        message = (
            f"graph D2 file is {size / 1000:.0f} kB (limit {max_bytes / 1000:.0f} kB); skipped "
            f"the SVG render, which can take minutes. Render it with: "
            f"fasthep render graph {build_paths.root}"
        )
        warnings.warn(message, stacklevel=2)
        return _skipped(message, graph_d2, graph_svg)

    outcome = render_path(
        "d2",
        graph_d2,
        graph_svg,
        plan_path=build_paths.compile_file("plan.yaml"),
    )
    return {
        "status": outcome.status.value,
        "message": outcome.message,
        "input": str(graph_d2),
        "output": str(outcome.output_path),
        "meta": outcome.meta,
    }


def _skipped(message: str, graph_d2: Path, graph_svg: Path) -> dict[str, Any]:
    return {
        "status": RenderStatus.SKIPPED.value,
        "message": message,
        "input": str(graph_d2),
        "output": str(graph_svg),
    }
