import { recorded } from "../model/format";
import type { RunIndex } from "../model/types";



function Table({ rows }: { rows: [string, unknown][] }) {
  return (
    <table>
      <tbody>
        {rows.map(([k, v]) => (
          <tr key={k}>
            <th scope="row">{k}</th>
            <td className={v === undefined || v === null ? "notrec" : ""}>{recorded(v)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** Read-only evidence about the run as a whole; the lineage stays the main screen. */
export function RunDetails({ index }: { index: RunIndex }) {
  const r = index.run;
  const resources = Object.entries(r.resource_summary ?? {});
  return (
    <section className="rundetails">
      <h2>Run details</h2>
      <h3>Run</h3>
      <Table
        rows={[
          ["Run id", r.id],
          ["Artifacts", index.artifacts.length],
          ["Partitions", r.partition_count],
          ["Graph", `${r.graph_node_count} nodes, ${r.graph_edge_count} edges`],
        ]}
      />
      <h3>Software</h3>
      <Table rows={Object.entries(r.software ?? {})} />
      <h3>Environment</h3>
      <Table rows={Object.entries(r.execution ?? {})} />
      <h3>Resources ({resources.length})</h3>
      {resources.length === 0 ? (
        <p className="notrec">No resources recorded</p>
      ) : (
        <ul className="members">
          {resources.map(([id, s]) => (
            <li key={id}>
              <strong>{id}</strong> {recorded(s.kind)} · era {recorded(s.requested_era)}
              {s.fallback === true && <span className="badge warnbadge">fallback recorded</span>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
