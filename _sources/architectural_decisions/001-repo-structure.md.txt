# 1. Repository structure

## Status

Current, partially superseded by [ADR 6](006-where-to-put-code.md)

## Context

We need to decide how to structure our bluesky and scans code, in 
terms of technical repository layout.

## Present

Tom & Kathryn

## Decision

We will create a `core` repository, called `ibex_bluesky_core`, and publish it on PyPI.

This repository will provide core building blocks, including plan stubs,
devices, and utilities which are generic and expected to be useful across
different science groups.

~~Beamline or technique specific repositories will then depend on the `core` repository via PyPI.~~
Superseded by [ADR 6](006-where-to-put-code.md).

The core repository will not depend on [`genie_python`](https://github.com/isiscomputinggroup/genie), so that other
groups at RAL can use this repository. The [uktena](https://github.com/isiscomputinggroup/uktena) python *distribution* 
includes this repository as one of its included libraries.

This `ibex_bluesky_core` repository is analogous to a similar repo, 
[dodal](https://github.com/diamondlightsource/dodal), being used at Diamond Light Source, or
[apstools](https://github.com/BCDA-APS/apstools), being used at the Advanced Photon Source.

## Consequences

- We will have some bluesky code across multiple locations.
- Other groups should be able to:
  - Pull this code easily from PyPI
  - Contribute to the code without depending on all of IBEX's infrastructure
- We have a comparable repository setup to other facilities on site who use bluesky
- The setup will be less "standard" from an IBEX perspective.
