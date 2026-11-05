import { CircleHelp, FileText, Info, Workflow } from "lucide-react";
import { useSyncExternalStore } from "react";
import { snapshot, subscribe } from "../data/metrics";

let cache = snapshot();
function getSnapshot() {
  return cache;
}
function sub(l: () => void) {
  return subscribe(() => {
    cache = snapshot();
    l();
  });
}

export function StatusBar(props: {
  status: string;
  tab: "lineage" | "text" | "run" | "help";
  onTab: (t: "lineage" | "text" | "run" | "help") => void;
  canShowText: boolean;
  canShowRun: boolean;
}) {
  const { status, tab, onTab, canShowRun, canShowText } = props;
  const metrics = useSyncExternalStore(sub, getSnapshot);
  const last = (n: string) => metrics.filter((m) => m.name === n).at(-1);
  const bytes = metrics.filter((m) => m.name.endsWith(":bytes")).reduce((s, m) => s + m.value, 0);
  const layoutMs = last("layout");
  const frame = last("render:first-frame");
  const tasks = metrics.filter((m) => m.name === "long-task");
  return (
    <footer className="status">
      <span className="tabs">
        <button type="button" aria-pressed={tab === "lineage"} onClick={() => onTab("lineage")}>
          <Workflow size={16} aria-hidden="true" /> Artifact lineage
        </button>
        <button type="button" aria-pressed={tab === "text"} disabled={!canShowText} onClick={() => onTab("text")}>
          <FileText size={16} aria-hidden="true" /> Text view
        </button>
        <button type="button" aria-pressed={tab === "run"} disabled={!canShowRun} onClick={() => onTab("run")}>
          <Info size={16} aria-hidden="true" /> Run details
        </button>
        <button type="button" aria-pressed={tab === "help"} onClick={() => onTab("help")}>
          <CircleHelp size={16} aria-hidden="true" /> Help
        </button>
      </span>
      <span>{status}</span>
      <span>
        loaded {(bytes / 1024).toFixed(0)} KB · layout {layoutMs ? `${layoutMs.value} ms` : "-"} ·
        first frame {frame ? `${frame.value} ms` : "-"} · long tasks {tasks.length}
      </span>
    </footer>
  );
}
