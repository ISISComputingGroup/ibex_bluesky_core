# Fitting Callback

Similar to [`LivePlot`](../callbacks/plotting.md), `ibex_bluesky_core` provides a thin wrapper around Bluesky's LiveFit class, enhancing it with additional functionality to better support real-time data fitting. This wrapper not only offers a wide selection of models to fit your data on, but also introduces guess generation for fit parameters. As new data points are acquired, the wrapper refines these guesses dynamically, improving the accuracy of the fit with each additional piece of data, allowing for more efficient and adaptive real-time fitting workflows.

In order to use the wrapper, import `LiveFit` from `ibex_bluesky_core` rather than 
`bluesky` directly:
```py
from ibex_bluesky_core.callbacks.fitting import LiveFit
```
**Note:** that you do not *need* `LivePlot` for `LiveFit` to work but it may be useful to know visaully how well the model fits to the raw data.

## Configuration

Below is a full example showing how to use standard `matplotlib` & `bluesky` functionality to apply fitting to a scan, using LivePlot and LiveFit. The fitting callback is set to expect data to take the form of a gaussian.
```py
import matplotlib.pyplot as plt
from ibex_bluesky_core.callbacks.plotting import LivePlot
from ibex_bluesky_core.callbacks.fitting import LiveFit
from bluesky.callbacks import LiveFitPlot

# Create a new figure to plot onto.
plt.figure()
# Make a new set of axes on that figure
ax = plt.gca() 
# ax is shared by fit_callback and plot_callback 

plot_callback = LivePlot(y="y_signal", x="x_signal", ax=ax, yerr="yerr_signal")
fit_callback = LiveFit(Gaussian.fit(), y="y_signal", x="x_signal", yerr="yerr_signal", update_every=0.5)
# Using the yerr parameter allows you to use error bars.
# update_every = in seconds, how often to recompute the fit. If `None`, do not compute until the end. Default is 1.
fit_plot_callback = LiveFitPlot(fit_callback, ax=ax, color="r")
```

**Note:** that the `LiveFit` callback doesn't directly do the plotting, it will return function parameters of the model its trying to fit to; a `LiveFit` object must be passed to `LiveFitPlot` which can then be subscribed to the `RunEngine`. See the [Bluesky Documentation](https://blueskyproject.io/bluesky/main/callbacks.html#livefitplot) for information on the various arguments that can be passed to the `LiveFitPlot` class.

Using the `yerr` argument allows you to pass uncertainties via a signal to LiveFit, so that the "weight" of each point influences the fit produced. By not providing a signal name you choose not to use uncertainties/weighting in the fitting calculation. Each weight is computed as `1/(standard deviation at point)` and is taken into account to determine how much a point affects the overall fit of the data. Same as the rest of `LiveFit`, the fit will be updated after every new point collected now taking into account the weights of each point. Uncertainty data is collected from Bluesky event documents after each new point.

The `plot_callback` and `fit_plot_callback` objects can then be subscribed to the `RunEngine`, using the same methods as described in [`LivePlot`](../callbacks/plotting.md). See the following example using `@subs_decorator`:

```py
@subs_decorator(
    [
        fit_plot_callback,
        plot_callback
    ]
)

def plan() -> ... 
```

## Models

We support **standard fits** for the following trends in data. See [Standard Fits](./standard_fits.md) for more infomation on the behaviour of these fits.

| Trend | Class Name in fitting_utils | Arguments | 
| ----- | -------------------------| ----------|
| Linear | [Linear](./standard_fits.md#linear) | None |
| Polynomial | [Polynomial](./standard_fits.md#polynomial) | Polynomial Degree (int) |
| Gaussian | [Gaussian](./standard_fits.md#gaussian) | None |
| Lorentzian | [Lorentzian](./standard_fits.md#lorentzian) | None |
| Damped Oscillator | [DampedOsc](./standard_fits.md#damped-oscillator-dampedosc) | None |
| Slit Scan Fit | [SlitScan](./standard_fits.md#slit-scan-slitscan) | Max Slit Size (int) |
| Error Function | [ERF](./standard_fits.md#error-function-erf) | None |
| Complementary Error Function | [ERFC](./standard_fits.md/#complementary-error-function-erfc) | None |
| Top Hat | [TopHat](./standard_fits.md#top-hat-tophat) | None |
| Trapezoid | [Trapezoid](./standard_fits.md#trapezoid) | None |
| PeakStats (COM) **\*** | - | -

\* Native to Bluesky there is support for `PeakStats` which "computes peak statsitics after a run finishes." See [Bluesky docs](https://blueskyproject.io/bluesky/main/callbacks.html#peakstats) for more information on this. Similar to `LiveFit` and `LiveFitPLot`, `PeakStats` is a callback and must be passed to `PeakStatsPlot` to be plotted on a set of axes, which is subscribed to by the `RunEngine`.

-------

Each of the above fit classes has a `.fit()` which returns an object of type `FitMethod`. This tells `LiveFit` how to perform fitting on the data. `FitMethod` is defined in `ibex_bluesky_core.callbacks.fitting`.

There are *two* ways that you can choose how to fit a model to your data:

### Option 1: Use the standard fits
When only using the standard fits provided by `ibex_bluesky_core`, the following syntax can be used, replacing `[FIT]` with your chosen one from `ibex_bluesky_core.callbacks.fitting.fitting_utils`:

```py
from bluesky.callbacks import LiveFitPlot
from ibex_bluesky_core.callbacks.fitting.fitting_utils import [FIT]

# Pass [FIT].fit() to the first parameter of LiveFit
lf = LiveFit([FIT].fit(), y="y_signal", x="x_signal", update_every=0.5)

# Then subscribe to LiveFitPlot(lf, ...)
```

The `[FIT].fit()` function will pass the `FitMethod` object straight to the `LiveFit` class.

**Note:** that for the fits in the above table that require parameters, you will need to pass value(s) to their `.fit` method. For example Polynomial fitting:

```py
lf = LiveFit(Polynomial.fit(3),  y="y_signal", x="x_signal", update_every=0.5)
# For a polynomial of degree 3
```

### Option 2: Use custom fits

If you wish, you can define your own non-standard `FitMethod` object. The `FitMethod` class takes two function arguments as follows:

- `model` 
    - A function representing the behaviour of the model.
    - Returns the `y` value (`float`) at the given `x` value and model parameters.
- `guess` 
    - A function that must take two `np.array` arrays, representing `x` data and respective `y` data, of type `float` as arguments and must return a `dict` in the form `dict[str, lmfit.Parameter]`.
    - This will be called to guess the properties of the model, given the data already collected in the Bluesky run.

See the following example on how to define these.

```py
# Linear Fitting

import lmfit

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

**Note:** that the parameters returned from the guess function must allocate to the arguments to the model function, ignoring the independant variable e.g `x` in this case. Array-like structures are not allowed. See the [lmfit documentation](https://lmfit.github.io/lmfit-py/parameters.html) for more information.

#### Option 2: Continued

Each `Fit` in `ibex_bluesky_core.callbacks.fitting` has a `.model()` and `.guess()`, which make up their fitting method. These are publically accessible class methods.

This means that aslong as the parameters returned from the guess function match to the arguments of the model function, you may mix and match user-made and standard, models and guess functions in the following manner:

```py
import lmfit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear

def different_model(x: float, c1: float, c0: float) -> float:
    
    return c1 * x + c0 ** 2 # y = mx + (c ** 2)


fit_method = FitMethod(different_model, Linear.guess())
# Uses the user defined model and the standard Guessing. function for linear models

lf = LiveFit(fit_method, y="y_signal", x="x_signal", update_every=0.5)

# Then subscribe to LiveFitPlot(lf, ...)
```
... or the other way round ...

```py
import lmfit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Linear

# This Guessing. function isn't very good because it's return values don't change on the data already collected in the Bluesky run
# It always guesses that the linear function is y = x

def different_guess(x: float, c1: float, c0: float) -> float:
    
    init_guess = {
        "c1": lmfit.Parameter("c1", 1), # gradient
        "c0": lmfit.Parameter("c0", 0), # y - intercept
    }

    return init_guess

fit_method = FitMethod(Linear.model(), different_guess)
# Uses the standard linear model and the user defined Guessing. function

lf = LiveFit(fit_method, y="y_signal", x="x_signal", update_every=0.5)

# Then subscribe to LiveFitPlot(lf, ...)
```

Or you can create a completely user-defined fitting method.

**Note:** that for fits that require arguments, you will need to pass values to their respecitive `.model` and `.guess` functions. E.g for `Polynomial` fitting:

```py
fit_method = FitMethod(Polynomial.model(3), different_guess) # If using a custom guess function
lf = LiveFit(fit_method, ...)
```
See the [standard fits](#models) list above for standard fits which require parameters. It gets more complicated if you want to define your own custom model or guess which you want to pass parameters to. You will have to define a function that takes these parameters and returns the model / guess function with the subsituted values.
