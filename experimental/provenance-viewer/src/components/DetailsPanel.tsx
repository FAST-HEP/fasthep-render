import { Copy, ExternalLink, FileText, TriangleAlert } from "lucide-react";
import { type ReactNode, useState } from "react";
import { artifactIcon, completenessIcon, entityIcon, entityTypeLabel } from "../icons";
import { recorded } from "../model/format";
import type {
  ArtifactSearchEntry,
  Details,
  GraphEntity,
  ProvenanceGraph,
  Resource,
  SummaryEntity,
  VisibleEntity,
} from "../model/types";
import { ValueTree } from "./ValueTree";

function Section(props: { title: string; count?: number; children: ReactNode; open?: boolean }) {
  return (
    <details className="sect" open={props.open ?? true}>
      <summary>
        {props.title}
        {props.count !== undefined ? ` (${props.count})` : ""}
      </summary>
      {props.children}
    </details>
  );
}

function copyText(text: string) {
  try {
    void navigator.clipboard.writeText(text);
  } catch {
    // Clipboard unavailable (insecure context, denied): nothing to do.
  }
}

export function DetailsPanel(props: {
  artifact?: ArtifactSearchEntry;
  entity?: VisibleEntity;
  details?: Details | "loading" | "failed";
  graph?: ProvenanceGraph;
  runId?: string;
}) {
  const { artifact, entity, details, graph, runId } = props;
  const [asText, setAsText] = useState(false);
  if (!artifact) return <aside className="details" />;

  const info =
    entity && entity.kind === "processing" && details && typeof details === "object" ? details.nodes[entity.id] : undefined;
  const inputs = entity && graph ? graph.edges.filter((e) => e.target === entity.id).map((e) => e.source) : [];
  const labelOf = (id: string) => {
    const n = graph?.nodes.find((x) => x.id === id);
    return n && n.kind !== "boundary" ? n.label : id;
  };
  const Icon = entity ? entityIcon(entity) : artifactIcon(artifact.kind);
  const title = entity ? (entity.kind === "summary" ? entity.label : entity.id) : artifact.name;
  const typeLabel = entity ? entityTypeLabel(entity) : `Artifact · ${artifact.kind}`;
  // What "view as text" shows and "copy" copies: the full record behind the panel.
  const record = entity
    ? { entity, inputs, ...(info ? { resolved: info.resolved, operations: info.operations, params: info.params, outputs: info.outputs, meta: info.meta } : {}) }
    : artifact;
  const rawText = JSON.stringify(record, null, 2);

  return (
    <aside className="details">
      <header className="dhead">
        <h2>{entity ? "Selected node" : "Selected artifact"}</h2>
        <div className="dtools">
          <button type="button" aria-label="View as text" aria-pressed={asText} title="View as text" onClick={() => setAsText(!asText)}>
            <FileText size={18} aria-hidden="true" />
          </button>
          <button type="button" aria-label="Copy as text" title="Copy as text" onClick={() => copyText(rawText)}>
            <Copy size={18} aria-hidden="true" />
          </button>
        </div>
      </header>
      <div className="identity">
        <Icon size={34} aria-hidden="true" />
        <div>
          <strong title={title}>{title}</strong>
          <div className="sub">{typeLabel}</div>
        </div>
      </div>

      {asText ? (
        <pre className="rawtext">{rawText}</pre>
      ) : !entity ? (
        <ArtifactInfo artifact={artifact} runId={runId} />
      ) : entity.kind === "summary" ? (
        <SummaryInfo e={entity} graph={graph} />
      ) : entity.kind === "boundary" ? (
        <p>Outside the focused group: {entity.label}. Return to the overview to see it in context.</p>
      ) : (
        <>
          <GraphInfo e={entity} />
          {inputs.length > 0 && (
            <Section title="Inputs" count={inputs.length}>
              <ul className="plain">
                {inputs.map((id) => (
                  <li key={id} title={id}>
                    {labelOf(id)}
                  </li>
                ))}
              </ul>
            </Section>
          )}
          {entity.kind === "processing" && (entity.resource_ids ?? []).length > 0 && (
            <Section title="Corrections and resources" count={(entity.resource_ids ?? []).length}>
              <Corrections ids={entity.resource_ids ?? []} resources={graph?.resources ?? {}} />
            </Section>
          )}
          {details === "loading" && <p>Loading details…</p>}
          {details === "failed" && <p className="warn">Details failed to load.</p>}
          {entity.kind === "processing" && info && (
            <>
              <Section title="Resolved by the compile plan">
                <ValueTree value={info.resolved} />
              </Section>
              <Section title="Operations recorded at run time">
                <ValueTree value={info.operations} />
              </Section>
              <Section title="Parameters">
                <ValueTree value={info.params} />
              </Section>
              <Section title="Outputs">
                <ValueTree value={info.outputs} />
              </Section>
              <Section title="Meta" open={false}>
                <ValueTree value={info.meta} />
              </Section>
            </>
          )}
        </>
      )}
    </aside>
  );
}

function ArtifactInfo({ artifact, runId }: { artifact: ArtifactSearchEntry; runId?: string }) {
  const CIcon = completenessIcon(artifact.completeness);
  const href = artifact.preview_ref && runId ? `${runId}/${artifact.preview_ref}` : undefined;
  return (
    <>
      <p>
        Producer: {recorded(artifact.producer_id)}
        <br />
        Provenance:{" "}
        <span className={`badge ${artifact.completeness}`}>
          <CIcon size={12} aria-hidden="true" /> {artifact.completeness}
        </span>
      </p>
      <p>{artifact.completeness_note}</p>
      <p className="sub" title={artifact.path}>
        {artifact.path}
      </p>
      {href && (
        <figure className="preview">
          <a href={href} target="_blank" rel="noreferrer" title="Open the existing plot">
            <img src={href} alt={`Plot of ${artifact.name}`} loading="lazy" />
          </a>
          <figcaption>
            <a href={href} target="_blank" rel="noreferrer" title={artifact.preview_path}>
              {artifact.preview_path ?? artifact.preview_ref} <ExternalLink size={12} aria-hidden="true" />
            </a>
            {artifact.preview_note && <div className="sub">{artifact.preview_note}</div>}
          </figcaption>
        </figure>
      )}
    </>
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
      <Section title="Members" count={group?.node_ids.length}>
        <ul className="plain">
          {names.map((n) => (
            <li key={n} title={n}>
              {n}
            </li>
          ))}
          {group && group.node_ids.length > names.length && <li>… {group.node_ids.length - names.length} more</li>}
        </ul>
      </Section>
    </>
  );
}

function Corrections({ ids, resources }: { ids: string[]; resources: Record<string, Resource> }) {
  return (
    <ul className="plain">
      {ids.map((id) => {
        const r = resources[id];
        return (
          <li key={id}>
            <strong title={id}>{id}</strong>
            {!r ? (
              <div className="notrec">Resource record Not recorded</div>
            ) : (
              <>
                <ValueTree
                  value={{
                    kind: r.kind,
                    era: r.requested_era,
                    correction: r.correction,
                    version: r.correction_version,
                    sha256: r.sha256,
                    path: r.path,
                  }}
                />
                {r.fallback === true && (
                  <div className="warn">
                    <TriangleAlert size={14} aria-hidden="true" /> Fallback recorded
                    {r.fallback_reason ?? r.reason ? `: ${r.fallback_reason ?? r.reason}` : ""}
                  </div>
                )}
              </>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function GraphInfo({ e }: { e: GraphEntity }) {
  const rows =
    e.kind === "dataset"
      ? { "Dataset type": e.dataset_type, Events: e.event_count, Files: e.file_count, Group: e.group }
      : { Role: e.role, Implementation: e.implementation, ...(e.variation ? { Variation: e.variation } : {}) };
  return (
    <Section title="Overview">
      <table className="valuetree">
        <tbody>
          {Object.entries(rows).map(([k, v]) => (
            <tr key={k}>
              <th scope="row" style={{ paddingLeft: "0.4rem" }}>
                {k}
              </th>
              <td title={recorded(v)} className={v === undefined || v === null ? "notrec" : ""}>
                {recorded(v)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}
