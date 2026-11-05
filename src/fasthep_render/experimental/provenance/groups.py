"""Candidate groups for a lineage graph.

Three kinds, each with an explicit ``origin``:

* ``variation``  (origin ``source``): recorded in ``meta.variation`` of the node;
* ``region``     (origin ``inferred``): branch point up to its merge point
  (immediate post-dominator), a contiguous region with entry and exit edges;
* ``chain``      (origin ``inferred``): maximal linear run of single-in/single-out nodes.

A group has no scheduling fields (see the Snakemake dual-use note in the task seed).
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def _topological(nodes: list[str], succ: dict[str, list[str]]) -> list[str]:
    indeg: dict[str, int] = dict.fromkeys(nodes, 0)
    for n in nodes:
        for s in succ[n]:
            indeg[s] += 1
    ready = sorted(n for n in nodes if indeg[n] == 0)
    order: list[str] = []
    while ready:
        n = ready.pop()
        order.append(n)
        for s in succ[n]:
            indeg[s] -= 1
            if indeg[s] == 0:
                ready.append(s)
    if len(order) != len(nodes):
        msg = "graph has a cycle"
        raise ValueError(msg)
    return order


def _edges_of(
    members: set[str], edges: list[dict[str, Any]]
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    entry = [
        {"source": e["source"], "target": e["target"]}
        for e in edges
        if e["target"] in members and e["source"] not in members
    ]
    exit_ = [
        {"source": e["source"], "target": e["target"]}
        for e in edges
        if e["source"] in members and e["target"] not in members
    ]
    return entry, exit_


def add_variation_family(
    groups: list[dict[str, Any]], edges: list[dict[str, Any]], minimum: int = 3
) -> list[dict[str, Any]]:
    """Put one ``variation_family`` group in front of three or more variation groups.

    The variations are recorded; that they form one family of parallel branches is
    derived, hence ``origin: inferred``. Listed first so it owns its members when
    collapsed; expanding it reveals the variation groups.
    """
    variations = [g for g in groups if g["kind"] == "variation"]
    if len(variations) < minimum:
        return groups
    members = sorted({n for g in variations for n in g["node_ids"]})
    entry, exit_ = _edges_of(set(members), edges)
    family = {
        "id": "family:variations",
        "kind": "variation_family",
        "label": f"{len(variations)} variations",
        "origin": "inferred",
        "source_ref": "derived from the recorded meta.variation groups",
        "child_groups": [g["id"] for g in variations],
        "node_ids": members,
        "entry_edges": entry,
        "exit_edges": exit_,
    }
    return [family, *groups]


def candidate_groups(
    node_ids: list[str],
    edges: list[dict[str, Any]],
    variations: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    succ: dict[str, list[str]] = defaultdict(list)
    pred: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        succ[e["source"]].append(e["target"])
        pred[e["target"]].append(e["source"])
    for n in node_ids:
        succ.setdefault(n, [])
        pred.setdefault(n, [])
    order = _topological(node_ids, succ)
    rank = {n: i for i, n in enumerate(order)}
    groups: list[dict[str, Any]] = []

    # variation groups: recorded
    by_var: dict[str, list[str]] = defaultdict(list)
    for n, var in variations.items():
        by_var[var["name"]].append(n)
    for name, members in sorted(by_var.items()):
        entry, exit_ = _edges_of(set(members), edges)
        groups.append(
            {
                "id": f"variation:{name}",
                "kind": "variation",
                "label": name,
                "origin": "source",
                "source_ref": "graph.json node meta.variation",
                "node_ids": sorted(members),
                "entry_edges": entry,
                "exit_edges": exit_,
            }
        )

    # chains: maximal single-in/single-out runs of length >= 3
    seen: set[str] = set()

    def linkable(a: str, b: str) -> bool:
        return len(succ[a]) == 1 and len(pred[b]) == 1

    for n in order:
        if n in seen:
            continue
        if len(pred[n]) == 1 and linkable(pred[n][0], n):
            continue  # not the start of a chain
        chain = [n]
        while len(succ[chain[-1]]) == 1 and linkable(chain[-1], succ[chain[-1]][0]):
            chain.append(succ[chain[-1]][0])
        seen.update(chain)
        if len(chain) >= 3:
            entry, exit_ = _edges_of(set(chain), edges)
            groups.append(
                {
                    "id": f"chain:{chain[0]}",
                    "kind": "chain",
                    "label": f"{len(chain)} steps from {chain[0]}",
                    "origin": "inferred",
                    "node_ids": chain,
                    "entry_edges": entry,
                    "exit_edges": exit_,
                }
            )

    # regions: branch point to immediate post-dominator
    pdom: dict[str, set[str]] = {}
    for n in reversed(order):
        sets = [pdom[s] for s in succ[n]]
        pdom[n] = {n} | (set.intersection(*sets) if sets else set())
    for n in order:
        if len(succ[n]) < 2:
            continue
        candidates = pdom[n] - {n}
        if not candidates:
            continue  # branches never merge inside the ancestry
        merge = min(candidates, key=lambda x: rank[x])
        region = {n}
        stack = [n]
        while stack:
            cur = stack.pop()
            for s in succ[cur]:
                if s != merge and s not in region:
                    region.add(s)
                    stack.append(s)
        if len(region) < 3:
            continue
        entry, exit_ = _edges_of(region, edges)
        groups.append(
            {
                "id": f"region:{n}",
                "kind": "region",
                "label": f"{n} to {merge}",
                "origin": "inferred",
                "merge_node": merge,
                "node_ids": sorted(region, key=lambda x: rank[x]),
                "entry_edges": entry,
                "exit_edges": exit_,
            }
        )
    return groups
