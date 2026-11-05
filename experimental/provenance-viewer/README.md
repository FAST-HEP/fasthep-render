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
