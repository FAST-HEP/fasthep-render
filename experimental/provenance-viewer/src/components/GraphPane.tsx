import {
  Background,
  Controls,
  type Edge,
  Handle,
  type Node,
  type NodeProps,
  Position,
  ReactFlow,
  ReactFlowProvider,
  type Viewport,
  useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useMemo, useRef } from "react";
import { record } from "../data/metrics";
import { type Placed, layout } from "../layout/dagre";
import { stabilise } from "../layout/stabilise";
import { hiddenLabel } from "../model/format";
import type { Resource, VisibleEntity, VisibleView } from "../model/types";

export interface Actions {
  fromSource: (groupId: string) => void;
  fromArtifact: (groupId: string) => void;
  expand: (groupId: string) => void;
  focus: (groupId: string) => void;
}

type Data = {
  entity: VisibleEntity;
  selected: boolean;
  actions: Actions;
  corrections: number;
  fallback: boolean;
};

const ROLE_MARK: Record<string, string> = { source: "SRC", transform: "OP", sink: "SINK", observer: "OBS" };

function EntityNode({ data }: NodeProps<Node<Data>>) {
  const e = data.entity;
  const cls = ["node", `node-${e.kind}`, e.kind === "processing" ? `role-${e.role}` : "", data.selected ? "selected" : ""];
  const a = data.actions;
  return (
    <div className={cls.join(" ")}>
      <Handle type="target" position={Position.Top} isConnectable={false} />
      {e.kind === "summary" ? (
        <>
          <div className="node-title">{hiddenLabel(e.hiddenCount, e.linear)}</div>
          <div className="node-sub">
            {e.groupKind}: {e.label} ({e.origin})
          </div>
          <div className="actions">
            {e.linear && (
              <button type="button" aria-label={`Reveal one step from the dataset side of ${e.label}`} onClick={(ev) => { ev.stopPropagation(); a.fromSource(e.groupId); }}>
                Reveal from top
              </button>
            )}
            <button type="button" aria-label={`Show all ${e.hiddenCount} hidden in ${e.label}`} onClick={(ev) => { ev.stopPropagation(); a.expand(e.groupId); }}>
              Show all
            </button>
            {e.linear && (
              <button type="button" aria-label={`Reveal one step from the artifact side of ${e.label}`} onClick={(ev) => { ev.stopPropagation(); a.fromArtifact(e.groupId); }}>
                Reveal from bottom
              </button>
            )}
            {!e.linear && (
              <button type="button" aria-label={`Focus on ${e.label}`} onClick={(ev) => { ev.stopPropagation(); a.focus(e.groupId); }}>
                Focus
              </button>
            )}
          </div>
        </>
      ) : e.kind === "boundary" ? (
        <div className="node-sub">{e.direction === "in" ? "from" : "to"} {e.label} (outside this group)</div>
      ) : e.kind === "dataset" ? (
        <>
          <div className="node-title">DATA {e.label}</div>
          <div className="node-sub">
            {e.dataset_type ?? "Not recorded"} · {e.event_count ?? "Not recorded"} events
          </div>
        </>
      ) : (
        <>
          <div className="node-title">
            <span className="mark">{ROLE_MARK[e.role] ?? e.role}</span> {e.label}
          </div>
          <div className="node-sub">{e.implementation ?? "Not recorded"}</div>
          {(data.corrections > 0 || data.fallback) && (
            <div className="badges">
              {data.corrections > 0 && <span className="badge">{data.corrections} correction{data.corrections > 1 ? "s" : ""}</span>}
              {data.fallback && <span className="badge warnbadge">fallback recorded</span>}
            </div>
          )}
        </>
      )}
      <Handle type="source" position={Position.Bottom} isConnectable={false} />
    </div>
  );
}

const nodeTypes = { entity: EntityNode };

function Inner(props: {
  view: VisibleView;
  resources: Record<string, Resource>;
  selectedId?: string;
  initialViewport?: Viewport;
  actions: Actions;
  onSelect: (id: string) => void;
  onViewport: (v: Viewport) => void;
}) {
  const { view, resources, selectedId, initialViewport, actions, onSelect, onViewport } = props;
  const flow = useReactFlow();
  const prev = useRef<Map<string, Placed>>();
  const { placed: raw, ms: layoutMs } = useMemo(() => layout(view), [view]);
  const placed = useMemo(() => stabilise(prev.current, raw), [raw]);

  useEffect(() => {
    prev.current = new Map(placed.map((p) => [p.id, p]));
  }, [placed]);

  const nodes: Node<Data>[] = useMemo(
    () =>
      view.nodes.map((entity, i) => {
        const ids = entity.kind === "processing" ? (entity.resource_ids ?? []) : [];
        return {
          id: entity.id,
          type: "entity",
          position: { x: placed[i].x, y: placed[i].y },
          width: placed[i].width,
          height: placed[i].height,
          data: {
            entity,
            selected: entity.id === selectedId,
            actions,
            corrections: ids.length,
            fallback: ids.some((r) => resources[r]?.fallback === true),
          },
        };
      }),
    [view, placed, selectedId, actions, resources],
  );
  const edges: Edge[] = useMemo(
    () => view.edges.map((e) => ({ id: `${e.source}>${e.target}`, source: e.source, target: e.target })),
    [view],
  );

  // Metrics are recorded in an effect, never during render.
  useEffect(() => {
    record("layout", layoutMs, "ms");
    record("layout:nodes", view.nodes.length, "count");
    record("layout:edges", view.edges.length, "count");
  }, [layoutMs, view]);
  useEffect(() => {
    const t0 = performance.now();
    requestAnimationFrame(() => record("render:first-frame", performance.now() - t0, "ms"));
  }, []);

  // Fit once when this pane opens; a restored viewport replaces the fit. Expansion never refits.
  useEffect(() => {
    if (!initialViewport) flow.fitView({ padding: 0.1 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flow]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      defaultViewport={initialViewport}
      onMoveEnd={(_, v) => onViewport(v)}
      onNodeClick={(_, n) => onSelect(n.id)}
      nodesDraggable={false}
      nodesConnectable={false}
      minZoom={0.05}
      onlyRenderVisibleElements
      proOptions={{ hideAttribution: true }}
    >
      <Background />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}

export function GraphPane(props: {
  paneKey: string;
  view: VisibleView;
  resources: Record<string, Resource>;
  selectedId?: string;
  initialViewport?: Viewport;
  actions: Actions;
  onSelect: (id: string) => void;
  onViewport: (v: Viewport) => void;
}) {
  // Remount per artifact and per focus so the viewport fits once and stays put on expansion.
  return (
    <ReactFlowProvider key={props.paneKey}>
      <Inner {...props} />
    </ReactFlowProvider>
  );
}
