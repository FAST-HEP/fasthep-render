from __future__ import annotations

from typing import Any

from fasthep_render.impl.data_mc import render_data_mc
from fasthep_render.impl.sinks._common import run_render_sink
from fasthep_render.types.data_mc import DATA_MC_RENDER_TYPE


def run_data_mc_render(target: Any, **kwargs: Any):
    return run_render_sink(
        op="hep.render.data_mc",
        render_type=DATA_MC_RENDER_TYPE,
        handler=render_data_mc,
        target=target,
        **kwargs,
    )
