// Textual lineage: the same visible view as the graph, as plain structure. It is the
// non-canvas fallback and the seam a terminal UI would reuse. Pure; no React, no layout.

import { hiddenLabel, recorded } from "./format";
import type { ArtifactSearchEntry, VisibleEntity, VisibleView } from "./types";

export interface TextAction {
  kind: "from_source" | "from_artifact" | "expand" | "focus";
  groupId: string;
  label: string;
}

export interface TextItem {
  /** 1-based position in the reading order; `from` and `to` refer to these. */
  n: number;
  id: string;
  tag: "dataset" | "source" | "step" | "sink" | "observer" | "summary" | "outside";
  title: string;
  detail: string;
  from: number[];
  to: number[];
  /** "branch" when several items follow, "merge" when several precede. */
  flow: ("branch" | "merge")[];
  corrections: string[];
  actions: TextAction[];
  selectable: boolean;
}

export interface TextLayer {
  index: number;
  parallel: number;
  items: TextItem[];
}

export interface TextLineage {
  header: string[];
  layers: TextLayer[];
}

function describe(e: VisibleEntity): Pick<TextItem, "tag" | "title" | "detail" | "actions" | "selectable"> {
  if (e.kind === "dataset") {
    return {
      tag: "dataset",
      title: e.label,
      detail: `${recorded(e.dataset_type)}, ${recorded(e.event_count)} events, ${recorded(e.file_count)} files`,
      actions: [],
      selectable: true,
    };
  }
  if (e.kind === "boundary") {
    return {
      tag: "outside",
      title: e.label,
      detail: `${e.direction === "in" ? "enters from" : "leaves to"} outside the focused group`,
      actions: [],
      selectable: true,
    };
  }
  if (e.kind === "summary") {
    const actions: TextAction[] = e.linear
      ? [
          { kind: "from_source", groupId: e.groupId, label: "Reveal one step from the dataset side" },
          { kind: "expand", groupId: e.groupId, label: `Show all ${e.hiddenCount}` },
          { kind: "from_artifact", groupId: e.groupId, label: "Reveal one step from the artifact side" },
        ]
      : [
          { kind: "expand", groupId: e.groupId, label: `Show all ${e.hiddenCount}` },
          { kind: "focus", groupId: e.groupId, label: `Focus on ${e.label}` },
        ];
    return {
      tag: "summary",
      title: hiddenLabel(e.hiddenCount, e.linear),
      detail: `${e.groupKind} "${e.label}", origin ${e.origin}${e.origin === "inferred" ? " (computed, not recorded by Flow)" : ""}`,
      actions,
      selectable: true,
    };
  }
  const tag = e.role === "source" ? "source" : e.role === "sink" ? "sink" : e.role === "observer" ? "observer" : "step";
  return {
    tag,
    title: e.label,
    detail: `implementation ${recorded(e.implementation)}${e.variation ? `, variation ${e.variation}` : ""}`,
    actions: [],
    selectable: true,
  };
}

/** Longest-path layer of every visible entity; entities in one layer run in parallel. */
function layersOf(view: VisibleView): Map<string, number> {
  const preds = new Map<string, string[]>();
  const succs = new Map<string, string[]>();
  for (const n of view.nodes) {
    preds.set(n.id, []);
    succs.set(n.id, []);
  }
  for (const e of view.edges) {
    preds.get(e.target)?.push(e.source);
    succs.get(e.source)?.push(e.target);
  }
  const indeg = new Map([...preds].map(([id, p]) => [id, p.length]));
  const ready = view.nodes.map((n) => n.id).filter((id) => indeg.get(id) === 0).sort();
  const layer = new Map<string, number>(ready.map((id) => [id, 0]));
  while (ready.length) {
    const id = ready.shift() as string;
    for (const s of (succs.get(id) ?? []).slice().sort()) {
      layer.set(s, Math.max(layer.get(s) ?? 0, (layer.get(id) ?? 0) + 1));
      indeg.set(s, (indeg.get(s) ?? 1) - 1);
      if (indeg.get(s) === 0) ready.push(s);
    }
  }
  return layer;
}

export function toTextLineage(
  view: VisibleView,
  artifact: Pick<ArtifactSearchEntry, "name" | "kind" | "completeness" | "completeness_note">,
  corrections: (entity: VisibleEntity) => string[] = () => [],
): TextLineage {
  const layer = layersOf(view);
  const ordered = view.nodes
    .slice()
    .sort((a, b) => (layer.get(a.id) ?? 0) - (layer.get(b.id) ?? 0) || a.id.localeCompare(b.id));
  const number = new Map(ordered.map((e, i) => [e.id, i + 1]));
  const from = new Map<string, number[]>();
  const to = new Map<string, number[]>();
  for (const e of view.edges) {
    const s = number.get(e.source);
    const t = number.get(e.target);
    if (s === undefined || t === undefined) continue;
    from.set(e.target, [...(from.get(e.target) ?? []), s]);
    to.set(e.source, [...(to.get(e.source) ?? []), t]);
  }
  const items: TextItem[] = ordered.map((e) => {
    const f = (from.get(e.id) ?? []).sort((a, b) => a - b);
    const t = (to.get(e.id) ?? []).sort((a, b) => a - b);
    return {
      n: number.get(e.id) as number,
      id: e.id,
      ...describe(e),
      from: f,
      to: t,
      flow: [...(t.length > 1 ? (["branch"] as const) : []), ...(f.length > 1 ? (["merge"] as const) : [])],
      corrections: corrections(e),
    };
  });
  const byLayer = new Map<number, TextItem[]>();
  for (const it of items) {
    const l = layer.get(it.id) ?? 0;
    byLayer.set(l, [...(byLayer.get(l) ?? []), it]);
  }
  const layers = [...byLayer.keys()]
    .sort((a, b) => a - b)
    .map((index) => ({ index: index + 1, parallel: (byLayer.get(index) ?? []).length, items: byLayer.get(index) ?? [] }));
  return {
    header: [
      `Lineage of ${artifact.name} (${artifact.kind})`,
      `Provenance: ${artifact.completeness}. ${artifact.completeness_note}`,
      `${items.length} entities shown, read from datasets (first) to the artifact (last).`,
    ],
    layers,
  };
}

/** Plain-text rendering, one line per entity; what a terminal UI could print. */
export function renderText(t: TextLineage): string[] {
  const lines = [...t.header];
  for (const l of t.layers) {
    lines.push(`Layer ${l.index}${l.parallel > 1 ? ` (${l.parallel} in parallel)` : ""}`);
    for (const i of l.items) {
      const refs = [
        i.from.length ? `from ${i.from.join(", ")}` : "",
        i.to.length ? `to ${i.to.join(", ")}` : "",
        ...i.flow,
      ].filter(Boolean);
      const corr = i.corrections.length ? `; corrections: ${i.corrections.join(", ")}` : "";
      const acts = i.actions.length ? `; actions: ${i.actions.map((a) => a.label).join(" | ")}` : "";
      lines.push(`  ${i.n}. [${i.tag}] ${i.title}: ${i.detail}${corr}${refs.length ? ` (${refs.join("; ")})` : ""}${acts}`);
    }
  }
  return lines;
}
