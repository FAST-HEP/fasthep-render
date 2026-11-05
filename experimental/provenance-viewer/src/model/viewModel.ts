// Pure view-model functions: no React, no layout coordinates, no fetching.
// These (and the JSON shapes) are the seam a later TUI would share.

import type {
  ArtifactSearchEntry,
  BoundaryEntity,
  Collapsed,
  ProvenanceGraph,
  RunIndex,
  SummaryEntity,
  VisibleView,
} from "./types";

/** Case-insensitive AND search over name, path, kind and producer. */
export function searchArtifacts(index: RunIndex, query: string): ArtifactSearchEntry[] {
  const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
  return index.artifacts.filter((a) => {
    const hay = `${a.name} ${a.path} ${a.kind} ${a.producer_id ?? ""}`.toLowerCase();
    return tokens.every((t) => hay.includes(t));
  });
}

/**
 * Initial collapse. Recorded variation groups once the graph is large; dataset
 * groups; and the interior of every linear run of four or more steps (the first
 * and last step stay visible).
 */
export function defaultCollapsed(graph: ProvenanceGraph, threshold = 200): Collapsed {
  const out: Collapsed = new Map();
  const large = graph.nodes.length > threshold;
  for (const g of graph.groups) {
    const n = g.node_ids.length;
    if (g.kind === "variation" && large) out.set(g.id, { lo: 0, hi: n });
    else if (g.kind === "datasets" || g.kind === "variation_family") out.set(g.id, { lo: 0, hi: n });
    else if (g.kind === "chain" && n >= 4) out.set(g.id, { lo: 1, hi: n - 1 });
  }
  return out;
}

/**
 * Visible view: the hidden range of every collapsed group becomes one summary node.
 * An entity in several collapsed groups belongs to the first. Edges are re-pointed
 * at the summaries, self loops dropped and duplicates merged. Nothing is invented.
 */
export function coarseView(graph: ProvenanceGraph, collapsed: Collapsed): VisibleView {
  const owner = new Map<string, string>();
  const hidden = new Map<string, number>();
  for (const g of graph.groups) {
    const range = collapsed.get(g.id);
    if (!range) continue;
    for (const id of g.node_ids.slice(range.lo, range.hi)) {
      if (!owner.has(id)) {
        owner.set(id, g.id);
        hidden.set(g.id, (hidden.get(g.id) ?? 0) + 1);
      }
    }
  }
  const summaries: SummaryEntity[] = [];
  for (const g of graph.groups) {
    const count = hidden.get(g.id);
    if (!count) continue;
    summaries.push({
      kind: "summary",
      id: `summary:${g.id}`,
      groupId: g.id,
      label: g.label,
      groupKind: g.kind,
      origin: g.origin,
      hiddenCount: count,
      linear: g.kind === "chain",
    });
  }
  const visibleId = (id: string) => (owner.has(id) ? `summary:${owner.get(id)}` : id);
  const nodes: VisibleView["nodes"] = [...graph.nodes.filter((n) => !owner.has(n.id)), ...summaries];
  const seen = new Set<string>();
  const edges: { source: string; target: string }[] = [];
  for (const e of graph.edges) {
    const source = visibleId(e.source);
    const target = visibleId(e.target);
    const key = `${source}\u0000${target}`;
    if (source === target || seen.has(key)) continue;
    seen.add(key);
    edges.push({ source, target });
  }
  return { nodes, edges };
}

/** Reveal one step from the dataset-facing end of a linear run. */
export function revealFromSource(collapsed: Collapsed, groupId: string): Collapsed {
  const r = collapsed.get(groupId);
  if (!r) return collapsed;
  const next = new Map(collapsed);
  if (r.lo + 1 >= r.hi) next.delete(groupId);
  else next.set(groupId, { lo: r.lo + 1, hi: r.hi });
  return next;
}

/** Reveal one step from the artifact-facing end of a linear run. */
export function revealFromArtifact(collapsed: Collapsed, groupId: string): Collapsed {
  const r = collapsed.get(groupId);
  if (!r) return collapsed;
  const next = new Map(collapsed);
  if (r.hi - 1 <= r.lo) next.delete(groupId);
  else next.set(groupId, { lo: r.lo, hi: r.hi - 1 });
  return next;
}

export function expandGroup(collapsed: Collapsed, groupId: string): Collapsed {
  if (!collapsed.has(groupId)) return collapsed;
  const next = new Map(collapsed);
  next.delete(groupId);
  return next;
}

/**
 * Focus on one group: a graph of just its members, the groups that lie wholly
 * inside it, and one boundary stand-in per outside neighbour, so the connections
 * entering and leaving stay visible. The result is an ordinary graph: apply
 * `defaultCollapsed` and `coarseView` to it, and focus again to go deeper.
 */
export function focusSubgraph(graph: ProvenanceGraph, groupId: string): ProvenanceGraph | undefined {
  const group = graph.groups.find((g) => g.id === groupId);
  if (!group) return undefined;
  const members = new Set(group.node_ids);
  const nodes: ProvenanceGraph["nodes"] = graph.nodes.filter((n) => members.has(n.id));
  const boundary = new Map<string, BoundaryEntity>();
  const edges: ProvenanceGraph["edges"] = [];
  const seen = new Set<string>();
  const add = (source: string, target: string) => {
    const key = `${source}\u0000${target}`;
    if (!seen.has(key)) {
      seen.add(key);
      edges.push({ source, target });
    }
  };
  const labels = new Map(graph.nodes.map((n) => [n.id, n.kind === "boundary" ? n.label : n.id]));
  const stand = (id: string, direction: "in" | "out") => {
    const label = labels.get(id) ?? id; // an existing stand-in keeps its original name
    const key = `outside:${direction}:${label}`;
    if (!boundary.has(key)) boundary.set(key, { kind: "boundary", id: key, label, direction });
    return key;
  };
  for (const e of graph.edges) {
    const s = members.has(e.source);
    const t = members.has(e.target);
    if (s && t) add(e.source, e.target);
    else if (t) add(stand(e.source, "in"), e.target);
    else if (s) add(e.source, stand(e.target, "out"));
  }
  const groups = graph.groups.filter((g) => g.id !== groupId && g.node_ids.every((n) => members.has(n)));
  return { ...graph, nodes: [...nodes, ...boundary.values()], edges, groups };
}

export interface Route {
  runId?: string;
  artifactId?: string;
}

/** Hash routing keeps the app static: `#/<run>/<artifact>`. */
export function parseRoute(hash: string): Route {
  const [runId, artifactId] = hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  return { runId, artifactId };
}

export function formatRoute(route: Route): string {
  const parts = [route.runId, route.runId ? route.artifactId : undefined].filter(Boolean);
  return parts.length ? `#/${parts.join("/")}` : "#/";
}

/** The selected entity if it is currently visible; the selection itself survives hiding. */
export function visibleSelection(view: VisibleView, selectedId?: string) {
  return selectedId === undefined ? undefined : view.nodes.find((n) => n.id === selectedId);
}
