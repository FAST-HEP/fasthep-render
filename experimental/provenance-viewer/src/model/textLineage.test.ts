import { describe, expect, it } from "vitest";
import { recorded } from "./format";
import { renderText, toTextLineage } from "./textLineage";
import type { ProvenanceGraph, VisibleView } from "./types";
import { coarseView, defaultCollapsed, focusSubgraph, revealFromSource, visibleSelection } from "./viewModel";

const artifact = { name: "H", kind: "histogram", completeness: "partial" as const, completeness_note: "no record" };
const proc = (id: string, impl: string | null = "impl") => ({
  kind: "processing" as const, id, label: id, role: "transform", implementation: impl,
});

// ds -> src -> a -> (b1 | b2) -> merge -> out
const graph: ProvenanceGraph = {
  schema_version: 1,
  run_id: "r",
  artifact_id: "a",
  nodes: [
    { kind: "dataset", id: "ds", label: "ds", dataset_type: "mc", event_count: "5", file_count: 1, source_node: "src" },
    { ...proc("src", "root_tree"), role: "source" },
    proc("a"),
    proc("b1"),
    proc("b2", null),
    proc("merge"),
    { ...proc("out"), role: "sink" },
  ],
  edges: [
    { source: "ds", target: "src" }, { source: "src", target: "a" },
    { source: "a", target: "b1" }, { source: "a", target: "b2" },
    { source: "b1", target: "merge" }, { source: "b2", target: "merge" },
    { source: "merge", target: "out" },
  ],
  groups: [],
};

describe("recorded", () => {
  it("keeps missing and empty apart", () => {
    expect(recorded(undefined)).toBe("Not recorded");
    expect(recorded(null)).toBe("Not recorded");
    expect(recorded("")).toBe("(empty)");
    expect(recorded([])).toBe("(empty)");
    expect(recorded(0)).toBe("0");
    expect(recorded(false)).toBe("false");
  });
});

describe("toTextLineage", () => {
  const view = coarseView(graph, new Map());
  const text = toTextLineage(view, artifact, (e) => (e.id === "a" ? ["res.one"] : []));

  it("lists exactly the visible entities, datasets first and the artifact last", () => {
    const ids = text.layers.flatMap((l) => l.items.map((i) => i.id));
    expect(new Set(ids)).toEqual(new Set(view.nodes.map((n) => n.id)));
    expect(ids[0]).toBe("ds");
    expect(ids.at(-1)).toBe("out");
  });

  it("marks parallel branches, branch and merge points, and references by number", () => {
    const layer = text.layers.find((l) => l.parallel === 2);
    expect(layer?.items.map((i) => i.id)).toEqual(["b1", "b2"]);
    const items = new Map(text.layers.flatMap((l) => l.items).map((i) => [i.id, i]));
    expect(items.get("a")?.flow).toEqual(["branch"]);
    expect(items.get("merge")?.flow).toEqual(["merge"]);
    const b1 = items.get("b1");
    expect(b1?.from).toEqual([items.get("a")?.n]);
    expect(b1?.to).toEqual([items.get("merge")?.n]);
  });

  it("keeps Not recorded, corrections and the completeness header", () => {
    const lines = renderText(text).join("\n");
    expect(lines).toContain("implementation Not recorded");
    expect(lines).toContain("corrections: res.one");
    expect(lines).toContain("Provenance: partial. no record");
    expect(lines).toContain("(2 in parallel)");
  });

  it("is deterministic", () => {
    expect(renderText(toTextLineage(view, artifact))).toEqual(renderText(toTextLineage(view, artifact)));
  });
});

describe("text view of collapsed and focused views", () => {
  const ids = ["s", "c1", "c2", "c3", "c4", "t"];
  const chain: ProvenanceGraph = {
    schema_version: 1, run_id: "r", artifact_id: "a",
    nodes: ids.map((id) => proc(id)),
    edges: ids.slice(1).map((id, i) => ({ source: ids[i], target: id })),
    groups: [{ id: "chain:c1", kind: "chain", label: "chain", origin: "inferred", node_ids: ["c1", "c2", "c3", "c4"], entry_edges: [], exit_edges: [] }],
  };

  it("offers the reveal actions for a linear summary and keeps the order", () => {
    const view = coarseView(chain, defaultCollapsed(chain));
    const items = toTextLineage(view, artifact).layers.flatMap((l) => l.items);
    const summary = items.find((i) => i.tag === "summary");
    expect(summary?.title).toBe("2 steps hidden");
    expect(summary?.actions.map((a) => a.kind)).toEqual(["from_source", "expand", "from_artifact"]);
    expect(summary?.detail).toContain("computed, not recorded by Flow");
    expect(items.map((i) => i.id)).toEqual(["s", "c1", "summary:chain:c1", "c4", "t"]);
  });

  it("revealing a step changes the text the same way it changes the graph", () => {
    const c = revealFromSource(defaultCollapsed(chain), "chain:c1");
    const view = coarseView(chain, c);
    const items = toTextLineage(view, artifact).layers.flatMap((l) => l.items);
    expect(items.map((i) => i.id)).toEqual(["s", "c1", "c2", "summary:chain:c1", "c4", "t"]);
    expect(items.find((i) => i.tag === "summary")?.title).toBe("1 step hidden");
  });

  it("describes boundary stand-ins in a focused view", () => {
    const sub = focusSubgraph(chain, "chain:c1") as ProvenanceGraph;
    const items = toTextLineage(coarseView(sub, new Map()), artifact).layers.flatMap((l) => l.items);
    expect(items.filter((i) => i.tag === "outside").map((i) => i.detail)).toEqual([
      "enters from outside the focused group",
      "leaves to outside the focused group",
    ]);
  });

  it("an entity stays selected while hidden and reappears when revealed", () => {
    const hidden = coarseView(chain, defaultCollapsed(chain));
    expect(visibleSelection(hidden, "c2")).toBeUndefined();
    const revealed = coarseView(chain, new Map());
    expect(visibleSelection(revealed, "c2")?.id).toBe("c2");
    expect(visibleSelection(revealed, undefined)).toBeUndefined();
  });
});

// type check: a view is just nodes and edges
const _v: VisibleView = { nodes: [], edges: [] };
void _v;
