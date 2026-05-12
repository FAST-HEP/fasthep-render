from __future__ import annotations

from typing import Any

from fasthep_render.impl.project import render_project_then
from fasthep_render.impl.sinks._common import run_render_sink
from fasthep_render.types.project import PROJECT_RENDER_TYPE


def run_project_render(target: Any, **kwargs: Any):
    return run_render_sink(
        op="hep.render.project",
        render_type=PROJECT_RENDER_TYPE,
        handler=render_project_then,
        target=target,
        **kwargs,
    )
