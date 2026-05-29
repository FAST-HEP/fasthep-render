from __future__ import annotations

from typing import Any

from fasthep_render.impl.cutflow_csv import render_cutflow_csv
from fasthep_render.impl.sinks._common import run_render_sink
from fasthep_render.types.cutflow_csv import CUTFLOW_CSV_RENDER_TYPE


def run_cutflow_csv_render(target: Any, **kwargs: Any):
    return run_render_sink(
        op="hep.render.cutflow_csv",
        render_type=CUTFLOW_CSV_RENDER_TYPE,
        handler=render_cutflow_csv,
        target=target,
        **kwargs,
    )
