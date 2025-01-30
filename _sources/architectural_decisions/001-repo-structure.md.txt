# Repository structure

## Status

Current

## Context

We need to decide how to structure our bluesky and scans code, in 
terms of technical repository layout.

## Present

Tom & Kathryn

## Decision

We will create a `core` repository, and publish it on PyPI.

This repository will provide core building blocks, including plan stubs,
devices, and utilities which are generic and expected to be useful across
different science groups.

Beamline or technique specific repositories will then depend on the `core`
repository via PyPI.

The core repository will not depend on `genie_python`, so that other groups
at RAL can use this repository. The genie python *distribution* may in future
depend on this repository.

This `core` repository is analogous to a similar repo, `dodal`, being used at
Diamond.

## Consequences

- We will have some bluesky code across multiple repositories.
- Other groups should be able to:
  - Pull this code easily from PyPI
  - Contribute to the code without depending on all of IBEX's infrastructure
- We have a comparable repository setup to other facilities on site who use bluesky
- The setup will be less "standard" from an IBEX perspective.
