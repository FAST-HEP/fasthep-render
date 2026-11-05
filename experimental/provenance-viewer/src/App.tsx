import type { Viewport } from "@xyflow/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DetailsPanel } from "./components/DetailsPanel";
import { type Actions, GraphPane } from "./components/GraphPane";
import { Sidebar } from "./components/Sidebar";
import { StatusBar } from "./components/StatusBar";
import { loadDetails, loadGraph, loadRunIndex, loadRuns } from "./data/loader";
import { startLongTaskObserver } from "./data/metrics";
import type { Collapsed, Details, ProvenanceGraph, RunIndex, RunsFile } from "./model/types";
import {
  coarseView,
  defaultCollapsed,
  expandGroup,
  focusView,
  formatRoute,
  parseRoute,
  revealFromArtifact,
  revealFromSource,
  searchArtifacts,
} from "./model/viewModel";

type Load<T> = { state: "idle" } | { state: "loading" } | { state: "failed"; message: string } | { state: "ready"; value: T };

function useHashRoute() {
  const [route, setRoute] = useState(() => parseRoute(window.location.hash));
  useEffect(() => {
    const on = () => setRoute(parseRoute(window.location.hash));
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

export function App() {
  const route = useHashRoute();
  const [runs, setRuns] = useState<Load<RunsFile>>({ state: "loading" });
  const [index, setIndex] = useState<Load<RunIndex>>({ state: "idle" });
  const [graph, setGraph] = useState<Load<ProvenanceGraph>>({ state: "idle" });
  const [details, setDetails] = useState<Details | "loading" | "failed" | undefined>();
  const [query, setQuery] = useState("");
  const [collapsed, setCollapsed] = useState<Collapsed>(new Map());
  const [focus, setFocus] = useState<string | undefined>();
  const viewports = useRef(new Map<string, Viewport>());
  const [selectedId, setSelectedId] = useState<string | undefined>();

  useEffect(() => {
    startLongTaskObserver();
    loadRuns()
      .then((value) => setRuns({ state: "ready", value }))
      .catch((e: Error) => setRuns({ state: "failed", message: e.message }));
  }, []);

  useEffect(() => {
    setGraph({ state: "idle" });
    setSelectedId(undefined);
    if (!route.runId) return setIndex({ state: "idle" });
    setIndex({ state: "loading" });
    loadRunIndex(route.runId)
      .then((value) => setIndex({ state: "ready", value }))
      .catch((e: Error) => setIndex({ state: "failed", message: e.message }));
  }, [route.runId]);

  const artifact = useMemo(
    () => (index.state === "ready" ? index.value.artifacts.find((a) => a.id === route.artifactId) : undefined),
    [index, route.artifactId],
  );

  useEffect(() => {
    setSelectedId(undefined);
    setDetails(undefined);
    setFocus(undefined);
    viewports.current.clear();
    if (!route.runId || !artifact?.graph_ref) return setGraph({ state: "idle" });
    setGraph({ state: "loading" });
    loadGraph(route.runId, artifact.graph_ref)
      .then((value) => {
        setCollapsed(defaultCollapsed(value));
        setGraph({ state: "ready", value });
      })
      .catch((e: Error) => setGraph({ state: "failed", message: e.message }));
  }, [route.runId, artifact]);

  const view = useMemo(() => {
    if (graph.state !== "ready") return undefined;
    return (focus && focusView(graph.value, focus)) || coarseView(graph.value, collapsed);
  }, [graph, collapsed, focus]);
  const focusGroup = graph.state === "ready" ? graph.value.groups.find((g) => g.id === focus) : undefined;
  const paneKey = `${route.runId}/${artifact?.id}/${focus ?? ""}`;
  const selected = view?.nodes.find((n) => n.id === selectedId);

  const select = useCallback(
    (id: string) => {
      setSelectedId(id);
      if (details === undefined && route.runId && artifact?.details_ref) {
        setDetails("loading");
        loadDetails(route.runId, artifact.details_ref)
          .then(setDetails)
          .catch(() => setDetails("failed"));
      }
    },
    [details, route.runId, artifact],
  );
  const actions: Actions = useMemo(
    () => ({
      fromSource: (id) => setCollapsed((c) => revealFromSource(c, id)),
      fromArtifact: (id) => setCollapsed((c) => revealFromArtifact(c, id)),
      expand: (id) => setCollapsed((c) => expandGroup(c, id)),
      focus: setFocus,
    }),
    [],
  );
  const go = (runId?: string, artifactId?: string) => {
    window.location.hash = formatRoute({ runId, artifactId });
  };

  const results = index.state === "ready" ? searchArtifacts(index.value, query) : [];
  const runList = runs.state === "ready" ? runs.value.runs : [];
  const unknownArtifact = index.state === "ready" && route.artifactId && !artifact;

  return (
    <div className="app">
      <header className="banner">
        <strong>FAST-HEP provenance viewer</strong>
        <span className="exp">EXPERIMENTAL prototype, no stability promise</span>
      </header>
      <Sidebar
        runs={runList}
        runId={route.runId}
        query={query}
        results={results}
        total={index.state === "ready" ? index.value.artifacts.length : 0}
        artifactId={route.artifactId}
        onRun={(id) => go(id || undefined)}
        onQuery={setQuery}
        onArtifact={(id) => go(route.runId, id)}
      />
      <main className="graph">
        {runs.state === "failed" && <p className="warn">Could not load runs.json: {runs.message}</p>}
        {index.state === "failed" && <p className="warn">Could not load the run: {index.message}</p>}
        {unknownArtifact && <p className="warn">Unknown artifact “{route.artifactId}” in this run.</p>}
        {!route.runId && <p className="empty">No run selected.</p>}
        {index.state === "ready" && !route.artifactId && <p className="empty">Select an artifact to see its lineage.</p>}
        {artifact && !artifact.graph_ref && (
          <p className="warn">
            Provenance {artifact.completeness}: {artifact.completeness_note}.
          </p>
        )}
        {graph.state === "loading" && <p className="empty">Loading lineage…</p>}
        {graph.state === "failed" && <p className="warn">Could not load the lineage: {graph.message}</p>}
        {focusGroup && (
          <nav className="crumb" aria-label="Breadcrumb">
            <button type="button" onClick={() => setFocus(undefined)}>
              Overview
            </button>
            <span> › {focusGroup.kind}: {focusGroup.label} ({focusGroup.node_ids.length} entities)</span>
          </nav>
        )}
        {view && artifact && (
          <GraphPane
            paneKey={paneKey}
            view={view}
            resources={graph.state === "ready" ? (graph.value.resources ?? {}) : {}}
            selectedId={selectedId}
            initialViewport={viewports.current.get(paneKey)}
            actions={actions}
            onSelect={select}
            onViewport={(v) => viewports.current.set(paneKey, v)}
          />
        )}
      </main>
      <DetailsPanel artifact={artifact} entity={selected} details={details} graph={graph.state === "ready" ? graph.value : undefined} />
      <StatusBar
        status={
          view
            ? `${artifact?.name}: ${view.nodes.length} visible of ${graph.state === "ready" ? graph.value.nodes.length : 0} entities`
            : "Ready"
        }
      />
    </div>
  );
}
