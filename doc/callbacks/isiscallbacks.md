{#icc}
# ISIS Standard Callbacks ({py:obj}`~ibex_bluesky_core.callbacks.ISISCallbacks`)

{py:obj}`~ibex_bluesky_core.callbacks.ISISCallbacks` is a helper to add common callbacks to 1-dimensional scans with a single dependent variable (with an optional uncertainty) and a single independent variable.  This should avoid some repetition as you don't need to pass `x` and `y` to each callback.

It is composed of the following callbacks:
- {py:obj}`ibex_bluesky_core.callbacks.LiveFit`
- {py:obj}`ibex_bluesky_core.callbacks.LivePlot`
- {external+bluesky:py:obj}`bluesky.callbacks.LiveTable`
- {external+bluesky:py:obj}`bluesky.callbacks.fitting.PeakStats`
- {external+bluesky:py:obj}`bluesky.callbacks.mpl_plotting.LiveFitPlot`
- {py:obj}`ibex_bluesky_core.callbacks.CentreOfMass`
- {py:obj}`ibex_bluesky_core.callbacks.PlotPNGSaver`
- {py:obj}`ibex_bluesky_core.callbacks.LiveFitLogger`
- {py:obj}`ibex_bluesky_core.callbacks.HumanReadableFileCallback`

## Live table

A {external+bluesky:py:obj}`~bluesky.callbacks.LiveTable` is enabled by default. This will show the values of X and Y according to their `seq_num` or event order.

You can pass optional fields to be displayed in the LiveTable with the `fields_for_live_table` argument or the `measured_fields` argument if you want the fields to be put in the human-readable file (see {ref}`below. <hr_files_icc>`)

## Plotting

Plotting is enabled by default and running a plan with {py:obj}`~ibex_bluesky_core.callbacks.ISISCallbacks` will close any current active plots.

## Fitting

If a {ref}`fitting method <standard_fitting_models>` is given via the `fit` argument (this is optional), fitting will be enabled. By default, this fit will be shown on a plot.

After a scan has run you can get the fitting results by using the {py:obj}`~ibex_bluesky_core.callbacks.ISISCallbacks.live_fit` property. 

## Centre of mass and Peak Stats

These are both enabled by default. To access {py:obj}`~ibex_bluesky_core.callbacks.CentreOfMass` information after a plan, use the {py:obj}`~ibex_bluesky_core.callbacks.ISISCallbacks.com` property.

To access {external+bluesky:py:obj}`~bluesky.callbacks.fitting.PeakStats` after a plan, use the {py:obj}`~ibex_bluesky_core.callbacks.ISISCallbacks.peak_stats` property.

## File output

### Fit output

These are enabled by default when a fit method is given. See {ref}`livefit_logger` for more information.

{#hr_files_icc}
### Human readable files

These are enabled by default and are appended to throughout a bluesky run. See {ref}`hr_file_cb` for more information.

### Plot PNGs

These are enabled by default. They are saved on the end of a bluesky run. See {ref}`plot_png_saver` for more information. 

### Raw Bluesky Events

These are enabled, but not by {py:obj}`ISISCallbacks <ibex_bluesky_core.callbacks.ISISCallbacks>`. See {ref}`event_doc_cb` for more information.

## Accessing callbacks directly

A list of callbacks used by the current instance can be obtained through the {py:obj}`subs <ibex_bluesky_core.callbacks.ISISCallbacks.subs>` property. 
