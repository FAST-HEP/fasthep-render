# fasthep-render Agent Instructions

`fasthep-render` provides rendering sinks, reports, styles, and graph
visualisation for FAST-HEP workflows. These instructions are repository-local
and should remain valid when this repository is cloned independently.

## Ownership

This repository owns:

- plot and report rendering for FAST-HEP products;
- rendering style models and style resolution;
- graph visualisation, including D2 source rendering when the external tool is
  available;
- render operations, Flow-facing sink specs, compile hooks, and declared output
  artifacts;
- machine-readable rendered outputs where implemented, such as cutflow CSV.

This repository does not own:

- histogram filling, cutflow production, selections, event processing, or
  analysis-product construction; those belong in `fasthep-carpenter`;
- plans, lifecycle semantics, artifact-claim contracts, hook contracts, or
  runtime orchestration; those belong in `fasthep-flow`;
- metadata, schema snapshots, diagnostics, or provenance capture; those belong
  in `fasthep-curator`;
- project-level documentation or tutorials; those belong in `fast-hep.github.io`
  and `fasthep-workshop`.

Renderers should consume finalized or reduced products at the correct lifecycle
scope. Do not duplicate analysis logic merely to make a plot easier to draw.

## Important Locations

- `src/fasthep_render/api.py` - public standalone and Flow-facing render API.
- `src/fasthep_render/model.py` - render outcomes, artifacts, axes, figure,
  legend, style, dataset-style, and renderer parameter models.
- `src/fasthep_render/render_types.py` - renderer contract types:
  parse, validate, and input resolution.
- `src/fasthep_render/registry.py` - package-local renderer registry for
  standalone and nested renderer dispatch.
- `src/fasthep_render/profiles/registry.yaml` - Flow registry entries for
  render sinks, graph compile hooks, report templates, and internal renderers.
- `src/fasthep_render/hist/` - histogram plot renderers and render-side
  projection/comparison helpers.
- `src/fasthep_render/tables/cutflow_csv.py` - cutflow CSV renderer.
- `src/fasthep_render/reports/` - report and schema-validation renderers.
- `src/fasthep_render/templates/reports/` - bundled Jinja report templates.
- `src/fasthep_render/graph/` - D2 graph renderer and graph compile hook.
- `tests/test_hist1d.py`, `tests/test_data_mc.py`, `tests/test_heatmap2d.py`,
  `tests/test_projection.py`, and `tests/test_comparison.py` - plot renderer
  tests.
- `tests/test_cutflow_csv.py` - machine-readable table output tests.
- `tests/test_report_template.py` and `tests/test_schema_validation_report.py`
  - report renderer tests.
- `tests/test_d2.py` - graph renderer and compile-hook behaviour.
- `tests/test_registry_profile.py`, `tests/test_imports_and_profile.py`, and
  `tests/test_flow_integration.py` - registry/profile and Flow integration.

`pixi.toml` defines a Sphinx `docs` task, but this repository currently has no
`docs/` source tree.

## Commands

Install and run tasks from the repository root:

```bash
pixi install
pixi run format
pixi run lint
pixi run lint-fix
pixi run typecheck
pixi run test
pixi run build
pixi run check
pixi run ci
pixi run check-dist
pixi run docs
pixi run docs-clean
```

`check` runs `lint`, `typecheck`, and `test`. `ci` runs `check` and `build`.
Build before `check-dist` so `dist/*` exists. `docs` expects a `docs/` tree
before it can succeed. The Pixi environments include `py311`, `py313`, `py314`,
and `docs`; use the default environment unless a compatibility check needs a
specific Python version.

## Renderer Contracts

- Use public Flow extension contracts: registry profiles, sink specs, compile
  hooks, and `OutputResult`. Package code should not import compiler internals.
- Keep output naming deterministic and expose static output claims to Flow
  through sink specs or hook result metadata.
- Never rely on silent last-write-wins behaviour. If multiple outputs are
  possible, make paths or output directories explicit and deterministic.
- Preserve input products during rendering. Render transforms may copy or derive
  display-only products, but should not mutate stored histograms, cutflows, or
  metadata.
- Handle optional axes, categories, ratio panels, dataset roles, and projection
  choices through explicit renderer contracts and validation.
- Keep styles separate from analysis semantics. Labels, colours, experiment
  marks, layout, and presentation hints must not change scientific selections,
  weights, or category definitions.
- Close plotting resources and keep Matplotlib execution headless-friendly.
  Tests set non-interactive backends where needed.
- Source graph formats such as `.d2` should remain useful even when optional
  external rendering tools are unavailable.

## Optional Tools

Graph SVG/PNG rendering uses the external `d2` command through
`fasthep-toolbench`. When `d2` is unavailable, the D2 renderer records a skipped
render outcome instead of making graph source generation unusable. Tests should
mock tool execution rather than requiring `d2` to be installed.

## Generated Files and Care Areas

- `src/fasthep_render/_version.py` is generated by Hatch/Hatch-VCS. Do not edit
  it by hand; keep `src/fasthep_render/_version.pyi` aligned with imports.
- Plot files, graph SVGs, report outputs, cutflow CSVs, distribution artifacts,
  and documentation builds are generated outputs. Do not check them in unless
  they are deliberate fixtures.
- Edit renderer code, templates, profiles, or source documentation rather than
  generated outputs.

## Focused Testing

- Public render API and standalone spec execution:
  `pixi run pytest tests/test_api.py`.
- Histogram renderers, projection, comparison, and style behaviour:
  `pixi run pytest tests/test_hist1d.py tests/test_data_mc.py tests/test_heatmap2d.py tests/test_projection.py tests/test_comparison.py`.
- Cutflow CSV:
  `pixi run pytest tests/test_cutflow_csv.py`.
- Report rendering:
  `pixi run pytest tests/test_report_template.py tests/test_schema_validation_report.py`.
- Graph rendering and compile hooks:
  `pixi run pytest tests/test_d2.py`.
- Registry/profile and Flow integration:
  `pixi run pytest tests/test_registry_profile.py tests/test_imports_and_profile.py tests/test_flow_integration.py`.

Prefer structural assertions on files, metadata, registry entries, and rendered
output manifests. Avoid brittle pixel comparisons unless a visual regression
test is intentional and documented.
