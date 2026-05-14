from __future__ import annotations

import networkx as nx
from hepflow.model.graph import GraphNode
from networkx.drawing.nx_pydot import to_pydot

_NODE_STYLES: dict[str, dict[str, str]] = {
    "reader": {"shape": "oval", "fillcolor": "#E3F2FD"},
    "transform": {"shape": "box", "fillcolor": "#E8F5E9"},
    "observer": {"shape": "diamond", "fillcolor": "#FFF3E0"},
    "sink": {"shape": "ellipse", "fillcolor": "#F3E5F5"},
    "default": {"shape": "box", "fillcolor": "#F5F5F5"},
}


def graph_to_pydot(graph: nx.DiGraph):
    """
    Convert networkx graph → pydot graph with styling applied.
    """
    g = nx.DiGraph()

    # --- Nodes ---
    for node_id in graph.nodes:
        payload: GraphNode = graph.nodes[node_id]["payload"]

        style = _NODE_STYLES.get(payload.role, _NODE_STYLES["default"])

        g.add_node(
            node_id,
            label=_label(payload),
            shape=style["shape"],
            style="filled",
            fillcolor=style["fillcolor"],
        )

    # --- Edges ---
    for u, v, data in graph.edges(data=True):
        label = data.get("output", "")
        if label:
            g.add_edge(u, v, label=label)
        else:
            g.add_edge(u, v)

    return to_pydot(g)


def write_graph_svg(graph: nx.DiGraph, path: str) -> None:
    """
    Write graph to SVG file.
    """
    pydot_graph = graph_to_pydot(graph)
    pydot_graph.write_svg(path)


def write_graph_png(graph: nx.DiGraph, path: str) -> None:
    """
    Write graph to PNG file.
    """
    pydot_graph = graph_to_pydot(graph)
    pydot_graph.write_png(path)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _label(node: GraphNode) -> str:
    """
    Graphviz uses \\n for newlines.
    """
    return f"{node.id}\\n{node.role}\\n{node.impl}"
