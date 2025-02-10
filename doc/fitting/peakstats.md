# PeakStats Callback

Similar to [`LivePlot`](../callbacks/plotting.md), `ibex_bluesky_core` provides a thin wrapper around Bluesky's `PeakStats` class, swapping out their Centre of Mass (CoM) algorithm for one that is better suited to our use cases.

`PeakStats` returns a dictionary of the following statistical properties... `com`, `cen`, `max`, `min`, `crossing` and `fwhm`. More info on this [here](https://blueskyproject.io/bluesky/main/callbacks.html#peakstats).

In order to use the wrapper, import `PeakStats` from `ibex_bluesky_core` rather than 
`bluesky` directly:
```py
from ibex_bluesky_core.callbacks.fitting import LiveFit
```

## Our CoM Algorithm

Given non-continuous arrays of collected data `x` and `y`, ({py:obj}`ibex_bluesky_core.callbacks.fitting.center_of_mass`) returns the `x` value of the centre of mass.

Our use cases require that our algorithm abides to the following rules:
- Any background on data does not skew the centre of mass
- The order in which data is received does not skew the centre of mass
- Should support non-constant point spacing without skewing the centre of mass

*Note that this is designed for only **positive** peaks.*

### Step-by-step

1) Sort `x` and `y` arrays in respect of `x` ascending. This is so that data can be received in any order.
2) From each `y` element, subtract `min(y)`. This means that any constant background over data is ignored. (Does not work for negative peaks)
3) Calculate weight for each point; based on it's `x` distances from neighbouring points. This ensures non-constant point spacing is accounted for in our calculation.
4) `CoM` is calculated as ```{math}
com_x = \frac{\sum_{}^{}x * y * \text{weight}}{\sum_{}^{}y * \text{weight}}
```