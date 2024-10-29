

Welcome to ibex_bluesky_core's documentation!
=============================================

``ibex_bluesky_core`` is a library of common ``bluesky`` functionality and ``ophyd-async``
devices for use on the ISIS neutron & muon source's beamlines.

`Bluesky <https://blueskyproject.io/bluesky/main/index.html>`_ is a generic data acquisition
framework, which started at NSLS-ii but is developed as a multi-facility collaboration. Bluesky
provides concepts such as "scanning" in a generic way.

`ophyd-async <https://blueskyproject.io/ophyd-async/main/index.html>`_ is a python device
abstraction library, which allows bluesky to communicate with an underlying control system
(EPICS/IBEX, in our case).

``ibex_bluesky_core`` provides:

- Central configuration for core bluesky classes, such as the ``RunEngine``.
- ``RunEngine`` Callbacks customized for use at ISIS: file writing, plotting, fitting, ...
- Central implementations of ISIS device classes using ``ophyd-async``: Blocks, DAE, ...
- Bluesky or scanning-related utilities which are useful across multiple beamlines.


Overview
========

.. note::

    bluesky is a very flexible data acquisition framework. The following example illustrates a minimal scan,
    not the full extent of bluesky's functionality.

Using ``ibex_bluesky_core``, one can define some simple instrument-specific devices::

    from ibex_bluesky_core.devices.block import block_r, block_mot

    mot = block_mot("mot")  # An IBEX block pointing at a motor
    det = block_r(float, "p5")  # A readback block

And define a simple step-scan which uses those devices::

    import bluesky.plans as bp
    from ophyd_async.plan_stubs import ensure_connected

    def my_plan(start: float, stop: float, num: int):
        yield from ensure_connected(det, mot, force_reconnect=True)
        yield from bp.scan([det], mot, start, stop, num)

After which, a simple scan can be run by a user::

    from ibex_bluesky_core.run_engine import get_run_engine

    # A bluesky RunEngine instance, already available if using IBEX GUI
    RE = get_run_engine()

    # Scan "mot" from 0 to 10 in 5 steps, reading "my_detector" at each step.
    RE(my_plan(0, 10, 5))

That plan may then also use:

- Other `experimental plans <https://blueskyproject.io/bluesky/main/plans.html#summary>`_ or
  `plan stubs <https://blueskyproject.io/bluesky/main/plans.html#stub-plans>`_, to build up more complex
  plans.
- `Callbacks <https://blueskyproject.io/bluesky/main/callbacks.html>`_ provided by either
  ``ibex_bluesky_core`` or ``bluesky``, which do something with the results of the scan: live
  fitting, live plotting, file-writing, ...
- `Simulation facilities <https://blueskyproject.io/bluesky/main/simulation.html>`_ provided by
  bluesky, to check for problems before the plan is run
- And a range of other functionality!

See the `manual system tests <https://github.com/ISISComputingGroup/ibex_bluesky_core/tree/main/manual_system_tests>`_ for
some full runnable examples of complex plans, using a wider range of bluesky functionality.

The reference documentation below lists the functionality that has been implemented in ``ibex_bluesky_core``,
however the vast majority of `bluesky <https://blueskyproject.io/bluesky/main/index.html>`_ functionality remains
available, and the advanced user is also encouraged to read that documentation.

Reference documentation
=======================

.. toctree::
   :maxdepth: 2
   :caption: Devices
   :glob:
   
   devices/*

.. toctree::
   :maxdepth: 2
   :caption: Callbacks
   :glob:

   callbacks/*

.. toctree::
   :maxdepth: 2
   :caption: Fitting
   :glob:

   fitting/*

.. toctree::
   :maxdepth: 2
   :caption: Preprocessors
   :glob:

   preprocessors/*

.. toctree::
   :maxdepth: 2
   :caption: Developer information
   :glob:

   dev/*
   
.. toctree::
   :titlesonly:
   :caption: Architectural decisions
   :glob:
   :maxdepth: 1

   architectural_decisions/*

.. toctree::
   :titlesonly:
   :caption: API reference

   _api
