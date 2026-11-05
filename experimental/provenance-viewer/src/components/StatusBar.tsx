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
  tab: "lineage" | "run";
  onTab: (t: "lineage" | "run") => void;
  canShowRun: boolean;
}) {
  const { status, tab, onTab, canShowRun } = props;
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
          Artifact lineage
        </button>
        <button type="button" aria-pressed={tab === "run"} disabled={!canShowRun} onClick={() => onTab("run")}>
          Run details
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
