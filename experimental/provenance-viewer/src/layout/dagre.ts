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
  if (n.kind === "summary") return { width: 280, height: 76 };
  if (n.kind === "dataset") return { width: 240, height: 64 };
  return { width: 240, height: 56 };
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
  return { placed, ms: performance.now() - t0 };
}
