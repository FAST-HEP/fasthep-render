// Pure view-model functions: no React, no layout coordinates, no fetching.
// These (and the JSON shapes) are the seam a later TUI would share.

import type {
  ArtifactSearchEntry,
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

/** Groups collapsed by default: recorded variations once the graph is large. */
export function defaultCollapsed(graph: ProvenanceGraph, threshold = 200): Set<string> {
  if (graph.nodes.length <= threshold) return new Set();
  return new Set(graph.groups.filter((g) => g.kind === "variation").map((g) => g.id));
}

/**
 * Visible view: every collapsed group becomes one summary node; an entity that is
 * in several collapsed groups belongs to the first. Edges are re-pointed at the
 * summaries, self loops dropped and duplicates merged. Nothing is invented.
 */
export function coarseView(graph: ProvenanceGraph, collapsed: Set<string>): VisibleView {
  const owner = new Map<string, string>();
  const hidden = new Map<string, number>();
  for (const g of graph.groups) {
    if (!collapsed.has(g.id)) continue;
    for (const id of g.node_ids) {
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
    });
  }
  const visibleId = (id: string) => (owner.has(id) ? `summary:${owner.get(id)}` : id);
  const nodes = [...graph.nodes.filter((n) => !owner.has(n.id)), ...summaries];
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
