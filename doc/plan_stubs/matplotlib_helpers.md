# `matplotlib` helpers

When attempting to use `matplotlib` UI functions directly in a plan, and running `matplotlib` using a `Qt`
backend (e.g. in a standalone shell outside IBEX), you may see an error of the form:

```
UserWarning: Starting a Matplotlib GUI outside of the main thread will likely fail.
  fig, ax = plt.subplots()
```

This is because the `RunEngine` runs plans in a worker thread, not in the main thread, which then requires special
handling when calling functions that will update a UI.

The following plan stubs provide Qt-safe wrappers around some matplotlib functions to avoid this error.

```{note}
Callbacks such as `LivePlot` and `LiveFitPlot` already route UI calls to the appropriate UI thread by default. 
The following plan stubs are only necessary if you need to call functions which will create or update a matplotlib
plot from a plan directly.
```

## `matplotlib_subplots`

The {py:obj}`ibex_bluesky_core.plan_stubs.matplotlib_subplots` plan stub is a Qt-safe wrapper 
around `matplotlib.pyplot.subplots()`. It allows the same arguments and keyword-arguments as the 
underlying matplotlib function.

Usage example:

```python
from ibex_bluesky_core.plan_stubs import matplotlib_subplots
from ibex_bluesky_core.callbacks.plotting import LivePlot
from bluesky.callbacks import LiveFitPlot
from bluesky.preprocessors import subs_decorator

def my_plan():
    # BAD
    # fig, ax = plt.subplots()
    
    # GOOD
    fig, ax = yield from matplotlib_subplots()
    
    # Pass the matplotlib ax object to other callbacks
    @subs_decorator([
        LiveFitPlot(..., ax=ax),
        LivePlot(..., ax=ax),
    ])
    def inner_plan():
        ...
```

