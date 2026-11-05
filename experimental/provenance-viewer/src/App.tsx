import type { Viewport } from "@xyflow/react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DetailsPanel } from "./components/DetailsPanel";
import { type Actions, GraphPane } from "./components/GraphPane";
import { HelpView } from "./components/HelpView";
import { RunDetails } from "./components/RunDetails";
import { Sidebar } from "./components/Sidebar";
import { TextView } from "./components/TextView";
import { StatusBar } from "./components/StatusBar";
import { toTextLineage } from "./model/textLineage";
import { loadDetails, loadGraph, loadRunIndex, loadRuns } from "./data/loader";
import { startLongTaskObserver } from "./data/metrics";
import type { Collapsed, Details, Group, ProvenanceGraph, RunIndex, RunsFile } from "./model/types";
import {
  coarseView,
  defaultCollapsed,
  expandGroup,
  focusSubgraph,
  formatRoute,
  parseRoute,
  revealFromArtifact,
  revealFromSource,
  searchArtifacts,
  visibleSelection,
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
  const [focusPath, setFocusPath] = useState<string[]>([]);
  const [focusCollapsed, setFocusCollapsed] = useState<Collapsed>(new Map());
  const [tab, setTab] = useState<"lineage" | "text" | "run" | "help">("lineage");
  const viewports = useRef(new Map<string, Viewport>());
  const detailsRequest = useRef<AbortController>();
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
    const ctl = new AbortController();
    loadRunIndex(route.runId, ctl.signal)
      .then((value) => setIndex({ state: "ready", value }))
      .catch((e: Error) => e.name !== "AbortError" && setIndex({ state: "failed", message: e.message }));
    return () => ctl.abort(); // a slower earlier response must not overwrite a newer selection
  }, [route.runId]);

  const artifact = useMemo(
    () => (index.state === "ready" ? index.value.artifacts.find((a) => a.id === route.artifactId) : undefined),
    [index, route.artifactId],
  );

  useEffect(() => {
    detailsRequest.current?.abort(); // details of the previous artifact must not arrive late
    setSelectedId(undefined);
    setDetails(undefined);
    setFocusPath([]);
    viewports.current.clear();
    if (!route.runId || !artifact?.graph_ref) return setGraph({ state: "idle" });
    setGraph({ state: "loading" });
    const ctl = new AbortController();
    loadGraph(route.runId, artifact.graph_ref, ctl.signal)
      .then((value) => {
        setCollapsed(defaultCollapsed(value));
        setGraph({ state: "ready", value });
      })
      .catch((e: Error) => e.name !== "AbortError" && setGraph({ state: "failed", message: e.message }));
    return () => ctl.abort();
  }, [route.runId, artifact]);

  // Only a graph that belongs to the selected artifact may be shown; during a switch the
  // previous artifact's graph is still in state for a moment and must not be laid out.
  const current: ProvenanceGraph | undefined =
    graph.state === "ready" && graph.value.artifact_id === artifact?.id ? graph.value : undefined;

  // The graph being shown: the artifact graph, or a focused subgraph of it (nested).
  const shown = useMemo(() => {
    if (!current) return undefined;
    let g: ProvenanceGraph | undefined = current;
    for (const id of focusPath) g = g && focusSubgraph(g, id);
    return g;
  }, [current, focusPath]);
  const collapsedNow = focusPath.length ? focusCollapsed : collapsed;
  const setCollapsedNow = focusPath.length ? setFocusCollapsed : setCollapsed;
  const view = useMemo(() => (shown ? coarseView(shown, collapsedNow) : undefined), [shown, collapsedNow]);
  const crumbs = useMemo(() => {
    if (!current) return [];
    const out: { id: string; label: string }[] = [];
    let g: ProvenanceGraph | undefined = current;
    for (const id of focusPath) {
      const grp: Group | undefined = g?.groups.find((x) => x.id === id);
      out.push({ id, label: grp ? `${grp.label} (${grp.node_ids.length})` : id });
      g = g && focusSubgraph(g, id);
    }
    return out;
  }, [current, focusPath]);
  const text = useMemo(
    () =>
      view && artifact
        ? toTextLineage(view, artifact, (e) => (e.kind === "processing" ? (e.resource_ids ?? []) : []))
        : undefined,
    [view, artifact],
  );
  const paneKey = `${route.runId}/${artifact?.id}/${focusPath.join(">")}`;
  const selected = view ? visibleSelection(view, selectedId) : undefined;

  const select = useCallback(
    (id: string) => {
      setSelectedId(id);
      if (details === undefined && route.runId && artifact?.details_ref) {
        setDetails("loading");
        const ctl = new AbortController();
        detailsRequest.current?.abort();
        detailsRequest.current = ctl;
        loadDetails(route.runId, artifact.details_ref, ctl.signal)
          .then(setDetails)
          .catch((e: Error) => e.name !== "AbortError" && setDetails("failed"));
      }
    },
    [details, route.runId, artifact],
  );
  const focusInto = useCallback(
    (groupId: string) => {
      if (!shown) return;
      const sub = focusSubgraph(shown, groupId);
      if (!sub) return;
      setFocusCollapsed(defaultCollapsed(sub));
      setFocusPath((p) => [...p, groupId]);
    },
    [shown],
  );
  const focusBack = (depth: number) => {
    // depth 0 is the overview; deeper levels keep their own collapse defaults
    const path = focusPath.slice(0, depth);
    let g: ProvenanceGraph | undefined = current;
    for (const id of path) g = g && focusSubgraph(g, id);
    if (g && path.length) setFocusCollapsed(defaultCollapsed(g));
    setFocusPath(path);
  };
  const actions: Actions = useMemo(
    () => ({
      fromSource: (id) => setCollapsedNow((c) => revealFromSource(c, id)),
      fromArtifact: (id) => setCollapsedNow((c) => revealFromArtifact(c, id)),
      expand: (id) => setCollapsedNow((c) => expandGroup(c, id)),
      focus: focusInto,
    }),
    [setCollapsedNow, focusInto],
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
        {index.state === "ready" && index.value.run.synthetic_note && (
          <p className="warn synthetic">SYNTHETIC RUN, not real provenance: {index.value.run.synthetic_note}</p>
        )}
        {tab === "help" && <HelpView />}
        {tab === "run" && index.state === "ready" && <RunDetails index={index.value} />}
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
        {tab === "text" && text && (
          <TextView text={text} selectedId={selectedId} actions={actions} onSelect={select} />
        )}
        {crumbs.length > 0 && (tab === "lineage" || tab === "text") && (
          <nav className="crumb" aria-label="Breadcrumb">
            <button type="button" onClick={() => focusBack(0)}>
              Overview
            </button>
            {crumbs.map((c, i) => (
              <span key={c.id}>
                {" › "}
                {i === crumbs.length - 1 ? (
                  c.label
                ) : (
                  <button type="button" onClick={() => focusBack(i + 1)}>
                    {c.label}
                  </button>
                )}
              </span>
            ))}
          </nav>
        )}
        {tab === "lineage" && view && artifact && (
          <GraphPane
            paneKey={paneKey}
            view={view}
            resources={shown?.resources ?? {}}
            selectedId={selectedId}
            initialViewport={viewports.current.get(paneKey)}
            actions={actions}
            onSelect={select}
            onViewport={(v) => viewports.current.set(paneKey, v)}
          />
        )}
      </main>
      <DetailsPanel artifact={artifact} entity={selected} details={details} graph={shown} runId={route.runId} />
      <StatusBar
        tab={tab}
        onTab={setTab}
        canShowRun={index.state === "ready"}
        canShowText={text !== undefined}
        status={
          view
            ? `${artifact?.name}: ${view.nodes.length} visible of ${current ? current.nodes.length : 0} entities${crumbs.length ? " (focused)" : ""}`
            : "Ready"
        }
      />
    </div>
  );
}
