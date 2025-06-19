# Plotting

## `LivePlot`

Bluesky has good integration with {py:obj}`matplotlib` for data visualization, and data from scans 
may be easily plotted using the {py:obj}`LivePlot<ibex_bluesky_core.callbacks.LivePlot>`  callback.

{py:obj}`ibex_bluesky_core` provides a thin wrapper over bluesky's default 
{py:obj}`LivePlot<bluesky.callbacks.mpl_plotting.LivePlot>` callback,
which ensures that plots are promptly displayed in IBEX.

In order to use the wrapper, import {py:obj}`LivePlot<ibex_bluesky_core.callbacks.LivePlot>` 
from {py:obj}`ibex_bluesky_core.callbacks` rather than importing
{py:obj}`bluesky.callbacks.mpl_plotting.LivePlot` directly:

```
from ibex_bluesky_core.callbacks.plotting import LivePlot
```

## Configuration

A range of configuration options for {py:obj}`LivePlot<ibex_bluesky_core.callbacks.LivePlot>` are available - see the 
[bluesky `LivePlot` documentation](https://blueskyproject.io/bluesky/main/callbacks.html#bluesky.callbacks.mpl_plotting.LivePlot)
for more details about available options.

The {py:obj}`LivePlot<ibex_bluesky_core.callbacks.LivePlot>` object allows an arbitrary set of matplotlib `Axes` to be passed in, onto
which it will plot. This can be used to configure properties which are not directly exposed
on the {py:obj}`LivePlot<ibex_bluesky_core.callbacks.LivePlot>` object, for example log-scaled axes.

See the [matplotlib `Axes` documentation](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.html) 
for a full range of options on how to configure an {py:obj}`Axes<matplotlib.axes.Axes>` object.

Below is a full example showing how to use standard {py:obj}`matplotlib` & {py:obj}`bluesky` functionality
to plot a scan with a logarithmically-scaled y-axis:

```python
import matplotlib.pyplot as plt
from ibex_bluesky_core.callbacks import LivePlot
from ibex_bluesky_core.plan_stubs import call_qt_aware

def plan():
    # Create a new figure to plot onto.
    yield from call_qt_aware(plt.figure)
    # Make a new set of axes on that figure
    ax = yield from call_qt_aware(plt.gca)
    # Set the y-scale to logarithmic
    yield from call_qt_aware(ax.set_yscale, "log")
    # Use the above axes in a LivePlot callback
    plot_callback = LivePlot(y="y_variable", x="x_variable", ax=ax, yerr="yerr_variable")
    # yerr is the uncertanties of each y value, producing error bars
```

```{note}
See [docs for `call_qt_aware`](../plan_stubs/matplotlib_helpers.md) for a description of why we need to use 
`yield from call_qt_aware` rather than calling `matplotlib` functions directly.
```

By providing a signal name to the `yerr` argument you can pass uncertainties to {py:obj}`LivePlot<ibex_bluesky_core.callbacks.LivePlot>`, by not providing anything for this argument means that no errorbars will be drawn. Errorbars are drawn after each point collected, displaying their standard deviation- uncertainty data is collected from Bluesky event documents and errorbars are updated after every new point added.

The `plot_callback` object can then be subscribed to the run engine, using either:
- An explicit callback when calling the run engine: `RE(some_plan(), plot_callback)`
- Be subscribed in a plan using {py:obj}`subs_decorator<bluesky.preprocessors.subs_decorator>` from bluesky **(recommended)**
- Globally attached to the run engine using {py:obj}`RE.subscribe<bluesky.run_engine.RunEngine.subscribe>`
  * Not recommended, not all scans will use the same variables and a plot setup that works
    for one scan is unlikely to be optimal for a different type of scan.

By subsequently re-using the same `ax` object in later scans, rather than creating a new 
`ax` object for each scan, two scans can be "overplotted" with each other for comparison.

## `LivePColorMesh`

{py:obj}`LivePColorMesh<ibex_bluesky_core.callbacks.LivePColorMesh>` is a specialized heatmap
plotting callback which reacts to *rows* of data at a time. This is suitable for use by DAE reducers
which emit rows of data at a time, such as 
{py:obj}`ibex_bluesky_core.devices.simpledae.PeriodSpecIntegralsReducer` or
{py:obj}`ibex_bluesky_core.devices.simpledae.DSpacingMappingReducer`.

This callback updates live as the scan progresses. It is otherwise very similar to the
existing bluesky plotting callbacks.

:::{note}
Due to an implementation detail of {py:obj}`matplotlib.pyplot.pcolormesh`,
the plot will only appear once at least *two* rows of data have been collected.
:::

## Saving plots to PNG files

`ibex_bluesky_core` provides a {py:obj}`PlotPNGSaver<ibex_bluesky_core.callbacks.PlotPNGSaver>` callback to save plots on a run stop to PNG files, which by saves them to the default output file location unless a filepath is explicitly given.

This is enabled by default in the {py:obj}`ISISCallbacks<ibex_bluesky_core.callbacks.ISISCallbacks>` callbacks collection. 

Using the above example (i.e. without the {py:obj}`ISISCallbacks<ibex_bluesky_core.callbacks.ISISCallbacks>` helper) it can be used like so: 

```python
from pathlib import Path
import matplotlib.pyplot as plt
from ibex_bluesky_core.callbacks import LivePlot, PlotPNGSaver
from ibex_bluesky_core.plan_stubs import call_qt_aware

def plan():
    # Create a new figure to plot onto.
    yield from call_qt_aware(plt.figure)
    # Make a new set of axes on that figure
    ax = yield from call_qt_aware(plt.gca)
    # Set the y-scale to logarithmic
    yield from call_qt_aware(ax.set_yscale, "log")
    # Use the above axes in a LivePlot callback
    plot_callback = LivePlot(y="y_variable", x="x_variable", ax=ax, yerr="yerr_variable")
    # Add a PNG saving callback
    png_callback = PlotPNGSaver(y="y_variable", x="x_variable", ax=ax, output_dir=Path("C://", "Some", "Custom", "Directory"), postfix="test123")
```
