# Detector-mapping alignment

Plans in this module provide support for detector-mapping alignment on reflectometers.

Plans in this module expect:
- A DAE collecting in period-per-point mode. A suitable controller is 
{py:obj}`ibex_bluesky_core.devices.simpledae.controllers.PeriodPerPointController`.
- A DAE configured to reduce data by exposing all spectrum integrals. A suitable reducer is 
{py:obj}`ibex_bluesky_core.devices.simpledae.reducers.PeriodSpecIntegralsReducer`.
- An angle map, as a `numpy` array of type `float64`, which has the same dimensionality as the set of selected detectors. This
maps each configured detector pixel to its angular position.

## Angle scan

API reference: {py:obj}`ibex_bluesky_core.plans.reflectometry.det_map_align.angle_scan_plan`

This plan takes a single DAE measurement, without moving anything.

The resulting plots & data files describe the relationship between angular position of each detector pixel,
and the counts observed on that detector pixel.

This plan returns the result of the angle fit, or `None` if the fit failed.

## Height & angle scan

API reference: {py:obj}`ibex_bluesky_core.plans.reflectometry.det_map_align.height_and_angle_scan_plan`

This plan scans over a provided height axis, taking a DAE measurement at each point. It then
does simultaneous height & angle fits, using a single set of measurements - avoiding the need
to scan height and angle separately.

It is assumed that optimum angle does not depend on height. The result of the angle scan
returned by this plan is meaningless if this assumption is untrue. This may be verified 
visually using the generated heatmap, or by multiple invocations of `angle_scan` at different 
height settings - the optimum angle should not vary with height.

This plan produces multiple plots & data files from a single scan:
- A heatmap visualising the 2-dimensional relationship between angle (x axis), height (y axis), and measured
intensity (heatmap colour).
- A set of plots & data files describing the relationship between integrated intensity (across 
every configured detector pixel, normalized by monitor), versus height.
- A set of plots & data files describing the relationship of accumulated counts on each detector pixel,
across all height points, versus angular pixel position. The only difference between this and the `angle_scan`
plan above is that this accumulates data across multiple height points, and therefore benefits from the
counting statistics of all measured height points.

This plan returns a dictionary with the following keys:
- `"angle_fit"`: the result of the angle fit, or `None` if the fit failed.
- `"height_fit"`: the result of the height fit, or `None` if the fit failed.
