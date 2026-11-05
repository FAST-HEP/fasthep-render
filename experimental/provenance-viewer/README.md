# Provenance viewer (EXPERIMENTAL)

Exploratory prototype for visualising Flow provenance. No stability promise, not part of the
`fasthep-render` public API or wheel. Plan and findings live in the fasthep-dev workspace
(`tasks/2026-10-28-provenance-visualisation`).

- `fixtures/zmumu`: Z to mumu example, regenerated with flow 2026.11.1.
- `fixtures/chip-large-sample`: one small cutflow (18 ancestors) from the 1,425-node CHIP run.

Fixtures are generated, never edited by hand:

```bash
python -m fasthep_render.experimental.provenance.cli BUNDLE OUT [--only NAME]
```

`tests/experimental/test_provenance_fixtures.py` fails on machine-specific content, dangling references or
unlisted files.

## Run the viewer (M2)

Node comes from this folder's own `pixi.toml` (conda-forge `nodejs`):

```bash
cd experimental/provenance-viewer
pixi run install            # once
pixi run dev                # serves fixtures/ at http://localhost:5173
pixi run test               # view-model unit tests
VIEWER_DATA_DIR=/path/to/normalised pixi run dev   # local, gitignored large-case output
python scripts/make-runs-json.py /path/to/normalised   # list runs for VIEWER_DATA_DIR
```

URL is `#/<run>/<artifact>`. The status bar shows loaded bytes, layout time, first frame and long tasks;
`window.__viewerMetrics()` returns every measurement.

## Icons and licences

Icons come from [lucide-react](https://lucide.dev) (ISC licence, compatible with this repository's BSD
licence); `src/icons.ts` maps every kind of entity, artifact and state to one. The legend is the Help tab.
