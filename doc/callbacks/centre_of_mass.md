# Centre of Mass

[`CentreOfMass`](ibex_bluesky_core.callbacks.CentreOfMass) is a callback that provides functionality for calculating our definition of Centre of Mass. We calculate centre of mass from the 2D region bounded by min(y), min(x), max(x), and straight-line segments joining (x, y) data points with their nearest neighbours along the x axis.

[`CentreOfMass`](ibex_bluesky_core.callbacks.CentreOfMass) has a property, `result` which stores the centre of mass value once the callback has finished.

In order to use the callback, import `CentreOfMass` from `ibex_bluesky_core.callbacks`.
```py
from ibex_bluesky_core.callbacks import CentreOfMass
```

## Our CoM Algorithm

Given non-continuous arrays of collected data `x` and `y`, ({py:obj}`ibex_bluesky_core.callbacks.CentreOfMass`) returns the `x` value of the centre of mass.

Our use cases require that our algorithm abides to the following rules:
- Any background on data does not skew the centre of mass
- The order in which data is received does not skew the centre of mass
- Should support non-constant point spacing without skewing the centre of mass

*Note that this is designed for only **positive** peaks.*

### Step-by-step

1) Sort `x` and `y` arrays in respect of `x` ascending. This is so that data can be received in any order.
2) From each `y` element, subtract `min(y)`. This means that any constant background over data is ignored. (Does not work for negative peaks)
3) Calculate weight/widths for each point; based on it's `x` distances from neighbouring points. This ensures non-constant point spacing is accounted for in our calculation.
4) For each decomposed shape that makes up the total area under the curve, `CoM` is calculated as the following:
```{math}
com_x = \frac{\sum_{}^{}x * y * \text{weight}}{\sum_{}^{}y * \text{weight}}
```

[`CentreOfMass`](ibex_bluesky_core.callbacks.CentreOfMass) can be used from our callbacks collection. See [ISISCallbacks](ibex_bluesky_core.callbacks.ISISCallbacks).