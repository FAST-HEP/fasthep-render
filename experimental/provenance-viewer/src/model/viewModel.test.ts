import { describe, expect, it } from "vitest";
import type { ProvenanceGraph, RunIndex } from "./types";
import { coarseView, defaultCollapsed, formatRoute, parseRoute, searchArtifacts } from "./viewModel";

const proc = (id: string) => ({ kind: "processing" as const, id, label: id, role: "transform" });

const graph: ProvenanceGraph = {
  schema_version: 1,
  run_id: "r",
  artifact_id: "a",
  nodes: ["r0", "a1", "a2", "b1", "z"].map(proc),
  edges: [
    { source: "r0", target: "a1" },
    { source: "a1", target: "a2" },
    { source: "r0", target: "b1" },
    { source: "a2", target: "z" },
    { source: "b1", target: "z" },
  ],
  groups: [
    { id: "variation:A", kind: "variation", label: "A", origin: "source", node_ids: ["a1", "a2"], entry_edges: [], exit_edges: [] },
    { id: "variation:B", kind: "variation", label: "B", origin: "source", node_ids: ["b1", "a2"], entry_edges: [], exit_edges: [] },
  ],
};

describe("coarseView", () => {
  it("is the full graph when nothing is collapsed", () => {
    const v = coarseView(graph, new Map());
    expect(v.nodes).toHaveLength(5);
    expect(v.edges).toHaveLength(5);
  });

  it("replaces a collapsed group by one summary and drops self loops", () => {
    const v = coarseView(graph, new Map([["variation:A", { lo: 0, hi: 2 }]]));
    const summary = v.nodes.find((n) => n.kind === "summary");
    expect(summary).toMatchObject({ id: "summary:variation:A", hiddenCount: 2 });
    expect(v.nodes.map((n) => n.id)).not.toContain("a1");
    expect(v.edges).toContainEqual({ source: "r0", target: "summary:variation:A" });
    expect(v.edges).toContainEqual({ source: "summary:variation:A", target: "z" });
    expect(v.edges.every((e) => e.source !== e.target)).toBe(true);
  });

  it("gives an entity in two collapsed groups to the first only", () => {
    const v = coarseView(graph, new Map([["variation:A", { lo: 0, hi: 2 }], ["variation:B", { lo: 0, hi: 2 }]]));
    const sums = v.nodes.filter((n) => n.kind === "summary");
    expect(sums.map((s) => s.kind === "summary" && s.hiddenCount)).toEqual([2, 1]);
  });

  it("never shows an edge between ids that are not visible", () => {
    const v = coarseView(graph, new Map([["variation:A", { lo: 0, hi: 2 }], ["variation:B", { lo: 0, hi: 2 }]]));
    const ids = new Set(v.nodes.map((n) => n.id));
    expect(v.edges.every((e) => ids.has(e.source) && ids.has(e.target))).toBe(true);
  });
});

describe("defaultCollapsed", () => {
  it("collapses recorded variations only for large graphs", () => {
    expect(defaultCollapsed(graph).size).toBe(0);
    expect([...defaultCollapsed(graph, 3).keys()]).toEqual(["variation:A", "variation:B"]);
  });
});

describe("searchArtifacts", () => {
  const index = {
    artifacts: [
      { id: "1", name: "DiMuonMass", path: "p/DiMuonMass.pkl", kind: "histogram", producer_id: "stage.DiMuonMass" },
      { id: "2", name: "DiMuonMass", path: "plots/DiMuonMass.png", kind: "plot", producer_id: "render.DiMuonMass.0" },
    ],
  } as unknown as RunIndex;

  it("matches every token across name, kind and producer", () => {
    expect(searchArtifacts(index, "dimuon").map((a) => a.id)).toEqual(["1", "2"]);
    expect(searchArtifacts(index, "dimuon plot").map((a) => a.id)).toEqual(["2"]);
    expect(searchArtifacts(index, "render").map((a) => a.id)).toEqual(["2"]);
    expect(searchArtifacts(index, "nothing")).toEqual([]);
  });
});

describe("route", () => {
  it("round trips and ignores an artifact without a run", () => {
    expect(parseRoute("#/zmumu/histogram-1")).toEqual({ runId: "zmumu", artifactId: "histogram-1" });
    expect(parseRoute("")).toEqual({});
    expect(formatRoute({ runId: "zmumu", artifactId: "x" })).toBe("#/zmumu/x");
    expect(formatRoute({ artifactId: "x" })).toBe("#/");
  });
});

import { expandGroup, focusView, revealFromArtifact, revealFromSource } from "./viewModel";

describe("linear reveal and focus", () => {
  const chainGraph: ProvenanceGraph = {
    schema_version: 1,
    run_id: "r",
    artifact_id: "a",
    nodes: ["s", "c1", "c2", "c3", "c4", "t", "side"].map(proc),
    edges: [
      { source: "s", target: "c1" },
      { source: "c1", target: "c2" },
      { source: "c2", target: "c3" },
      { source: "c3", target: "c4" },
      { source: "c4", target: "t" },
      { source: "c2", target: "side" },
    ],
    groups: [
      { id: "chain:c1", kind: "chain", label: "chain", origin: "inferred", node_ids: ["c1", "c2", "c3", "c4"], entry_edges: [], exit_edges: [] },
    ],
  };

  it("hides the interior of a long run by default", () => {
    const c = defaultCollapsed(chainGraph);
    expect(c.get("chain:c1")).toEqual({ lo: 1, hi: 3 });
    const v = coarseView(chainGraph, c);
    expect(v.nodes.map((n) => n.id)).toEqual(["s", "c1", "c4", "t", "side", "summary:chain:c1"]);
  });

  it("reveals one step from either end, then the whole run", () => {
    let c = defaultCollapsed(chainGraph);
    c = revealFromSource(c, "chain:c1");
    expect(coarseView(chainGraph, c).nodes.map((n) => n.id)).toContain("c2");
    expect(coarseView(chainGraph, c).nodes.map((n) => n.id)).not.toContain("c3");
    c = revealFromArtifact(c, "chain:c1");
    expect(c.has("chain:c1")).toBe(false);
    expect(coarseView(chainGraph, c).nodes).toHaveLength(7);
  });

  it("expandGroup is a no-op for a group that is not collapsed", () => {
    const c = defaultCollapsed(chainGraph);
    expect(expandGroup(c, "nope")).toBe(c);
  });

  it("focus keeps members and shows outside neighbours as boundary stand-ins", () => {
    const v = focusView(chainGraph, "chain:c1");
    expect(v?.nodes.filter((n) => n.kind === "boundary").map((n) => n.id).sort()).toEqual([
      "outside:in:s",
      "outside:out:side",
      "outside:out:t",
    ]);
    expect(v?.nodes.filter((n) => n.kind !== "boundary")).toHaveLength(4);
    expect(focusView(chainGraph, "missing")).toBeUndefined();
  });
});
