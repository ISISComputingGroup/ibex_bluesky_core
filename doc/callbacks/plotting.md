# Plotting

Bluesky has good integration with `matplotlib` for data visualization, and data from scans 
may be easily plotted using the `LivePlot` callback.

`ibex_bluesky_core` provides a thin wrapper over bluesky's default `LivePlot` callback,
which ensures that plots are promptly displayed in IBEX.

In order to use the wrapper, import `LivePlot` from `ibex_bluesky_core` rather than 
`bluesky` directly:
```
from ibex_bluesky_core.callbacks.plotting import LivePlot
```

## Configuration

A range of configuration options for `LivePlot` are available - see the 
[bluesky `LivePlot` documentation](https://blueskyproject.io/bluesky/main/callbacks.html#bluesky.callbacks.mpl_plotting.LivePlot)
for more details about available options.

The `LivePlot` object allows an arbitrary set of matplotlib `Axes` to be passed in, onto
which it will plot. This can be used to configure properties which are not directly exposed 
on the `LivePlot` object, for example log-scaled axes.

See the [matplotlib `Axes` documentation](https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.html) 
for a full range of options on how to configure an `Axes` object.

Below is a full example showing how to use standard `matplotlib` & `bluesky` functionality
to plot a scan with a logarithmically-scaled y-axis:

```python
import matplotlib.pyplot as plt
from ibex_bluesky_core.callbacks.plotting import LivePlot
# Create a new figure to plot onto.
plt.figure()
# Make a new set of axes on that figure
ax = plt.gca()
# Set the y-scale to logarithmic
ax.set_yscale("log")
# Use the above axes in a LivePlot callback
plot_callback = LivePlot(y="y_variable", x="x_variable", ax=ax, yerr="yerr_variable")
# yerr is the uncertanties of each y value, producing error bars
```

By providing a signal name to the `yerr` argument you can pass uncertainties to LivePlot, by not providing anything for this argument means that no errorbars will be drawn. Errorbars are drawn after each point collected, displaying their standard deviation- uncertainty data is collected from Bluesky event documents and errorbars are updated after every new point added.

The `plot_callback` object can then be subscribed to the run engine, using either:
- An explicit callback when calling the run engine: `RE(some_plan(), plot_callback)`
- Be subscribed in a plan using `@subs_decorator` from bluesky **(recommended)**
- Globally attached to the run engine using `RE.subscribe(plot_callback)`
  * Not recommended, not all scans will use the same variables and a plot setup that works
    for one scan is unlikely to be optimal for a different type of scan.

By subsequently re-using the same `ax` object in later scans, rather than creating a new 
`ax` object for each scan, two scans can be "overplotted" with each other for comparison.
