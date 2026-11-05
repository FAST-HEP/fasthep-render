import { describe, expect, it } from "vitest";
import { type Placed, wrapWideRanks } from "./dagre";

const box = (id: string, x: number, y: number): Placed => ({ id, x, y, width: 100, height: 40 });

describe("wrapWideRanks", () => {
  it("leaves narrow ranks alone", () => {
    const p = [box("a", 0, 0), box("b", 150, 0), box("c", 70, 100)];
    expect(wrapWideRanks(p, 6)).toEqual(p);
  });

  it("wraps a wide rank into rows and pushes lower ranks down", () => {
    const wide = Array.from({ length: 7 }, (_, i) => box(`w${i}`, i * 130, 0));
    const below = box("z", 300, 100);
    const out = wrapWideRanks([...wide, below], 3, 20);
    const ys = new Set(out.filter((p) => p.id.startsWith("w")).map((p) => p.y));
    expect([...ys].sort((a, b) => a - b)).toEqual([0, 60, 120]);
    expect(out.find((p) => p.id === "z")?.y).toBe(100 + 2 * 60);
    expect(new Set(out.map((p) => `${p.x},${p.y}`)).size).toBe(out.length); // no overlap on a cell
  });
});
