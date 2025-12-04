# Centre of Mass

{py:obj}`ibex_bluesky_core.callbacks.CentreOfMass` provides functionality for calculating a specific definition of a "centre of mass": it computes the centre of mass of a 2-dimensional region bounded by:
- `min(x)`
- `max(x)`
- `min(y)`
- Straight-line segments joining `(x, y)` data points with their nearest neighbours along the x axis

{py:obj}`~ibex_bluesky_core.callbacks.CentreOfMass` stores its result in the {py:obj}`~ibex_bluesky_core.callbacks.CentreOfMass.result` property.

:::{note}
This will return **different** results from the `com` property available from {py:obj}`bluesky.callbacks.fitting.PeakStats` in the following cases:
- Points irregularly sampled along the x-axis
- Points with negative y-values
- x data which does not monotonically increase

For a detailed comparison of the two implementations, see [unit tests written to expose tricky cases](https://github.com/bluesky/bluesky/blob/2d6fecd45e8de3a7d53d1c16dcd1a7b8f6f88d69/src/bluesky/tests/test_scientific.py#L142).
:::

Given non-continuous arrays of collected data `x` and `y`, {py:obj}`~ibex_bluesky_core.callbacks.CentreOfMass` returns the `x` value of the centre of mass.

Many of our use cases require that our algorithm follows the following rules:
- Any background on data should not change the centre of mass.
- The order in which data is received should not change the centre of mass
- Should support non-constant point spacing without skewing the centre of mass

```{note}
Note that this is designed for only **positive** peaks.
```

{py:obj}`ibex_bluesky_core.callbacks.CentreOfMass` is included in {doc}`our callbacks collection <isiscallbacks>`.

---

**Implementation details**

1) Sort `x` and `y` arrays in respect of `x` ascending. This is so that data can be received in any order.
2) From each `y` element, subtract `min(y)`. This means that any constant background over data is ignored.
3) Decompose the curve into a series of trapezoidal regions, and then further decompose those
trapezoidal regions into rectangular and triangular regions.
4) Compute centre of mass of the overall shape by composition of each region:
```{math}
C_x = \frac{\sum_{i}^{} C_{ix} * A_i}{\sum_{i}^{} A_i}
```