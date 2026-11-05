"""Guards for the checked-in viewer fixtures (leaks, integrity, determinism)."""

from __future__ import annotations

import importlib.util
import json
import warnings
from pathlib import Path

import pytest

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from fasthep_render.experimental.provenance.normalise import normalise

FIXTURES = (
    Path(__file__).resolve().parents[2] / "experimental/provenance-viewer/fixtures"
)
RUNS = sorted(p for p in FIXTURES.iterdir() if (p / "run-index.json").exists())
# Machine-specific values that must never be checked in. The user name and host
# names of known development machines are listed because the path pattern alone
# would miss them in free text.
FORBIDDEN = ("/home/", "/Users/", "/afs/", "/eos/", "phxlk", "prometheus", "IT110403")


def _json(path: Path) -> dict:
    return json.loads(path.read_text())


def test_fixtures_present() -> None:
    assert {p.name for p in RUNS} >= {
        "zmumu",
        "chip-large-sample",
        "synthetic-fallback",
    }


@pytest.mark.parametrize("run", RUNS, ids=lambda p: p.name)
def test_no_machine_specific_content(run: Path) -> None:
    for f in run.rglob("*"):
        if f.is_file():
            data = f.read_bytes()  # binary previews are checked too
            hits = [s for s in FORBIDDEN if s.encode() in data]
            assert not hits, f"{f.relative_to(FIXTURES)} contains {hits}"
    assert _json(run / "fixture-provenance.json")["leaks_found"] == []


@pytest.mark.parametrize("run", RUNS, ids=lambda p: p.name)
def test_every_asset_declares_schema_version(run: Path) -> None:
    for f in run.rglob("*.json"):
        assert _json(f)["schema_version"] == 1, f


@pytest.mark.parametrize("run", RUNS, ids=lambda p: p.name)
def test_referential_integrity(run: Path) -> None:
    index = _json(run / "run-index.json")
    assert index["artifacts"]
    for a in index["artifacts"]:
        assert a["completeness"] in {
            "complete",
            "partial",
            "unavailable",
            "not_recorded",
        }
        if a["completeness"] == "unavailable":
            assert "graph_ref" not in a
            continue
        graph = _json(run / a["graph_ref"])
        details = _json(run / a["details_ref"])
        ids = {n["id"] for n in graph["nodes"]}
        assert len(ids) == len(graph["nodes"])
        assert a["producer_id"] in ids
        for e in graph["edges"]:
            assert e["source"] in ids
            assert e["target"] in ids
        for g in graph["groups"]:
            assert g["origin"] in {
                "source",
                "sanitized",
                "curated",
                "inferred",
                "synthetic",
            }
            assert set(g["node_ids"]) <= ids
        processing = {n["id"] for n in graph["nodes"] if n["kind"] == "processing"}
        assert set(details["nodes"]) == processing


@pytest.mark.parametrize("run", RUNS, ids=lambda p: p.name)
def test_every_file_is_listed_or_known(run: Path) -> None:
    index = _json(run / "run-index.json")
    expected = {"run-index.json", "fixture-provenance.json", "FIXTURE.md"}
    for a in index["artifacts"]:
        expected |= {a.get("graph_ref"), a.get("details_ref"), a.get("preview_ref")} - {
            None
        }
    found = {str(f.relative_to(run)) for f in run.rglob("*") if f.is_file()}
    assert found == expected


def test_preview_files_exist_and_are_small() -> None:
    previews = 0
    for run in RUNS:
        for a in _json(run / "run-index.json")["artifacts"]:
            if "preview_ref" in a:
                previews += 1
                assert (run / a["preview_ref"]).stat().st_size <= 1_000_000
    assert previews >= 2  # the Z-mumu histogram and its plot


def test_synthetic_run_is_labelled_and_exercises_every_state() -> None:
    run = FIXTURES / "synthetic-fallback"
    index = _json(run / "run-index.json")
    assert index["run"]["synthetic_note"]
    assert "SYNTHETIC" in (run / "FIXTURE.md").read_text()
    assert {a["completeness"] for a in index["artifacts"]} == {
        "complete",
        "partial",
        "unavailable",
    }
    graph = _json(
        run
        / next(a["graph_ref"] for a in index["artifacts"] if a["name"] == "Selected")
    )
    assert any(r.get("fallback") is True for r in graph["resources"].values())
    assert any(
        n["kind"] == "processing" and n["implementation"] is None
        for n in graph["nodes"]
    )


def test_synthetic_fixture_regenerates_identically(tmp_path: Path) -> None:
    script = FIXTURES.parent / "scripts/make_synthetic_bundle.py"
    spec = importlib.util.spec_from_file_location("make_synthetic_bundle", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main(tmp_path / "bundle")
    note = _json(FIXTURES / "synthetic-fallback/run-index.json")["run"][
        "synthetic_note"
    ]
    normalise(tmp_path / "bundle", tmp_path / "out", synthetic=note)
    for f in (FIXTURES / "synthetic-fallback").rglob("*.json"):
        rel = f.relative_to(FIXTURES / "synthetic-fallback")
        if rel.name == "fixture-provenance.json":
            continue  # carries the bundle label and measurements
        assert (tmp_path / "out" / rel).read_text() == f.read_text(), rel


def test_zmumu_node_resolves_through_the_plan_and_plot_has_its_path() -> None:
    run = FIXTURES / "zmumu"
    index = _json(run / "run-index.json")
    hist = next(a for a in index["artifacts"] if a["kind"] == "histogram")
    assert hist["preview_path"] == "artifacts/plots/DiMuonMass.png"
    details = _json(run / hist["details_ref"])["nodes"]["stage.BasicVars"]
    assert details["resolved"]["impl"] == "hep.define"
    assert details["resolved"]["inputs"][0]["node_id"] == "read.events"
    assert details["operations"] is None  # not recorded at run time for this run


def test_execution_count_is_recorded_or_absent_never_zero() -> None:
    chip = FIXTURES / "chip-large-sample"
    ref = _json(chip / "run-index.json")["artifacts"][0]["details_ref"]
    counts = [n["execution_count"] for n in _json(chip / ref)["nodes"].values()]
    assert 1 in counts  # nodes that ran in the one recorded partition
    assert 0 not in counts  # a run that recorded nothing is null, not 0
    zmumu = FIXTURES / "zmumu"
    zref = next(
        a["details_ref"]
        for a in _json(zmumu / "run-index.json")["artifacts"]
        if "details_ref" in a
    )
    assert all(
        n["execution_count"] is None for n in _json(zmumu / zref)["nodes"].values()
    )


def test_runs_json_lists_exactly_the_fixture_runs() -> None:
    runs = _json(FIXTURES / "runs.json")
    assert runs["schema_version"] == 1
    assert sorted(r["id"] for r in runs["runs"]) == sorted(p.name for p in RUNS)
