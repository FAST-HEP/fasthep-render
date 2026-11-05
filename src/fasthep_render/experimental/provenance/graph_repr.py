"""Parse the ``GraphNode(...)`` repr strings found in ``graph/graph.json``.

Flow currently writes graph nodes as ``{"id": ..., "payload": "GraphNode(...)"}``.
The repr is parsed with ``ast`` (literals only, nothing is evaluated). Needing this
is itself an upstream ask: the graph should be structured JSON.
"""

from __future__ import annotations

import ast
from typing import Any


def parse_graph_node(payload: str) -> dict[str, Any]:
    tree = ast.parse(payload, mode="eval")
    call = tree.body
    if not isinstance(call, ast.Call) or getattr(call.func, "id", None) != "GraphNode":
        msg = "payload is not a GraphNode(...) call"
        raise ValueError(msg)
    return {kw.arg: ast.literal_eval(kw.value) for kw in call.keywords if kw.arg}
