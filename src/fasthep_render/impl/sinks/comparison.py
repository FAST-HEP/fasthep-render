from __future__ import annotations

from typing import Any

from fasthep_render.impl.comparison import render_comparison
from fasthep_render.impl.sinks._common import run_render_sink
from fasthep_render.types.comparison import COMPARISON_RENDER_TYPE


def run_comparison_render(target: Any, **kwargs: Any):
    return run_render_sink(
        op="hep.render.comparison",
        render_type=COMPARISON_RENDER_TYPE,
        handler=render_comparison,
        target=target,
        **kwargs,
    )
