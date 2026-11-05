import type { ArtifactSearchEntry, Details, GraphEntity, SummaryEntity, VisibleEntity } from "../model/types";

function Json({ value }: { value: unknown }) {
  if (value === undefined) return <div className="notrec">Not recorded</div>;
  return <pre>{JSON.stringify(value, null, 1)}</pre>;
}

export function DetailsPanel(props: {
  artifact?: ArtifactSearchEntry;
  entity?: VisibleEntity;
  details?: Details | "loading" | "failed";
}) {
  const { artifact, entity, details } = props;
  if (!artifact) return <aside className="details" />;
  const info = entity && entity.kind !== "summary" ? (details && typeof details === "object" ? details.nodes[entity.id] : undefined) : undefined;
  return (
    <aside className="details">
      <h2>{entity ? entity.id : artifact.name}</h2>
      {!entity && (
        <>
          <p>
            {artifact.kind} · producer {artifact.producer_id ?? "Not recorded"}
          </p>
          <p>
            Provenance: <span className={`badge ${artifact.completeness}`}>{artifact.completeness}</span>
          </p>
          <p>{artifact.completeness_note}</p>
          <p className="sub">{artifact.path}</p>
        </>
      )}
      {entity?.kind === "summary" && <SummaryInfo e={entity} />}
      {entity && entity.kind !== "summary" && (
        <>
          <GraphInfo e={entity as GraphEntity} />
          {details === "loading" && <p>Loading details…</p>}
          {details === "failed" && <p className="warn">Details failed to load.</p>}
          {entity.kind === "processing" && info && (
            <>
              <h3>Parameters</h3>
              <Json value={info.params} />
              <h3>Outputs</h3>
              <Json value={info.outputs} />
              <h3>Meta</h3>
              <Json value={info.meta} />
            </>
          )}
        </>
      )}
    </aside>
  );
}

function SummaryInfo({ e }: { e: SummaryEntity }) {
  return (
    <p>
      {e.hiddenCount} entities hidden in the {e.groupKind} group “{e.label}”. Origin: {e.origin}
      {e.origin === "inferred" ? " (computed, not recorded by Flow)" : ""}.
    </p>
  );
}

function GraphInfo({ e }: { e: GraphEntity }) {
  return e.kind === "dataset" ? (
    <ul>
      <li>Dataset type: {e.dataset_type ?? "Not recorded"}</li>
      <li>Events: {e.event_count ?? "Not recorded"}</li>
      <li>Files: {e.file_count ?? "Not recorded"}</li>
      <li>Group: {e.group ?? "Not recorded"}</li>
    </ul>
  ) : (
    <ul>
      <li>Role: {e.role}</li>
      <li>Implementation: {e.implementation ?? "Not recorded"}</li>
      {e.variation && <li>Variation: {e.variation}</li>}
    </ul>
  );
}
