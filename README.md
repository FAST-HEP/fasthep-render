# fasthep-render

[![CI](https://github.com/FAST-HEP/fasthep-render/actions/workflows/ci.yml/badge.svg)](https://github.com/FAST-HEP/fasthep-render/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/fasthep-render)](https://pypi.org/project/fasthep-render/)
[![Python Versions](https://img.shields.io/pypi/pyversions/fasthep-render)](https://pypi.org/project/fasthep-render/)
[![Documentation Status](https://readthedocs.org/projects/fasthep-render/badge/?version=latest)](https://fasthep-render.readthedocs.io/en/latest/)
[![Discussions](https://img.shields.io/static/v1?label=Discussions\&message=Ask\&color=blue\&logo=github)](https://github.com/FAST-HEP/fasthep/discussions)

<p align="center">
  <a href="https://github.com/FAST-HEP/fasthep">
    <picture>
      <source
        media="(prefers-color-scheme: dark)"
        srcset="https://raw.githubusercontent.com/FAST-HEP/logos-etc/master/fast-hep-white.png"
      >
      <source
        media="(prefers-color-scheme: light)"
        srcset="https://raw.githubusercontent.com/FAST-HEP/logos-etc/master/fast-hep-black.png"
      >
      <img
        alt="FAST-HEP"
        src="https://raw.githubusercontent.com/FAST-HEP/logos-etc/master/fast-hep-black.png"
        width="500"
      >
    </picture>
  </a>
</p>

`fasthep-render` provides plotting, table rendering, reporting, and visualization utilities for FAST-HEP workflows.

The Python import namespace is:

```python id="zlm9e4"
import fasthep_render
```

## Scope

`fasthep-render` is responsible for:

* histogram rendering
* cutflow tables
* report generation
* plotting backends
* rendering registries
* artifact formatting
* summary visualizations
* workflow diagnostics output

It is the presentation and reporting layer of the FAST-HEP ecosystem.

## Relationship to `fasthep-flow`

`fasthep-flow` provides:

* workflow compilation
* orchestration
* execution planning
* backend interfaces

`fasthep-render` provides:

* visualization
* report generation
* artifact formatting
* plotting implementations
* rendering specifications

In practice, most HEP users will use both packages together.

## Recommended companion packages

* `fasthep-flow`

  * workflow language and execution engine

* `fasthep-carpenter`

  * HEP analysis transforms
  * histogramming
  * event processing

* `fasthep-curator`

  * dataset inspection
  * validation
  * metadata generation

* `fasthep-cli`

  * the unified `fasthep` command-line interface

Alternatively, install the meta package:

```bash id="8w8c26"
pip install fasthep
```

## Installation

Install directly:

```bash id="51vrbp"
pip install fasthep-render
```

Development environment:

```bash id="1zwf1u"
pixi install
pixi run ci
```

## Minimal example

Example render specification:

```yaml id="n8d4uo"
render:
  NumberOfJets:
    renderer: histogram
    style:
      title: Jet multiplicity
      x_label: Number of jets
      y_label: Events
```

Example Python usage:

```python id="xskmwo"
from fasthep_render.api import render_artifact

render_artifact(
    artifact="results/NumberOfJets.pkl",
    spec="render_specs/render_NumberOfJets.yaml",
    output="results/NumberOfJets.png",
)
```

## Design principles

`fasthep-render` focuses on:

* declarative rendering
* reusable render specifications
* backend-independent visualization
* registry-driven extensibility
* reproducible reports
* publication-oriented outputs

The package intentionally separates rendering and presentation concerns from workflow execution and analysis logic.

## Documentation

Main FAST-HEP documentation:

* [https://fast-hep.github.io](https://fast-hep.github.io)

API documentation for this package:

* [https://fasthep-render.readthedocs.io/en/latest/](https://fasthep-render.readthedocs.io/en/latest/)

## Repository

Main FAST-HEP repository and project links:

* [https://github.com/FAST-HEP/fasthep](https://github.com/FAST-HEP/fasthep)

## Contributing

Contribution guidelines, development setup, and project-wide documentation are maintained centrally in the main FAST-HEP repository.

## Legacy branch

Earlier rendering implementations existed inside the monolithic prototype repositories.

The current repository contains the standalone split-package rendering layer.

## Status

FAST-HEP is currently in active pre-alpha development.

Interfaces may evolve rapidly while the package split and stabilization work continues.
