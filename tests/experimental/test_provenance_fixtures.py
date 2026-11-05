"""Guards for the checked-in viewer fixtures (leaks, integrity, determinism)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

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
    assert {p.name for p in RUNS} >= {"zmumu", "chip-large-sample"}


@pytest.mark.parametrize("run", RUNS, ids=lambda p: p.name)
def test_no_machine_specific_content(run: Path) -> None:
    for f in run.rglob("*"):
        if f.is_file():
            text = f.read_text()
            hits = [s for s in FORBIDDEN if s in text]
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
        expected |= {a.get("graph_ref"), a.get("details_ref")} - {None}
    found = {str(f.relative_to(run)) for f in run.rglob("*") if f.is_file()}
    assert found == expected


def test_runs_json_lists_exactly_the_fixture_runs() -> None:
    runs = _json(FIXTURES / "runs.json")
    assert runs["schema_version"] == 1
    assert sorted(r["id"] for r in runs["runs"]) == sorted(p.name for p in RUNS)
