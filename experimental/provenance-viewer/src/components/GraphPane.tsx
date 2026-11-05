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
  useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useMemo } from "react";
import { record } from "../data/metrics";
import { layout } from "../layout/dagre";
import type { VisibleEntity, VisibleView } from "../model/types";

type Data = { entity: VisibleEntity; selected: boolean; onExpand: (groupId: string) => void };

const ROLE_MARK: Record<string, string> = { source: "SRC", transform: "OP", sink: "SINK", observer: "OBS" };

function EntityNode({ data }: NodeProps<Node<Data>>) {
  const e = data.entity;
  const cls = ["node", `node-${e.kind}`, e.kind === "processing" ? `role-${e.role}` : "", data.selected ? "selected" : ""];
  return (
    <div className={cls.join(" ")}>
      <Handle type="target" position={Position.Top} isConnectable={false} />
      {e.kind === "summary" ? (
        <>
          <div className="node-title">{e.hiddenCount} steps hidden</div>
          <div className="node-sub">
            {e.groupKind}: {e.label} ({e.origin})
          </div>
          <button type="button" className="expand" onClick={() => data.onExpand(e.groupId)}>
            Expand {e.hiddenCount}
          </button>
        </>
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
        </>
      )}
      <Handle type="source" position={Position.Bottom} isConnectable={false} />
    </div>
  );
}

const nodeTypes = { entity: EntityNode };

function Inner(props: {
  view: VisibleView;
  selectedId?: string;
  onSelect: (id: string) => void;
  onExpand: (groupId: string) => void;
}) {
  const { view, selectedId, onSelect, onExpand } = props;
  const flow = useReactFlow();
  const { placed, ms: layoutMs } = useMemo(() => layout(view), [view]);

  const nodes: Node<Data>[] = useMemo(
    () =>
      view.nodes.map((entity, i) => ({
        id: entity.id,
        type: "entity",
        position: { x: placed[i].x, y: placed[i].y },
        width: placed[i].width,
        height: placed[i].height,
        data: { entity, selected: entity.id === selectedId, onExpand },
      })),
    [view, placed, selectedId, onExpand],
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

  // Fit once per artifact (view identity changes on expansion; do not refit then).
  useEffect(() => {
    const t0 = performance.now();
    requestAnimationFrame(() => {
      record("render:first-frame", performance.now() - t0, "ms");
    });
  }, []);
  useEffect(() => {
    flow.fitView({ padding: 0.1 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flow]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
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
  artifactKey: string;
  view: VisibleView;
  selectedId?: string;
  onSelect: (id: string) => void;
  onExpand: (groupId: string) => void;
}) {
  // Remount per artifact so the viewport fits once and then stays put on expansion.
  return (
    <ReactFlowProvider key={props.artifactKey}>
      <Inner {...props} />
    </ReactFlowProvider>
  );
}
