from __future__ import annotations

from hepflow.compiler.profiles import load_profile_config
from hepflow.registry.loaders import load_object


def test_registry_profile_loads_render_sink_specs_and_impls(tmp_path) -> None:
    cfg = load_profile_config("fasthep_render:registry", project_root=tmp_path)
    sinks = cfg["registry"]["sinks"]
    renderers = cfg["registry"]["renderers"]

    expected = {
        "hep.render.hist1d",
        "hep.render.data_mc",
        "hep.render.heatmap2d",
        "hep.render.project",
        "hep.render.comparison",
        "hep.render.cutflow_csv",
    }

    assert expected <= set(sinks)
    assert expected <= set(renderers)

    for name in expected:
        sink_spec = load_object(sinks[name]["spec"])
        sink_impl = load_object(sinks[name]["impl"])
        renderer_spec = load_object(renderers[name]["spec"])
        renderer_impl = load_object(renderers[name]["impl"])

        assert sink_spec["kind"] == "sink"
        assert callable(sink_impl)
        assert callable(renderer_spec.parse_params)
        assert callable(renderer_impl)
