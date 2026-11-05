import { artifactIcon, completenessIcon } from "../icons";
import type { ArtifactSearchEntry, RunsFile } from "../model/types";

export function Sidebar(props: {
  runs: RunsFile["runs"];
  runId?: string;
  query: string;
  results: ArtifactSearchEntry[];
  total: number;
  artifactId?: string;
  onRun: (id: string) => void;
  onQuery: (q: string) => void;
  onArtifact: (id: string) => void;
}) {
  return (
    <aside className="sidebar">
      <label>
        Run
        <select value={props.runId ?? ""} onChange={(e) => props.onRun(e.target.value)}>
          <option value="">Select a run</option>
          {props.runs.map((r) => (
            <option key={r.id} value={r.id}>
              {r.label}
            </option>
          ))}
        </select>
      </label>
      {props.runId ? (
        <>
          <input
            type="search"
            placeholder="Search artifacts"
            aria-label="Search artifacts"
            value={props.query}
            onChange={(e) => props.onQuery(e.target.value)}
          />
          <div className="count">
            {props.results.length} of {props.total} artifacts
          </div>
          <ul className="results">
            {props.results.map((a) => {
              const KindIcon = artifactIcon(a.kind);
              const StateIcon = completenessIcon(a.completeness);
              return (
              <li key={a.id}>
                <button
                  type="button"
                  className={a.id === props.artifactId ? "active" : ""}
                  onClick={() => props.onArtifact(a.id)}
                >
                  <KindIcon size={26} className="result-icon" aria-hidden="true" />
                  <span className="result-text">
                    <strong>{a.name}</strong>
                    <span className="sub">
                      {a.kind} · {a.producer_id ?? "producer not recorded"}
                    </span>
                    <span className={`badge ${a.completeness}`}>
                      <StateIcon size={12} aria-hidden="true" /> {a.completeness}
                    </span>
                  </span>
                </button>
              </li>
              );
            })}
            {props.results.length === 0 && <li className="empty">No artifact matches this search.</li>}
          </ul>
        </>
      ) : (
        <p className="empty">Examples are local, sanitized fixtures. Select a run to search its artifacts.</p>
      )}
    </aside>
  );
}
