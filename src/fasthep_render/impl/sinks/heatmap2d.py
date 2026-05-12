from __future__ import annotations

from typing import Any

from fasthep_render.impl.heatmap2d import render_heatmap2d
from fasthep_render.impl.sinks._common import run_render_sink
from fasthep_render.types.heatmap2d import HEATMAP2D_RENDER_TYPE


def run_heatmap2d_render(target: Any, **kwargs: Any):
    return run_render_sink(
        op="hep.render.heatmap2d",
        render_type=HEATMAP2D_RENDER_TYPE,
        handler=render_heatmap2d,
        target=target,
        **kwargs,
    )
