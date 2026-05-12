from __future__ import annotations

from typing import Any

from fasthep_render.impl.hist1d import render_hist1d
from fasthep_render.impl.sinks._common import run_render_sink
from fasthep_render.types.hist1d import HIST1D_RENDER_TYPE


def run_hist1d_render(target: Any, **kwargs: Any):
    return run_render_sink(
        op="hep.render.hist1d",
        render_type=HIST1D_RENDER_TYPE,
        handler=render_hist1d,
        target=target,
        **kwargs,
    )
