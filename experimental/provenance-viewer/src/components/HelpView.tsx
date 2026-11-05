import type { LucideIcon } from "lucide-react";
import { ArrowRightFromLine, ArrowRightToLine, Boxes, Cog, Database, Eye, FileInput, HardDriveDownload, Layers, SlidersHorizontal, Split, TriangleAlert } from "lucide-react";
import { artifactIcon, completenessIcon } from "../icons";
import type { Completeness } from "../model/types";

function Sample(props: { icon: LucideIcon; className: string; label: string }) {
  const Icon = props.icon;
  return (
    <div className={`node sample ${props.className}`}>
      <Icon size={22} aria-hidden="true" />
      <span>{props.label}</span>
    </div>
  );
}

const STATES: [Completeness, string][] = [
  ["complete", "A provenance record exists and the producer is in the graph."],
  ["partial", "No record for this artifact; the lineage is derived from the compile graph."],
  ["unavailable", "The producer is not in the graph, so no lineage can be shown."],
  ["not_recorded", "A single fact was not recorded (shown as the words Not recorded)."],
];

// Artifact kinds as they appear in the sidebar; icons come from the same mapping the sidebar uses.
const ARTIFACTS: [string, string, string][] = [
  ["histogram", "Histogram", "A filled histogram, as written by a histogram step."],
  ["plot", "Plot", "A rendered image of a product, such as a histogram. Its details show a preview."],
  ["cutflow", "Cutflow", "Event counts after each selection step."],
  ["table", "Table", "A table, such as a CSV export."],
  ["root_tree", "Other file", "Any other written file, such as a skim (a ROOT tree)."],
];

/** The legend: every shape, icon, badge and control the viewer uses, in one place. */
export function HelpView() {
  return (
    <section className="helpview" aria-label="Legend">
      <h2>Legend</h2>
      <p className="sub">The lineage reads from datasets (top) to the selected artifact (bottom). Select a node to see its details.</p>

      <h3>Things in the graph</h3>
      <div className="legend">
        <Sample icon={Database} className="node-dataset" label="Dataset" />
        <span>A logical dataset with its type and event count. File lists are not shown.</span>
        <Sample icon={FileInput} className="role-source" label="Source" />
        <span>Reads the datasets into the workflow.</span>
        <Sample icon={Cog} className="role-transform" label="Transform" />
        <span>A processing step (a Flow graph node).</span>
        <Sample icon={HardDriveDownload} className="role-sink" label="Sink" />
        <span>Writes a product, such as a histogram or a file.</span>
        <Sample icon={Eye} className="role-observer" label="Observer" />
        <span>Watches the stream without changing it.</span>
        <Sample icon={Layers} className="node-summary" label="Hidden steps" />
        <span>Dashed: several entities collapsed into one box. The count, group and origin are on it.</span>
        <Sample icon={Boxes} className="node-summary" label="Hidden group" />
        <span>Dashed: a group, such as the 24 variations. Use Show all or Focus.</span>
        <Sample icon={Split} className="node-summary" label="Variation" />
        <span>One systematic variation: a recorded copy of the processing chain.</span>
        <Sample icon={ArrowRightToLine} className="node-boundary" label="From outside" />
        <span>Dotted: in a focused view, something outside the group that feeds into it.</span>
        <Sample icon={ArrowRightFromLine} className="node-boundary" label="To outside" />
        <span>Dotted: in a focused view, something outside the group that this feeds.</span>
        <div className="node sample">
          <span className="badge">
            <SlidersHorizontal size={11} aria-hidden="true" /> 2 corrections
          </span>
        </div>
        <span>The step uses recorded corrections or resources (details panel lists them).</span>
        <div className="node sample">
          <span className="badge warnbadge">
            <TriangleAlert size={11} aria-hidden="true" /> fallback recorded
          </span>
        </div>
        <span>The record says a fallback was used. Shown only when it was recorded.</span>
      </div>

      <h3>Artifacts in the sidebar</h3>
      <div className="legend">
        {ARTIFACTS.map(([kind, label, text]) => {
          const Icon = artifactIcon(kind);
          return (
            <div key={kind} className="contents">
              <div className="node sample">
                <Icon size={22} aria-hidden="true" />
                <span>{label}</span>
              </div>
              <span>{text}</span>
            </div>
          );
        })}
      </div>

      <h3>Selection</h3>
      <p>The selected node keeps its colour and gets a thicker outline.</p>

      <h3>Provenance of an artifact</h3>
      <ul className="plain">
        {STATES.map(([c, text]) => {
          const Icon = completenessIcon(c);
          return (
            <li key={c}>
              <span className={`badge ${c}`}>
                <Icon size={12} aria-hidden="true" /> {c.replace("_", " ")}
              </span>{" "}
              {text}
            </li>
          );
        })}
      </ul>

      <h3>Where a fact comes from</h3>
      <ul className="plain">
        <li><strong>source</strong>: taken from the run's own records.</li>
        <li><strong>inferred</strong>: computed by this viewer, not recorded by Flow (for example linear runs and the variation family).</li>
        <li><strong>curated</strong>: added by hand to bridge a gap, with documented evidence.</li>
        <li><strong>synthetic</strong>: invented to exercise the viewer; the run is labelled.</li>
        <li><strong>sanitized</strong>: a machine-specific value was replaced.</li>
      </ul>

      <h3>Controls</h3>
      <ul className="plain">
        <li><strong>Reveal from top / bottom</strong>: show one more hidden step from the dataset side or the artifact side.</li>
        <li><strong>Show all</strong>: open a hidden box completely. <strong>Focus</strong>: look at one group on its own; the breadcrumb goes back.</li>
        <li><strong>Text view</strong>: the same lineage as a list, with the same controls. <strong>Run details</strong>: software, environment and resources of the whole run.</li>
        <li>In the details panel: <strong>view as text</strong> shows the raw record, <strong>copy</strong> copies it.</li>
      </ul>

      <h3>Missing and empty</h3>
      <p>
        <span className="notrec">Not recorded</span> means the run did not record the fact. <code>(empty)</code> means it was recorded as empty.
      </p>
    </section>
  );
}
