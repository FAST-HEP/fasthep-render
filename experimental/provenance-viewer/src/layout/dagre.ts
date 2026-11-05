import dagre from "@dagrejs/dagre";
import type { VisibleEntity, VisibleView } from "../model/types";

export interface Placed {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
}

export function sizeOf(n: VisibleEntity): { width: number; height: number } {
  if (n.kind === "summary") return { width: 280, height: n.linear ? 104 : 92 };
  if (n.kind === "boundary") return { width: 240, height: 40 };
  if (n.kind === "dataset") return { width: 240, height: 64 };
  // room for the correction badges below the implementation line
  return { width: 240, height: n.kind === "processing" && (n.resource_ids?.length ?? 0) > 0 ? 80 : 56 };
}

/**
 * Wrap ranks wider than `perRow` boxes into several rows. Parallel siblings (24
 * variations, 9 datasets) would otherwise make one very wide rank and force the
 * fit-to-view zoom down to unreadable. Lower ranks move down to make room.
 */
export function wrapWideRanks(placed: Placed[], perRow = 6, rowGap = 24): Placed[] {
  const byRank = new Map<number, Placed[]>();
  for (const p of placed) {
    const key = Math.round(p.y + p.height / 2);
    byRank.set(key, [...(byRank.get(key) ?? []), p]);
  }
  const out = new Map<string, Placed>();
  let shift = 0;
  for (const key of [...byRank.keys()].sort((a, b) => a - b)) {
    const rank = (byRank.get(key) ?? []).sort((a, b) => a.x - b.x);
    const rows = Math.ceil(rank.length / perRow);
    const height = Math.max(...rank.map((p) => p.height));
    if (rows === 1) {
      for (const p of rank) out.set(p.id, { ...p, y: p.y + shift });
      continue;
    }
    const centre = rank.reduce((s, p) => s + p.x + p.width / 2, 0) / rank.length;
    for (let r = 0; r < rows; r += 1) {
      const row = rank.slice(r * perRow, (r + 1) * perRow);
      const rowWidth = row.reduce((s, p) => s + p.width, 0) + (row.length - 1) * 30;
      let x = centre - rowWidth / 2;
      for (const p of row) {
        out.set(p.id, { ...p, x, y: p.y + shift + r * (height + rowGap) });
        x += p.width + 30;
      }
    }
    shift += (rows - 1) * (height + rowGap);
  }
  return placed.map((p) => out.get(p.id) ?? p);
}

/** Top-to-bottom layered layout. Positions are view state; never stored in the data. */
export function layout(view: VisibleView): { placed: Placed[]; ms: number } {
  const t0 = performance.now();
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "TB", nodesep: 30, ranksep: 50 });
  g.setDefaultEdgeLabel(() => ({}));
  for (const n of view.nodes) g.setNode(n.id, sizeOf(n));
  for (const e of view.edges) g.setEdge(e.source, e.target);
  dagre.layout(g);
  const placed = view.nodes.map((n) => {
    const p = g.node(n.id);
    const { width, height } = sizeOf(n);
    return { id: n.id, x: p.x - width / 2, y: p.y - height / 2, width, height };
  });
  return { placed: wrapWideRanks(placed), ms: performance.now() - t0 };
}
