# `ibex_bluesky_core` documentation

Welcome to ibex_bluesky_core's documentation!

`ibex_bluesky_core` is a library of common `bluesky` functionality and `ophyd-async`
devices for use on the ISIS neutron & muon source's beamlines.

[Bluesky](https://blueskyproject.io/bluesky/main/index.html) is a generic data acquisition
framework, which started at NSLS-ii but is developed as a multi-facility collaboration. Bluesky
provides concepts such as "scanning" in a generic way.

[ophyd-async](https://blueskyproject.io/ophyd-async/main/index.html) is a python device
abstraction library, which allows bluesky to communicate with an underlying control system
(EPICS/IBEX, in our case).

`ibex_bluesky_core` provides:

- Central configuration for core bluesky classes, such as the {external+bluesky:py:obj}`RunEngine <bluesky.run_engine.RunEngine>`.
- {external+bluesky:py:obj}`RunEngine <bluesky.run_engine.RunEngine>` Callbacks customized for use at ISIS: file writing, plotting, fitting, ...
- Central implementations of ISIS device classes using `ophyd-async`: Blocks, DAE, ...
- Bluesky or scanning-related utilities which are useful across multiple beamlines.


```{toctree}
:maxdepth: 2
:caption: Getting started
:glob:

tutorial/overview.md
```

```{toctree}
:maxdepth: 2
:caption: Devices
:glob:

devices/*
```

```{toctree}
:maxdepth: 2
:caption: Callbacks
:glob:

callbacks/isiscallbacks
callbacks/fitting
callbacks/centre_of_mass
callbacks/plotting
callbacks/file_writing
```

```{toctree}
:maxdepth: 2
:caption: Plans
:glob:

plans/plans
plans/reflectometry
```

```{toctree}
:maxdepth: 2
:caption: Plan stubs
:glob:

plan_stubs/*
```
 
```{toctree}
:titlesonly:
:caption: Reference

_api
replotting_scans
architectural_decisions
developer_information
```
