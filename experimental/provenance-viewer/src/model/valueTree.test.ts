import { describe, expect, it } from "vitest";
import { toRows } from "./valueTree";

describe("toRows", () => {
  it("shows scalars as they are and keeps null and empty distinct from missing", () => {
    const rows = toRows({ a: 25, b: "", c: null, d: "x" });
    expect(rows.map((r) => [r.key, r.text])).toEqual([
      ["a", "25"],
      ["b", "(empty)"],
      ["c", "null"],
      ["d", "x"],
    ]);
    expect(toRows(undefined)).toEqual([]);
  });

  it("nests objects and names array items of objects by name", () => {
    const rows = toRows({
      variables: [
        { name: "Muon_Pt", expr: "sqrt(Muon_Px ** 2 + Muon_Py ** 2)" },
        { name: "IsoMuon_Idx", expr: "(Muon_Iso / Muon_Pt) < 0.10" },
      ],
    });
    expect(rows[0].text).toBe("[2 items]");
    expect(rows[0].children?.map((c) => c.key)).toEqual(["Muon_Pt", "IsoMuon_Idx"]);
    const expr = rows[0].children?.[0].children?.find((c) => c.key === "expr");
    expect(expr?.text).toBe("sqrt(Muon_Px ** 2 + Muon_Py ** 2)");
    expect(expr?.full).toBe(expr?.text);
  });

  it("summarises containers and shows short scalar lists inline", () => {
    const rows = toRows({ branches: ["a", "b", "c"], many: [1, 2, 3, 4, 5, 6, 7], o: { x: 1, y: 2 }, e: {}, items: [{ k: 1 }] });
    const by = Object.fromEntries(rows.map((r) => [r.key, r]));
    expect(by.branches.text).toBe("a, b, c");
    expect(by.branches.children).toBeUndefined();
    expect(by.many.text).toBe("[7 items]");
    expect(by.o.text).toBe("{2 keys}");
    expect(by.e.text).toBe("{}");
    expect(by.items.children?.[0].key).toBe("[0]");
  });

  it("keeps the complete text for the hover title", () => {
    const [row] = toRows({ o: { x: [1, 2], y: "z" } });
    expect(row.full).toBe('{"x":[1,2],"y":"z"}');
  });
});
