from __future__ import annotations

import importlib.resources as resources

from hepflow.compiler.profiles import load_profile_config
from hepflow.registry.loaders import load_object

import fasthep_render


def test_import_package() -> None:
    assert fasthep_render is not None


def test_load_registry_profile_resource() -> None:
    text = (
        resources.files("fasthep_render.profiles")
        .joinpath("registry.yaml")
        .read_text(encoding="utf-8")
    )

    assert "hep.render.hist1d" in text
    assert "fasthep_render.sinks.hist1d:run_hist1d_render" in text


def test_load_render_specs_and_impls() -> None:
    refs = [
        (
            "fasthep_render.sinks.hist1d:HIST1D_RENDER_SPEC",
            "fasthep_render.sinks.hist1d:run_hist1d_render",
        ),
        (
            "fasthep_render.sinks.data_mc:DATA_MC_RENDER_SPEC",
            "fasthep_render.sinks.data_mc:run_data_mc_render",
        ),
        (
            "fasthep_render.sinks.heatmap2d:HEATMAP2D_RENDER_SPEC",
            "fasthep_render.sinks.heatmap2d:run_heatmap2d_render",
        ),
        (
            "fasthep_render.sinks.project:PROJECT_RENDER_SPEC",
            "fasthep_render.sinks.project:run_project_render",
        ),
        (
            "fasthep_render.sinks.comparison:COMPARISON_RENDER_SPEC",
            "fasthep_render.sinks.comparison:run_comparison_render",
        ),
        (
            "fasthep_render.sinks.cutflow_csv:CUTFLOW_CSV_RENDER_SPEC",
            "fasthep_render.sinks.cutflow_csv:run_cutflow_csv_render",
        ),
    ]

    for spec_ref, impl_ref in refs:
        spec = load_object(spec_ref)
        impl = load_object(impl_ref)
        assert spec["kind"] == "sink"
        assert callable(impl)


def test_flow_loads_render_profile(tmp_path) -> None:
    cfg = load_profile_config("fasthep_render:registry", project_root=tmp_path)

    assert "hep.render.data_mc" in cfg["registry"]["sinks"]
    assert "hep.render.heatmap2d" in cfg["registry"]["sinks"]
    assert "hep.render.comparison" in cfg["registry"]["sinks"]
    assert "hep.render.cutflow_csv" in cfg["registry"]["sinks"]
    assert "hep.render.project" in cfg["registry"]["sinks"]
