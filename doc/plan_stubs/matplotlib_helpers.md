# [`call_qt_aware`](ibex_bluesky_core.plan_stubs.call_qt_aware) (matplotlib helpers)

When attempting to use `matplotlib` UI functions directly in a plan, and running `matplotlib` using a `Qt`
backend (e.g. in a standalone shell outside IBEX), you may see a hang or an error of the form:

```
UserWarning: Starting a Matplotlib GUI outside of the main thread will likely fail.
  fig, ax = plt.subplots()
```

This is because the `RunEngine` runs plans in a worker thread, not in the main thread, which then requires special
handling when calling functions that will update a UI.

The [`call_qt_aware`](ibex_bluesky_core.plan_stubs.call_qt_aware) plan stub can call `matplotlib` functions in a
Qt-aware context, which allows them to be run directly from a plan. It allows the same arguments and 
keyword-arguments as the underlying matplotlib function it is passed.

```{note}
Callbacks such as `LivePlot` and `LiveFitPlot` already route UI calls to the appropriate UI thread by default. 
The following plan stubs are only necessary if you need to call functions which will create or update a matplotlib
plot from a plan directly - for example to create or close a set of axes before passing them to callbacks.
```

Usage example:

```python
import matplotlib.pyplot as plt
from ibex_bluesky_core.plan_stubs import call_qt_aware
from ibex_bluesky_core.callbacks.plotting import LivePlot
from bluesky.callbacks import LiveFitPlot
from bluesky.preprocessors import subs_decorator


def my_plan():
    # BAD - likely to either crash or hang the plan.
    # plt.close("all")
    # fig, ax = plt.subplots()

    # GOOD
    yield from call_qt_aware(plt.close, "all")
    fig, ax = yield from call_qt_aware(plt.subplots)

    # Pass the matplotlib ax object to other callbacks
    @subs_decorator([
        LiveFitPlot(..., ax=ax),
        LivePlot(..., ax=ax),
    ])
    def inner_plan():
        ...
```
