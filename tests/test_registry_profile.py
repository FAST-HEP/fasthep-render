from __future__ import annotations

from hepflow.compiler.profiles import load_profile_config
from hepflow.registry.loaders import load_object

from fasthep_render.registry import resolve_render_registry


def test_registry_profile_loads_render_sink_specs_and_impls(tmp_path) -> None:
    cfg = load_profile_config("fasthep_render:registry", project_root=tmp_path)
    sinks = cfg["registry"]["sinks"]

    expected = {
        "hep.render.hist1d",
        "hep.render.data_mc",
        "hep.render.heatmap2d",
        "hep.render.project",
        "hep.render.comparison",
        "hep.render.cutflow_csv",
    }

    assert expected <= set(sinks)
    assert cfg["registry"]["render"]["d2"] == {
        "spec": "fasthep_render.renderers.d2:D2_RENDER_TYPE",
        "impl": "fasthep_render.renderers.d2:render_d2",
    }
    assert cfg["registry"]["compile_hooks"]["fasthep.render.graph_d2"] == {
        "spec": "fasthep_render.compile_hooks:GRAPH_D2_RENDER_HOOK_SPEC",
        "impl": "fasthep_render.compile_hooks:render_graph_d2_hook",
    }

    for name in expected:
        sink_spec = load_object(sinks[name]["spec"])
        sink_impl = load_object(sinks[name]["impl"])

        assert sink_spec["kind"] == "sink"
        assert callable(sink_impl)


def test_render_registry_is_render_package_local() -> None:
    registry = resolve_render_registry()

    assert "hep.render.hist1d" in registry.renderers
    assert "d2" in registry.renderers
    assert callable(registry.renderers["hep.render.hist1d"].spec.parse_params)
    assert callable(registry.renderers["hep.render.hist1d"].handler)
