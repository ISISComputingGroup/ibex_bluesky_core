# ISIS Standard Callbacks ({py:obj}`ISISCallbacks <ibex_bluesky_core.callbacks.ISISCallbacks>`)

{py:obj}`ISISCallbacks <ibex_bluesky_core.callbacks.ISISCallbacks>` is a helper to add common callbacks to 1-dimensional scans with a single dependent variable with an optional uncertainty and a single independent variable. 

It is composed from the following callbacks:
- {py:obj}`ibex_bluesky_core.callbacks.LiveFit`
- {py:obj}`ibex_bluesky_core.callbacks.LivePlot`
- {external+bluesky:py:obj}`bluesky.callbacks.mpl_plotting.LiveFitPlot`
- {py:obj}`ibex_bluesky_core.callbacks.CentreOfMass`
- {py:obj}`ibex_bluesky_core.callbacks.PlotPNGSaver`
- {py:obj}`ibex_bluesky_core.callbacks.LiveFitLogger`
- {py:obj}`ibex_bluesky_core.callbacks.HumanReadableFileCallback`