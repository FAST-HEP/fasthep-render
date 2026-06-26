from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any

from fasthep_render.render_types import RenderEntry, RenderTypeSpec

_BUILTIN_RENDERERS: dict[str, dict[str, str]] = {
    "hep.render.hist1d": {
        "spec": "fasthep_render.renderers.hist1d:HIST1D_RENDER_TYPE",
        "impl": "fasthep_render.renderers.hist1d:render_hist1d",
    },
    "hep.render.data_mc": {
        "spec": "fasthep_render.renderers.data_mc:DATA_MC_RENDER_TYPE",
        "impl": "fasthep_render.renderers.data_mc:render_data_mc",
    },
    "hep.render.heatmap2d": {
        "spec": "fasthep_render.renderers.heatmap2d:HEATMAP2D_RENDER_TYPE",
        "impl": "fasthep_render.renderers.heatmap2d:render_heatmap2d",
    },
    "hep.render.project": {
        "spec": "fasthep_render.renderers.project:PROJECT_RENDER_TYPE",
        "impl": "fasthep_render.renderers.project:render_project_then",
    },
    "hep.render.comparison": {
        "spec": "fasthep_render.renderers.comparison:COMPARISON_RENDER_TYPE",
        "impl": "fasthep_render.renderers.comparison:render_comparison",
    },
    "hep.render.cutflow_csv": {
        "spec": "fasthep_render.renderers.cutflow:CUTFLOW_CSV_RENDER_TYPE",
        "impl": "fasthep_render.renderers.cutflow:render_cutflow_csv",
    },
}


@dataclass(frozen=True)
class RenderRegistry:
    """
    Render-package-local registry for renderer-internal dispatch.

    Flow treats rendering as ordinary sink-component execution. This registry is
    intentionally private to ``fasthep-render`` and exists for APIs such as
    standalone render-spec execution and project/downstream rendering.
    """

    renderers: dict[str, RenderEntry] = field(default_factory=dict)


def resolve_render_registry(
    registry_cfg: dict[str, Any] | None = None,
) -> RenderRegistry:
    entries = dict(_BUILTIN_RENDERERS)
    extra = dict((registry_cfg or {}).get("renderers") or {})
    entries.update(extra)
    return RenderRegistry(
        renderers={name: _load_render_entry(name, entry) for name, entry in entries.items()}
    )


def _load_render_entry(name: str, entry_cfg: dict[str, Any]) -> RenderEntry:
    if not isinstance(entry_cfg, dict):
        raise TypeError(
            f"Renderer registry entry '{name}' must be a mapping with 'spec' and 'impl'"
        )

    spec_obj = _load_object(entry_cfg["spec"])
    impl_obj = _load_object(entry_cfg["impl"])

    if not isinstance(spec_obj, RenderTypeSpec):
        raise TypeError(f"Renderer spec '{name}' did not resolve to RenderTypeSpec")
    if not callable(impl_obj):
        raise TypeError(f"Renderer impl '{name}' did not resolve to a callable")

    return RenderEntry(spec=spec_obj, handler=impl_obj)


def _load_object(spec: str) -> Any:
    if not isinstance(spec, str) or ":" not in spec:
        raise ValueError(
            f"Invalid object spec '{spec}'. Expected format 'module.submodule:object'"
        )
    mod_name, obj_name = spec.split(":", 1)
    mod = importlib.import_module(mod_name)
    try:
        return getattr(mod, obj_name)
    except AttributeError as exc:
        raise AttributeError(
            f"Module '{mod_name}' has no attribute '{obj_name}'"
        ) from exc
