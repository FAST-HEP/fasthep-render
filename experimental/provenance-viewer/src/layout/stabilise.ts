import type { Placed } from "./dagre";

/**
 * Keep the picture still after an expansion. Dagre re-lays the whole graph, so
 * nodes that were already visible are shifted back by the median offset between
 * their old and new positions. Layered layout cannot pin every node; this keeps
 * the surroundings of what the user just touched where they were.
 */
export function stabilise(prev: Map<string, Placed> | undefined, next: Placed[]): Placed[] {
  if (!prev) return next;
  const dx: number[] = [];
  const dy: number[] = [];
  for (const n of next) {
    const p = prev.get(n.id);
    if (p) {
      dx.push(p.x - n.x);
      dy.push(p.y - n.y);
    }
  }
  if (dx.length === 0) return next;
  const median = (v: number[]) => v.slice().sort((a, b) => a - b)[Math.floor(v.length / 2)];
  const mx = median(dx);
  const my = median(dy);
  return next.map((n) => ({ ...n, x: n.x + mx, y: n.y + my }));
}
