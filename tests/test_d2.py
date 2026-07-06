from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fasthep_toolbench.command import CommandResult
from hepflow.build_layout import BuildPaths

from fasthep_render import compile_hooks
from fasthep_render.api import render_path, render_spec_file
from fasthep_render.model import RenderStatus
from fasthep_render.renderers import d2


def test_render_spec_file_renders_d2_product(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = tmp_path / "render_d2.yaml"
    graph = tmp_path / "graph.d2"
    out = tmp_path / "graph.png"
    graph.write_text('"a" -> "b"\n', encoding="utf-8")
    spec.write_text(
        "\n".join(
            [
                "impl: d2",
                "spec:",
                "  op: d2",
                "",
            ]
        ),
        encoding="utf-8",
    )
    calls: list[tuple[str, list[str]]] = []

    def fake_run(tool: str, args: list[str]) -> CommandResult:
        calls.append((tool, args))
        out.write_bytes(b"png")
        return CommandResult(command=["d2", *args], exit_code=0, stdout="", stderr="")

    monkeypatch.setattr(d2, "run_registered_tool", fake_run)

    outcome = render_spec_file(spec, products={"d2": graph}, out=out)

    assert outcome.status == RenderStatus.RENDERED
    assert out.read_bytes() == b"png"
    assert calls == [
        (
            "d2",
            [str(graph), str(out)],
        )
    ]


def test_d2_renderer_infers_format_from_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = tmp_path / "graph.d2"
    out = tmp_path / "graph.svg"
    graph.write_text('"a" -> "b"\n', encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(tool: str, args: list[str]) -> CommandResult:
        assert tool == "d2"
        calls.append(args)
        return CommandResult(command=["d2", *args], exit_code=0, stdout="", stderr="")

    monkeypatch.setattr(d2, "run_registered_tool", fake_run)

    outcome = d2.render_d2(
        product={"d2": graph.read_text(encoding="utf-8")},
        common=d2.RenderCommonSpec(),
        params=d2.D2RenderParams(),
        ctx={"product_paths": {"d2": graph}, "output_path": str(out)},
    )

    assert outcome.status == RenderStatus.RENDERED
    assert calls == [[str(graph), str(out)]]


def test_render_path_uses_d2_renderer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = tmp_path / "graph.d2"
    out = tmp_path / "graph.png"
    graph.write_text('"a" -> "b"\n', encoding="utf-8")
    calls: list[tuple[str, list[str]]] = []

    def fake_run(tool: str, args: list[str]) -> CommandResult:
        calls.append((tool, args))
        return CommandResult(command=["d2", *args], exit_code=0, stdout="", stderr="")

    monkeypatch.setattr(d2, "run_registered_tool", fake_run)

    outcome = render_path("d2", graph, out)

    assert outcome.spec_path is None
    assert outcome.status == RenderStatus.RENDERED
    assert calls == [("d2", [str(graph), str(out)])]


def test_d2_renderer_skips_when_executable_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = tmp_path / "graph.d2"
    out = tmp_path / "graph.png"
    graph.write_text('"a" -> "b"\n', encoding="utf-8")

    def fake_run(tool: str, args: list[str]) -> CommandResult:
        return CommandResult(
            command=[tool, *args],
            exit_code=127,
            stdout="",
            stderr="Command not found: d2",
        )

    monkeypatch.setattr(d2, "run_registered_tool", fake_run)

    outcome = d2.render_d2(
        product={"d2": graph.read_text(encoding="utf-8")},
        common=d2.RenderCommonSpec(),
        params=d2.D2RenderParams(format="png"),
        ctx={"product_paths": {"d2": graph}, "output_path": str(out)},
    )

    assert outcome.status == RenderStatus.SKIPPED
    assert outcome.message == "Command not found: d2"


def test_graph_d2_compile_hook_requests_shared_renderer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph_dir = tmp_path / "graph"
    graph_dir.mkdir()
    (graph_dir / "graph.d2").write_text('"a" -> "b"\n', encoding="utf-8")
    (tmp_path / "compile").mkdir()
    (tmp_path / "compile" / "plan.yaml").write_text("nodes: []\n", encoding="utf-8")
    seen: dict[str, Any] = {}

    class Ctx:
        build_paths = BuildPaths(root=tmp_path)

    class Outcome:
        def __init__(self) -> None:
            self.status = RenderStatus.RENDERED
            self.message = None
            self.output_path = graph_dir / "graph.png"
            self.meta = {"renderer": "d2"}

    def fake_render_path(*args: Any, **kwargs: Any) -> Outcome:
        seen["args"] = args
        seen["kwargs"] = kwargs
        return Outcome()

    monkeypatch.setattr(compile_hooks, "render_path", fake_render_path)

    result = compile_hooks.render_graph_d2_hook(Ctx())

    assert seen["args"] == ("d2", graph_dir / "graph.d2", graph_dir / "graph.png")
    assert seen["kwargs"]["plan_path"] == tmp_path / "compile" / "plan.yaml"
    assert result["graph_render"]["status"] == "rendered"
    assert not (tmp_path / "render" / "specs" / "graph_d2.yaml").exists()
