# Reflectometry parameter scans

Specialised plans are provided in the `ibex_bluesky_core.plans.reflectometry` module, which wrap step scans and
adaptive scans over reflectometry parameters.

## `refl_scan`

API reference: {py:obj}`ibex_bluesky_core.plans.reflectometry.refl_scan`

This plan is similar to the general {py:obj}`scan<ibex_bluesky_core.plans.scan>` plan, but assumes that the single
parameter being scanned over is a reflectometry parameter.

The parameter is passed by name, rather than as a device. This is possible because logic detecting when a move is
complete is implemented in the reflectometry server. Therefore, no tolerances or wait times are necessary in the
bluesky layer.

## `refl_adaptive_scan`

API reference: {py:obj}`ibex_bluesky_core.plans.reflectometry.refl_adaptive_scan`

As above, but wrapping {py:obj}`scan<ibex_bluesky_core.plans.adaptive_scan>`, in order to perform a scan with dynamic
step size, stepping coarsely over regions with low change and finely over regions with high change.
