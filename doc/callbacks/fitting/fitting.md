# Fitting (`LiveFit`)

Similar to [`LivePlot`](/callbacks/plotting.md), {py:obj}`ibex_bluesky_core.callbacks.LiveFit` provides a thin wrapper around Bluesky's {py:obj}`bluesky.callbacks.LiveFit` class, enhancing it with additional functionality to better support real-time data fitting. This wrapper not only offers a wide selection of models to fit your data on, but also introduces guess generation for fit parameters. As new data points are acquired, the wrapper refines these guesses dynamically, improving the accuracy of the fit with each additional piece of data, allowing for more efficient and adaptive real-time fitting workflows.

In order to use the wrapper, import `LiveFit` is imported from {py:obj}`ibex_bluesky_core.callbacks.LiveFit` rather than {py:obj}`bluesky.callbacks.LiveFit`:

```python
from ibex_bluesky_core.callbacks import LiveFit
```

## Configuration

Below is a full example showing how to use standard {external+matplotlib:doc}`matplotlib <index>` & {external+bluesky:doc}`bluesky <index>` functionality to apply fitting to a scan, using {py:obj}`~ibex_bluesky_core.callbacks.LivePlot` and {py:obj}`~ibex_bluesky_core.callbacks.LiveFit`. The fitting callback is set to expect data to take the form of a Gaussian, using the {py:obj}`ibex_bluesky_core.fitting.Gaussian` model.

```python
import matplotlib.pyplot as plt
from ibex_bluesky_core.callbacks import LiveFit, LivePlot
from ibex_bluesky_core.fitting import Gaussian
from bluesky.callbacks import LiveFitPlot

# Create a new figure to plot onto.
plt.figure()
# Make a new set of axes on that figure
ax = plt.gca() 
# ax is shared by fit_callback and plot_callback 

plot_callback = LivePlot(y="y_signal", x="x_signal", ax=ax, yerr="yerr_signal")
fit_callback = LiveFit(Gaussian.fit(), y="y_signal", x="x_signal", yerr="yerr_signal", update_every=0.5)
# Using the yerr parameter allows you to use error bars.
# update_every = in seconds, how often to recompute the fit. 
#   If `None`, do not compute until the end. Default is 1.
fit_plot_callback = LiveFitPlot(fit_callback, ax=ax, color="r")
```

:::{note}
The {py:obj}`~ibex_bluesky_core.callbacks.LiveFit` callback doesn't perform plotting. It will return fitted parameters; a {py:obj}`~ibex_bluesky_core.callbacks.LiveFit` object must be passed to {py:obj}`bluesky.callbacks.mpl_plotting.LiveFitPlot` in order to plot.
:::

Using the `yerr` argument allows you to pass uncertainties via a signal to LiveFit, so that the "weight" of each point influences the fit produced. By not providing a signal name you choose not to use uncertainties/weighting in the fitting calculation. Each weight is computed as `1/(standard deviation at point)` and is taken into account to determine how much a point affects the overall fit of the data. Same as the rest of {py:obj}`~ibex_bluesky_core.callbacks.LiveFit`, the fit will be updated after every new point collected now taking into account the weights of each point. Uncertainty data is collected from Bluesky event documents after each new point.

The `plot_callback` and `fit_plot_callback` objects can then be subscribed to the `RunEngine`, for example using {py:obj}`~bluesky.preprocessors.subs_decorator`:

```python
from bluesky.preprocessors import subs_decorator


@subs_decorator(
    [
        fit_plot_callback,
        plot_callback
    ]
)
def plan():
   ...
```

## Models

We support **standard fits** for the following trends in data. See [Standard Fits](./standard_fits.md) for more information on the behaviour of these fits.

| Trend | Class Name in {py:obj}`ibex_bluesky_core.fitting` | Arguments | 
| ----- |---------------------------------------------------| ----------|
| Linear | [Linear](#fit_linear)                             | None |
| Polynomial | [Polynomial](#fit_polynomial)                     | Polynomial Degree (int) |
| Gaussian | [Gaussian](#fit_gaussian)                         | None |
| Lorentzian | [Lorentzian](#fit_lorentzian)                     | None |
| Damped Oscillator | [DampedOsc](#fit_damped_osc)                      | None |
| Slit Scan Fit | [SlitScan](#fit_slitscan)                         | None |
| Error Function | [ERF](#fit_erf)                                   | None |
| Complementary Error Function | [ERFC](#fit_erfc)                                 | None |
| Top Hat | [TopHat](#fit_tophat)                             | None |
| Trapezoid | [Trapezoid](#fit_trapezoid)                       | None |
| PeakStats (COM) **\*** | -                                                 | - |

Bluesky additionally provides a {py:obj}`bluesky.callbacks.fitting.PeakStats` callback which computes peak statistics after a run finishes. Similar to {py:obj}`~ibex_bluesky_core.callbacks.LiveFit`, {py:obj}`~bluesky.callbacks.fitting.PeakStats` does not plot by itself. The {py:obj}`~bluesky.callbacks.mpl_plotting.plot_peak_stats` function can be used to draw results of a {py:obj}`~bluesky.callbacks.fitting.PeakStats` on a plot.

-------

Each of the above fit classes has a `.fit()` which returns an object of type {py:obj}`ibex_bluesky_core.fitting.FitMethod`. This tells {py:obj}`~ibex_bluesky_core.callbacks.LiveFit` how to perform fitting on the data.

There are *two* ways that you can choose how to fit a model to your data:

## Standard Models

When only using the standard fits provided by the {py:obj}`ibex_bluesky_core.fitting` module, the following syntax can be used, replacing `[FIT]` with your chosen model from {py:obj}`ibex_bluesky_core.fitting`:

```python
from bluesky.callbacks import LiveFitPlot
from ibex_bluesky_core.fitting import [FIT]

# Pass [FIT].fit() to the first parameter of LiveFit
lf = LiveFit([FIT].fit(), y="y_signal", x="x_signal", update_every=0.5)

# Then subscribe to LiveFitPlot(lf, ...)
```

The `[FIT].fit()` function will pass the {py:obj}`~ibex_bluesky_core.fitting.FitMethod` object straight to the {py:obj}`~ibex_bluesky_core.callbacks.LiveFit` class.

:::{note}
For the fits in the above table that require parameters, you will need to pass value(s) to their `.fit` method. For example, for a {py:obj}`~ibex_bluesky_core.fitting.Polynomial` model:
:::

```python
# For a polynomial of degree 3
lf = LiveFit(Polynomial.fit(3),  y="y_signal", x="x_signal", update_every=0.5)
```

## Custom Models

If you wish, you can define your own non-standard {py:obj}`~ibex_bluesky_core.fitting.FitMethod` object. The {py:obj}`~ibex_bluesky_core.fitting.FitMethod` class takes two function arguments as follows:

- `model` 
    - A function representing the behaviour of the model.
    - Returns the `y` value ({py:obj}`float`) at the given `x` value and model parameters.
- `guess` 
    - A function that must take two {py:obj}`numpy.ndarray` arrays, representing `x` data and respective `y` data, of type {py:obj}`float` as arguments and must return a {py:obj}`dict` with {py:obj}`str` keys and {py:obj}`lmfit.parameter.Parameter` values.
    - This will be called to guess a set of initial values for the fit, given the data already collected in the bluesky run.

See the following example on how to define these.

```python
# Linear Fitting
import numpy.typing as npt
import numpy as np
import lmfit
from ibex_bluesky_core.fitting import FitMethod
from ibex_bluesky_core.callbacks import LiveFit

def model(x: float, c1: float, c0: float) -> float:
    
    return c1 * x + c0 # y = mx + c

def guess(x: npt.NDArray[np.float64], y: npt.NDArray[np.float64]) -> dict[str, lmfit.Parameter]:

    # Linear regression calculation
    # x = set of x data
    # y = set of respective y data
    # x[n] makes a pair with y[n]
    
    numerator = sum(x * y) - sum(x) * sum(y)
    denominator = sum(x**2) - sum(x) ** 2

    c1 = numerator / denominator
    c0 = (sum(y) - c1 * sum(x)) / len(x)

    init_guess = {
        "c1": lmfit.Parameter("c1", c1), # gradient
        "c0": lmfit.Parameter("c0", c0), # y - intercept
    }

    return init_guess

fit_method = FitMethod(model, guess) 
#Pass the model and guess function to FitMethod

lf = LiveFit(fit_method, y="y_signal", x="x_signal", update_every=0.5)

# Then subscribe to LiveFitPlot(lf, ...)
```

:::{note}
The parameters returned from the guess function must allocate to the arguments to the model function, ignoring the independant variable e.g `x` in this case. Array-like structures are not allowed. See the {external+lmfit:doc}`parameters` for more information.
:::

Each {py:obj}`~ibex_bluesky_core.fitting.FitMethod` in {py:obj}`ibex_bluesky_core.fitting` has a `.model()` and `.guess()`, which make up their fitting method. These are publicly accessible class methods.

This means that as long as the parameters returned from the guess function match to the arguments of the model, you may mix and match user-defined and standard models and guess functions:

```python
from ibex_bluesky_core.callbacks import LiveFit
from ibex_bluesky_core.fitting import FitMethod, Linear


def different_model(x: float, c1: float, c0: float) -> float:
    return c1 * x + c0 ** 2  # y = mx + (c ** 2)


fit_method = FitMethod(different_model, Linear.guess())
# Uses the user defined model and the standard Guessing. function for linear models

lf = LiveFit(fit_method, y="y_signal", x="x_signal", update_every=0.5)

# Then subscribe to LiveFitPlot(lf, ...)
```
Or the other way round ...

```python
import lmfit
from ibex_bluesky_core.callbacks import LiveFit
from ibex_bluesky_core.fitting import FitMethod, Linear


# This Guessing. function isn't very good because it's return values don't change on the data already collected in the Bluesky run
# It always guesses that the linear function is y = x

def different_guess(x: float, c1: float, c0: float) -> float:
    init_guess = {
      "c1": lmfit.Parameter("c1", 1),  # gradient
      "c0": lmfit.Parameter("c0", 0),  # y - intercept
    }
  
    return init_guess


fit_method = FitMethod(Linear.model(), different_guess)
# Uses the standard linear model and the user defined Guessing. function

lf = LiveFit(fit_method, y="y_signal", x="x_signal", update_every=0.5)

# Then subscribe to LiveFitPlot(lf, ...)
```

Or you can create a completely user-defined fitting method.

:::{note}
For fits that require arguments, you will need to pass values to their respecitive `.model` and `.guess` functions. E.g for {py:obj}`~ibex_bluesky_core.fitting.Polynomial` fitting:
:::

```python
fit_method = FitMethod(Polynomial.model(3), different_guess) # If using a custom guess function
lf = LiveFit(fit_method, ...)
```
