import type { Actions } from "./GraphPane";
import type { TextAction, TextLineage } from "../model/textLineage";

/** Text lineage: the non-canvas view of exactly what the graph shows, with the same actions. */
export function TextView(props: {
  text: TextLineage;
  selectedId?: string;
  actions: Actions;
  onSelect: (id: string) => void;
}) {
  const { text, selectedId, actions, onSelect } = props;
  const run = (a: TextAction) => {
    if (a.kind === "from_source") actions.fromSource(a.groupId);
    else if (a.kind === "from_artifact") actions.fromArtifact(a.groupId);
    else if (a.kind === "expand") actions.expand(a.groupId);
    else actions.focus(a.groupId);
  };
  return (
    <section className="textview" aria-label="Textual lineage">
      <h2>{text.header[0]}</h2>
      {text.header.slice(1).map((h) => (
        <p key={h} className="sub">
          {h}
        </p>
      ))}
      {text.layers.map((l) => (
        <div key={l.index}>
          <h3>
            Layer {l.index}
            {l.parallel > 1 ? ` (${l.parallel} in parallel)` : ""}
          </h3>
          <ol className="textitems">
            {l.items.map((i) => (
              <li key={i.id} value={i.n} className={i.id === selectedId ? "selected" : ""}>
                <strong>[{i.tag}] {i.title}</strong>: {i.detail}
                {i.corrections.length > 0 && <span>; corrections: {i.corrections.join(", ")}</span>}
                <div className="sub">
                  {i.from.length > 0 && <span>from {i.from.join(", ")}. </span>}
                  {i.to.length > 0 && <span>to {i.to.join(", ")}. </span>}
                  {i.flow.map((f) => (
                    <span key={f}>{f}. </span>
                  ))}
                </div>
                <div className="actions">
                  <button type="button" onClick={() => onSelect(i.id)}>
                    Show details
                  </button>
                  {i.actions.map((a) => (
                    <button key={a.kind} type="button" onClick={() => run(a)}>
                      {a.label}
                    </button>
                  ))}
                </div>
              </li>
            ))}
          </ol>
        </div>
      ))}
    </section>
  );
}
