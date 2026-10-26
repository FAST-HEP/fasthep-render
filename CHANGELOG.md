# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project uses
calendar versioning (`YYYY.MM.N`) rather than semantic versioning.

Add new entries under `## [Unreleased]`, in the category they belong to. At release time, rename
`## [Unreleased]` to `## [<version>] - <YYYY-MM-DD>` and start a fresh `## [Unreleased]` above it.

## [Unreleased]

### Added

- Allowed `hist1d` plots to have optional data (no data overlay required).

## [2026.08.1] - 2026-08-19

### Added

- Added a D2-based graph renderer and compile hook for rendering compiled graphs as diagrams.
- Added a schema comparison report, built on general input products.
- Added support for Flow's variation syntax in render operations.
- Added an area-normalisation option to comparison plots.

### Changed

- Moved the render model, types, and registry from `fasthep-flow` into `fasthep-render`.
- Improved the provenance report template.
- Render operations now skip inactive inputs instead of processing them.
- Reorganised the internal module layout for easier navigation.
- Renamed "author" terminology to "workflow" throughout, aligning with the published talk and
  paper.

### Fixed

- D2 compile graphs now render as SVG by default, giving better text boundaries.
