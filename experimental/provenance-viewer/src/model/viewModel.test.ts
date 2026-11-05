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

import { expandGroup, focusSubgraph, revealFromArtifact, revealFromSource, visibleIdFor } from "./viewModel";

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
    const sub = focusSubgraph(chainGraph, "chain:c1");
    expect(sub?.nodes.filter((n) => n.kind === "boundary").map((n) => n.id).sort()).toEqual([
      "outside:in:s",
      "outside:out:side",
      "outside:out:t",
    ]);
    expect(sub?.nodes.filter((n) => n.kind !== "boundary")).toHaveLength(4);
    expect(focusSubgraph(chainGraph, "missing")).toBeUndefined();
  });
});

describe("visibleIdFor", () => {
  it("finds an entity, or the summary it is hidden in, or nothing", () => {
    const ids = ["s", "c1", "c2", "c3", "c4", "t"];
    const g: ProvenanceGraph = {
      schema_version: 1, run_id: "r", artifact_id: "a",
      nodes: ids.map(proc),
      edges: ids.slice(1).map((id, i) => ({ source: ids[i], target: id })),
      groups: [{ id: "chain:c1", kind: "chain", label: "chain", origin: "inferred", node_ids: ["c1", "c2", "c3", "c4"], entry_edges: [], exit_edges: [] }],
    };
    const view = coarseView(g, defaultCollapsed(g));
    expect(visibleIdFor(view, g, "s")).toBe("s");
    expect(visibleIdFor(view, g, "c2")).toBe("summary:chain:c1");
    expect(visibleIdFor(view, g, "c1")).toBe("c1");
    expect(visibleIdFor(view, g, "elsewhere")).toBeUndefined();
  });
});

describe("hierarchical focus", () => {
  const ids = ["r", "a1", "a2", "a3", "a4", "b1", "b2", "b3", "b4", "z"];
  const g: ProvenanceGraph = {
    schema_version: 1,
    run_id: "r",
    artifact_id: "x",
    nodes: ids.map(proc),
    edges: [
      ...["a", "b"].flatMap((v) => [
        { source: "r", target: `${v}1` },
        { source: `${v}1`, target: `${v}2` },
        { source: `${v}2`, target: `${v}3` },
        { source: `${v}3`, target: `${v}4` },
        { source: `${v}4`, target: "z" },
      ]),
    ],
    groups: [
      { id: "family:v", kind: "variation_family", label: "2 variations", origin: "inferred", node_ids: ["a1", "a2", "a3", "a4", "b1", "b2", "b3", "b4"], entry_edges: [], exit_edges: [], child_groups: ["variation:a", "variation:b"] },
      { id: "variation:a", kind: "variation", label: "a", origin: "source", node_ids: ["a1", "a2", "a3", "a4"], entry_edges: [], exit_edges: [] },
      { id: "variation:b", kind: "variation", label: "b", origin: "source", node_ids: ["b1", "b2", "b3", "b4"], entry_edges: [], exit_edges: [] },
      { id: "chain:a1", kind: "chain", label: "chain a", origin: "inferred", node_ids: ["a1", "a2", "a3", "a4"], entry_edges: [], exit_edges: [] },
    ],
  };

  it("collapses the whole family in the overview", () => {
    const v = coarseView(g, defaultCollapsed(g, 5));
    expect(v.nodes.map((n) => n.id)).toEqual(["r", "z", "summary:family:v"]);
    expect(v.edges).toContainEqual({ source: "r", target: "summary:family:v" });
    expect(v.edges).toContainEqual({ source: "summary:family:v", target: "z" });
  });

  it("focus on the family shows its variations as summaries, then one variation in full", () => {
    const fam = focusSubgraph(g, "family:v");
    expect(fam?.groups.map((x) => x.id)).toEqual(["variation:a", "variation:b", "chain:a1"]);
    const famView = coarseView(fam as ProvenanceGraph, defaultCollapsed(fam as ProvenanceGraph, 5));
    expect(famView.nodes.filter((n) => n.kind === "summary")).toHaveLength(2);
    const one = focusSubgraph(fam as ProvenanceGraph, "variation:a");
    expect(one?.nodes.filter((n) => n.kind === "boundary").map((n) => n.id).sort()).toEqual([
      "outside:in:r",
      "outside:out:z",
    ]);
    const oneView = coarseView(one as ProvenanceGraph, defaultCollapsed(one as ProvenanceGraph));
    expect(oneView.nodes.filter((n) => n.kind === "summary")).toHaveLength(1);
  });
});
