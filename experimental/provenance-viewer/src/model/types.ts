// Shapes of the normalised JSON (schema version 1, a sketch, not a contract).
// See render/src/fasthep_render/experimental/provenance/normalise.py.

export type Completeness = "complete" | "partial" | "unavailable" | "not_recorded";
export type Origin = "source" | "sanitized" | "curated" | "inferred" | "synthetic";

export interface RunsFile {
  schema_version: 1;
  runs: { id: string; label: string }[];
}

export interface ArtifactSearchEntry {
  id: string;
  run_id: string;
  name: string;
  path: string;
  kind: string;
  producer_id?: string | null;
  completeness: Completeness;
  completeness_note: string;
  graph_ref?: string;
  details_ref?: string;
  ancestor_count?: number;
}

export interface RunIndex {
  schema_version: 1;
  run: {
    id: string;
    software?: Record<string, string>;
    execution?: Record<string, string>;
    partition_count: number;
    resource_ids: string[];
    graph_node_count: number;
    graph_edge_count: number;
  };
  artifacts: ArtifactSearchEntry[];
}

export interface ProcessingEntity {
  kind: "processing";
  id: string;
  label: string;
  role: "source" | "transform" | "sink" | "observer" | string;
  implementation?: string | null;
  variation?: string | null;
}

export interface DatasetEntity {
  kind: "dataset";
  id: string;
  label: string;
  dataset_type?: string | null;
  event_count?: string | number | null;
  file_count?: number;
  group?: string | null;
  source_node: string;
}

export type GraphEntity = ProcessingEntity | DatasetEntity;

export interface Edge {
  source: string;
  target: string;
  output?: string;
  input_name?: string;
}

export interface Group {
  id: string;
  kind: "variation" | "chain" | "region";
  label: string;
  origin: Origin;
  node_ids: string[];
  entry_edges: { source: string; target: string }[];
  exit_edges: { source: string; target: string }[];
  merge_node?: string;
}

export interface ProvenanceGraph {
  schema_version: 1;
  run_id: string;
  artifact_id: string;
  nodes: GraphEntity[];
  edges: Edge[];
  groups: Group[];
}

export interface Details {
  schema_version: 1;
  artifact_id: string;
  nodes: Record<string, { params?: unknown; outputs?: unknown; meta?: unknown }>;
}

// Derived, visible view: summaries replace collapsed groups.
export interface SummaryEntity {
  kind: "summary";
  id: string;
  groupId: string;
  label: string;
  groupKind: Group["kind"];
  origin: Origin;
  hiddenCount: number;
}

export type VisibleEntity = GraphEntity | SummaryEntity;

export interface VisibleView {
  nodes: VisibleEntity[];
  edges: { source: string; target: string }[];
}
