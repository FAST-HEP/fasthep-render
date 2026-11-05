"""Normalise a Flow run bundle into viewer JSON (schema sketch version 1)."""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from . import SCHEMA_VERSION
from .graph_repr import parse_graph_node
from .groups import add_variation_family, candidate_groups
from .sanitize import Sanitizer, find_leaks

# manifest key per artifacts/<dir>/manifest.json; each entry has a producer node id
_LIST_MANIFESTS = {"cutflows": "cutflow", "histograms": "histogram", "tables": "table"}


def _load(path: Path) -> Any:
    return json.loads(path.read_text())


def _slug(kind: str, path: str) -> str:
    return f"{kind}-{hashlib.sha1(path.encode()).hexdigest()[:10]}"


def _write(path: Path, data: Any) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=1, sort_keys=True) + "\n"
    path.write_text(text)
    return len(text.encode())


def _artifact_entries(bundle: Path) -> list[dict[str, Any]]:
    """Every manifest entry that names an artifact and its producer node."""
    out: list[dict[str, Any]] = []
    prov = bundle / "artifacts/provenance/manifest.json"
    records: dict[str, dict[str, Any]] = {}
    if prov.exists():
        for rec in _load(prov).get("records", []):
            records[rec["artifact"]] = rec
    for sub, kind in _LIST_MANIFESTS.items():
        f = bundle / f"artifacts/{sub}/manifest.json"
        if f.exists():
            for item in _load(f).get(sub, []):
                out.append(
                    {
                        "name": item["id"],
                        "path": item["path"],
                        "kind": kind,
                        "producer": item.get("producer"),
                        "source_manifest": f"artifacts/{sub}/manifest.json",
                    }
                )
    for f in sorted((bundle / "artifacts/files").glob("*/manifest.json")):
        m = _load(f)
        for ds in m.get("datasets", {}).values():
            for item in ds.get("files", []):
                out.append(
                    {
                        "name": Path(item["path"]).name,
                        "path": item["path"],
                        "kind": m.get("kind", "file"),
                        "producer": m.get("node_id"),
                        "source_manifest": str(f.relative_to(bundle)),
                    }
                )
    for plot in sorted((bundle / "artifacts/plots").glob("*")):
        rel = str(plot.relative_to(bundle))
        out.append(
            {
                "name": plot.stem,
                "path": rel,
                "kind": "plot",
                "producer": f"render.{plot.stem}.0",
                "source_manifest": "artifacts/plots (directory listing)",
            }
        )
    for e in out:
        for rpath, rec in records.items():
            if rpath.endswith(e["path"]) or e["path"].endswith(rpath):
                e["record"] = rec
                e["producer"] = e["producer"] or rec.get("node_id")
    return out


def _resource(raw: dict[str, Any]) -> dict[str, Any]:
    """Flatten a recorded resource: top-level facts plus the selected file."""
    out = {k: v for k, v in raw.items() if k != "selected"}
    sel = raw.get("selected") or {}
    for key in (
        "correction",
        "correction_version",
        "fallback",
        "sha256",
        "size_bytes",
        "path",
    ):
        if key in sel:
            out[key] = sel[key]
    for key in ("fallback_reason", "reason"):
        if key in sel:
            out[key] = sel[key]
    return out


_PREVIEW_SUFFIXES = {".png", ".svg", ".pdf"}
_PREVIEW_MAX_BYTES = 1_000_000


def _copy_preview(bundle: Path, rel: str, out: Path) -> str | None:
    """Copy a small plot file next to the viewer JSON; return its relative ref."""
    src = bundle / rel
    if src.suffix.lower() not in _PREVIEW_SUFFIXES or not src.is_file():
        return None
    if src.stat().st_size > _PREVIEW_MAX_BYTES:
        return None
    ref = f"referenced-files/{src.name}"
    (out / ref).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, out / ref)
    return ref


_RESOLVED_KEYS = (
    "impl",
    "inputs",
    "outputs",
    "input_scope",
    "output_scope",
    "partitioning",
    "materialize",
)


_ROLE_SECTION = {
    "source": "sources",
    "transform": "transforms",
    "sink": "sinks",
    "observer": "observers",
}


def _resolved_by_plan(bundle: Path) -> dict[str, dict[str, Any]]:
    """What each node resolves to in the compile plan (without its parameters).

    A plan node only names a registry key (``hep.hist``); the callable it runs is in
    the plan's ``registry`` section and the profile that supplied it in
    ``provenance.registry_changes``. Both are joined here.
    """
    plan = bundle / "compile/plan.yaml"
    if not plan.exists():
        return {}
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    data = yaml.load(plan.read_text(), Loader=loader)
    registry = data.get("registry", {})
    changes = (data.get("provenance") or {}).get("registry_changes") or {}
    layer: dict[tuple[str, str], str] = {}
    for kind in ("added", "replaced", "overridden"):  # later entries win
        for c in changes.get(kind, []) or []:
            layer[(c.get("section"), c.get("key"))] = c.get("layer")
    out: dict[str, dict[str, Any]] = {}
    for n in data.get("nodes", []):
        item: dict[str, Any] = {"impl": n.get("impl")}
        section = _ROLE_SECTION.get(n.get("role"), "")
        entry = (registry.get(section) or {}).get(n.get("impl"))
        if isinstance(entry, dict):
            item["callable"] = entry.get("impl")
            item["spec"] = entry.get("spec")
            item["provided_by"] = layer.get((section, n.get("impl")))
        op = (n.get("meta") or {}).get("workflow_op")
        if op is not None:
            item["workflow_op"] = op
        for k in _RESOLVED_KEYS:
            if k != "impl" and k in n:
                item[k] = n[k]
        out[n["id"]] = item
    return out


def _ancestors(target: str, pred: dict[str, list[str]]) -> set[str]:
    seen, stack = {target}, [target]
    while stack:
        for p in pred.get(stack.pop(), []):
            if p not in seen:
                seen.add(p)
                stack.append(p)
    return seen


def normalise(
    bundle: Path,
    out: Path,
    *,
    sanitize: bool = True,
    only: tuple[str, ...] = (),
    synthetic: str | None = None,
) -> dict[str, Any]:
    bundle = bundle.resolve()
    t0 = time.perf_counter()
    graph = _load(bundle / "graph/graph.json")
    execution = _load(bundle / "artifacts/provenance/execution.json")
    env = execution.get("execution", {})
    san = Sanitizer(
        bundle_root=str(bundle),
        secrets=(
            str(env.get("hostname", "")),
            str(env.get("fqdn", "")),
            Path.home().name,
        ),
    )
    clean = san.any if sanitize else (lambda v: v)

    nodes: dict[str, dict[str, Any]] = {}
    for n in graph["nodes"]:
        parsed = parse_graph_node(n["payload"])
        nodes[n["id"]] = parsed
    edges = graph["edges"]
    pred: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        pred[e["target"]].append(e["source"])

    node_resources: dict[str, list[str]] = defaultdict(list)
    node_ops: dict[str, Any] = {}
    for ex in execution.get("executions", {}).values():
        nid = ex.get("node_id")
        ops = ex.get("operations") or []
        if nid not in node_ops and ops:
            node_ops[nid] = ops
        for op in ops:
            for rid in (op.get("inputs") or {}).get("resources", []):
                if rid not in node_resources[nid]:
                    node_resources[nid].append(rid)
    executions_per_node: dict[str, int] = defaultdict(int)
    for ex in [
        *execution.get("executions", {}).values(),
        *execution.get("node_executions", []),
    ]:
        executions_per_node[ex.get("node_id")] += 1
    catalog = execution.get("resources", {})
    resolved = _resolved_by_plan(bundle)

    run_id = execution["run_id"]
    summary = {}
    if (bundle / "run_summary.yaml").exists():
        summary = {"has_run_summary": True}
    entries = _artifact_entries(bundle)
    if only:
        entries = [e for e in entries if e["name"] in only]

    sizes: dict[str, int] = {}
    index_entries: list[dict[str, Any]] = []
    for e in entries:
        aid = _slug(e["kind"], e["path"])
        producer = e["producer"]
        has_record = "record" in e
        in_graph = producer in nodes
        if has_record and in_graph:
            completeness = "complete"
        elif in_graph:
            completeness = "partial"
        else:
            completeness = "unavailable"
        entry = {
            "id": aid,
            "run_id": run_id,
            "name": e["name"],
            "path": clean(e["path"]),
            "kind": e["kind"],
            "producer_id": producer,
            "completeness": completeness,
            "completeness_note": {
                "complete": "provenance record and graph producer found",
                "partial": "no provenance record; lineage derived from the compile graph",
                "unavailable": "producer node not found in the graph",
            }[completeness],
        }
        if in_graph:
            anc = _ancestors(producer, pred)
            sub_edges = [x for x in edges if x["source"] in anc and x["target"] in anc]
            variations = {
                n: nodes[n]["meta"]["variation"]
                for n in anc
                if isinstance(nodes[n].get("meta", {}).get("variation"), dict)
            }
            groups = add_variation_family(
                candidate_groups(sorted(anc), sub_edges, variations), sub_edges
            )
            graph_nodes = []
            details: dict[str, Any] = {}
            datasets = []
            for nid in sorted(anc):
                p = nodes[nid]
                params = dict(p.get("params") or {})
                if p.get("role") == "source":
                    for ds in params.pop("datasets", []):
                        files = ds.get("files", [])
                        datasets.append(
                            {
                                "kind": "dataset",
                                "id": f"dataset:{ds['name']}",
                                "label": ds["name"],
                                "dataset_type": ds.get("eventtype"),
                                "event_count": ds.get("nevents"),
                                "file_count": len(files),
                                "group": ds.get("group"),
                                "meta": clean(ds.get("meta", {})),
                                "source_node": nid,
                            }
                        )
                graph_nodes.append(
                    {
                        "kind": "processing",
                        "id": nid,
                        "label": nid.split(".", 1)[-1],
                        "role": p.get("role"),
                        "implementation": p.get("impl"),
                        "resource_ids": sorted(node_resources.get(nid, [])),
                        "variation": (p.get("meta") or {})
                        .get("variation", {})
                        .get("name")
                        if isinstance((p.get("meta") or {}).get("variation"), dict)
                        else None,
                    }
                )
                details[nid] = {
                    # None (not 0) when the run recorded no execution of this node
                    "execution_count": executions_per_node.get(nid) or None,
                    "resolved": clean(resolved.get(nid)),
                    "operations": clean(node_ops.get(nid)),
                    "params": clean(params),
                    "outputs": p.get("outputs"),
                    "meta": clean(p.get("meta", {})),
                }
            if len(datasets) >= 4:
                groups.append(
                    {
                        "id": "datasets:all",
                        "kind": "datasets",
                        "label": f"{len(datasets)} datasets",
                        "origin": "source",
                        "source_ref": "read node params.datasets",
                        "node_ids": [d["id"] for d in datasets],
                        "entry_edges": [],
                        "exit_edges": [
                            {"source": d["id"], "target": d["source_node"]}
                            for d in datasets
                        ],
                    }
                )
            used = sorted({r for n in anc for r in node_resources.get(n, [])})
            resources = {rid: clean(_resource(catalog.get(rid, {}))) for rid in used}
            ds_edges = [
                {"source": d["id"], "target": d["source_node"], "output": "dataset"}
                for d in datasets
            ]
            doc = {
                "schema_version": SCHEMA_VERSION,
                "run_id": run_id,
                "artifact_id": aid,
                "nodes": graph_nodes + datasets,
                "edges": sub_edges + ds_edges,
                "groups": groups,
                "resources": resources,
            }
            sizes[f"artifacts/{aid}/graph.json"] = _write(
                out / f"artifacts/{aid}/graph.json", doc
            )
            sizes[f"artifacts/{aid}/details.json"] = _write(
                out / f"artifacts/{aid}/details.json",
                {
                    "schema_version": SCHEMA_VERSION,
                    "artifact_id": aid,
                    "nodes": details,
                },
            )
            entry["graph_ref"] = f"artifacts/{aid}/graph.json"
            entry["details_ref"] = f"artifacts/{aid}/details.json"
            entry["ancestor_count"] = len(anc)
        index_entries.append(entry)

    # A plot is the preview of an artifact when the graph has an edge from the
    # artifact's producer to the plot's producer (derived from recorded edges).
    by_producer = {e["producer_id"]: e for e in index_entries if e.get("producer_id")}
    plots = [e for e in index_entries if e["kind"] == "plot"]
    for e in plots:
        ref = _copy_preview(bundle, e["path"], out)
        if ref:
            e["preview_ref"] = ref
            e["preview_path"] = e["path"]
            for src_id in pred.get(e["producer_id"], []):
                owner = by_producer.get(src_id)
                if owner is not None and owner is not e and "preview_ref" not in owner:
                    owner["preview_ref"] = ref
                    owner["preview_path"] = e["path"]
                    owner["preview_note"] = (
                        f"plot {e['name']}: graph edge {src_id} to {e['producer_id']}"
                    )

    run_index = {
        "schema_version": SCHEMA_VERSION,
        "run": {
            "id": run_id,
            "software": execution.get("software"),
            "execution": clean(
                {k: v for k, v in env.items() if k not in {"hostname", "fqdn"}}
            ),
            "partition_count": len(execution.get("partitions", [])),
            "resource_ids": sorted(execution.get("resources", {})),
            "resource_summary": {
                rid: {
                    "kind": r.get("kind"),
                    "requested_era": r.get("requested_era"),
                    "fallback": (r.get("selected") or {}).get("fallback"),
                }
                for rid, r in sorted(execution.get("resources", {}).items())
            },
            "synthetic_note": synthetic,
            "graph_node_count": len(nodes),
            "graph_edge_count": len(edges),
            **summary,
        },
        "artifacts": sorted(index_entries, key=lambda x: (x["kind"], x["path"])),
    }
    sizes["run-index.json"] = _write(out / "run-index.json", run_index)

    leaks = find_leaks(run_index) if sanitize else ["sanitization disabled"]
    for rel in sizes:
        if sanitize:
            leaks += find_leaks(_load(out / rel))
    report = {
        "schema_version": SCHEMA_VERSION,
        "tool": "fasthep_render.experimental.provenance.normalise",
        "bundle_label": bundle.name,
        "subset_of_artifacts": list(only) or None,
        "sanitized": sanitize,
        "sanitization_counts": san.counts,
        "leaks_found": sorted(set(leaks)),
        "source_graph_sha256": hashlib.sha256(
            (bundle / "graph/graph.json").read_bytes()
        ).hexdigest(),
        "origin_summary": {
            "source": "graph nodes, edges, dataset facts, meta.variation groups",
            "sanitized": "paths, host names, user names",
            "inferred": "chain and region groups (computed here)",
            "curated": [],
            "synthetic": [synthetic] if synthetic else [],
        },
        "measurements": {
            "normalise_seconds": round(time.perf_counter() - t0, 3),
            "output_bytes": sizes,
            "artifacts": len(index_entries),
        },
    }
    _write(out / "fixture-provenance.json", report)
    (out / "FIXTURE.md").write_text(_fixture_md(report, run_index))
    return report


def _fixture_md(report: dict[str, Any], run_index: dict[str, Any]) -> str:
    rows = "\n".join(
        f"| {a['name']} | {a['kind']} | {a['completeness']} | {a.get('ancestor_count', '-')} |"
        for a in run_index["artifacts"]
    )
    origins = "\n".join(f"- `{k}`: {v}" for k, v in report["origin_summary"].items())
    subset = report["subset_of_artifacts"]
    return (
        f"# Fixture: {report['bundle_label']}\n\n"
        "Generated by `fasthep_render.experimental.provenance` (experimental). "
        "Do not edit by hand; regenerate from the bundle.\n\n"
        + (
            f"**SYNTHETIC RUN: {report['origin_summary']['synthetic'][0]}**\n\n"
            if report["origin_summary"]["synthetic"]
            else ""
        )
        + f"- source graph sha256: `{report['source_graph_sha256']}`\n"
        f"- sanitized: {report['sanitized']}; rules fired: {report['sanitization_counts']}\n"
        f"- subset of artifacts: {subset if subset else 'all'}\n\n"
        f"## Artifacts\n\n| name | kind | provenance | ancestors |\n|---|---|---|---|\n{rows}\n\n"
        f"## Origin of fields\n\n{origins}\n"
    )
