import { recorded } from "../model/format";
import type { ArtifactSearchEntry, Details, GraphEntity, ProvenanceGraph, Resource, SummaryEntity, VisibleEntity } from "../model/types";

function Json({ value }: { value: unknown }) {
  if (value === undefined) return <div className="notrec">Not recorded</div>;
  return <pre>{JSON.stringify(value, null, 1)}</pre>;
}

export function DetailsPanel(props: {
  artifact?: ArtifactSearchEntry;
  entity?: VisibleEntity;
  details?: Details | "loading" | "failed";
  graph?: ProvenanceGraph;
  runId?: string;
}) {
  const { artifact, entity, details, graph, runId } = props;
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
          {artifact.preview_ref && runId && (
            <p>
              <a href={`${runId}/${artifact.preview_ref}`} target="_blank" rel="noreferrer">
                Open the existing plot ({artifact.preview_ref.split("/").pop()})
              </a>
              {artifact.preview_note && <span className="sub"> {artifact.preview_note}</span>}
            </p>
          )}
        </>
      )}
      {entity?.kind === "summary" && <SummaryInfo e={entity} graph={graph} />}
      {entity?.kind === "boundary" && (
        <p>Outside the focused group: {entity.label}. Return to the overview to see it in context.</p>
      )}
      {entity && entity.kind !== "summary" && entity.kind !== "boundary" && (
        <>
          <GraphInfo e={entity as GraphEntity} />
          {details === "loading" && <p>Loading details…</p>}
          {details === "failed" && <p className="warn">Details failed to load.</p>}
          {entity.kind === "processing" && (
            <Corrections ids={entity.resource_ids ?? []} resources={graph?.resources ?? {}} />
          )}
          {entity.kind === "processing" && info && (
            <>
              <h3>Declared operations</h3>
              <Json value={info.operations} />
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

function SummaryInfo({ e, graph }: { e: SummaryEntity; graph?: ProvenanceGraph }) {
  const group = graph?.groups.find((g) => g.id === e.groupId);
  const names = group?.node_ids.slice(0, 40) ?? [];
  return (
    <>
      <p>
        {e.hiddenCount} entities hidden in the {e.groupKind} group “{e.label}”. Origin: {e.origin}
        {e.origin === "inferred" ? " (computed, not recorded by Flow)" : ""}.
      </p>
      <h3>Members</h3>
      <ul className="members">
        {names.map((n) => (
          <li key={n}>{n}</li>
        ))}
        {group && group.node_ids.length > names.length && <li>… {group.node_ids.length - names.length} more</li>}
      </ul>
    </>
  );
}

function Corrections({ ids, resources }: { ids: string[]; resources: Record<string, Resource> }) {
  if (ids.length === 0) return null;
  
  return (
    <>
      <h3>Corrections and resources ({ids.length})</h3>
      <ul className="members">
        {ids.map((id) => {
          const r = resources[id];
          return (
            <li key={id}>
              <strong>{id}</strong>
              {!r ? (
                <div className="notrec">Resource record Not recorded</div>
              ) : (
                <div className="sub">
                  {recorded(r.kind)} · era {recorded(r.requested_era)} · {recorded(r.correction)} v{recorded(r.correction_version)}
                  <br />
                  sha256 {r.sha256 ? r.sha256.slice(0, 12) : "Not recorded"} · {recorded(r.path)}
                  {r.fallback === true && (
                    <div className="warn">Fallback recorded{r.fallback_reason ?? r.reason ? `: ${r.fallback_reason ?? r.reason}` : ""}</div>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </>
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
