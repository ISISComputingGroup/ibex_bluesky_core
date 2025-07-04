# Fitting Callbacks

Similar to [`LivePlot`](../callbacks/plotting.md), [`ibex_bluesky_core`](ibex_bluesky_core) provides a thin wrapper around Bluesky's [`LiveFit`](ibex_bluesky_core.callbacks.LiveFit) class, enhancing it with additional functionality to better support real-time data fitting. This wrapper not only offers a wide selection of models to fit your data on, but also introduces guess generation for fit parameters. As new data points are acquired, the wrapper refines these guesses dynamically, improving the accuracy of the fit with each additional piece of data, allowing for more efficient and adaptive real-time fitting workflows.

In order to use the wrapper, import[`LiveFit`](ibex_bluesky_core.callbacks.LiveFit from [`ibex_bluesky_core`](ibex_bluesky_core) rather than 
`bluesky` directly:
```py
from ibex_bluesky_core.callbacks.fitting import LiveFit
```
.. note::
  that you do not *need* [`LivePlot`](ibex_bluesky_core.callbacks.LivePlot)  for [`LiveFit`](ibex_bluesky_core.callbacks.LiveFit) to work but it may be useful to know visaully how well the model fits to the raw data.

## Configuration

Below is a full example showing how to use standard `matplotlib` & `bluesky` functionality to apply fitting to a scan, using LivePlot and LiveFit. The fitting callback is set to expect data to take the form of a gaussian.
```py
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
# update_every = in seconds, how often to recompute the fit. If `None`, do not compute until the end. Default is 1.
fit_plot_callback = LiveFitPlot(fit_callback, ax=ax, color="r")
```

.. note::
  that the [`LiveFit`](ibex_bluesky_core.callbacks.LiveFit) callback doesn't directly do the plotting, it will return function parameters of the model its trying to fit to; a [`LiveFit`](ibex_bluesky_core.callbacks.LiveFit) object must be passed to `LiveFitPlot` which can then be subscribed to the `RunEngine`. See the [Bluesky Documentation](https://blueskyproject.io/bluesky/main/callbacks.html#livefitplot) for information on the various arguments that can be passed to the `LiveFitPlot` class.

Using the `yerr` argument allows you to pass uncertainties via a signal to LiveFit, so that the "weight" of each point influences the fit produced. By not providing a signal name you choose not to use uncertainties/weighting in the fitting calculation. Each weight is computed as `1/(standard deviation at point)` and is taken into account to determine how much a point affects the overall fit of the data. Same as the rest of [`LiveFit`](ibex_bluesky_core.callbacks.LiveFit), the fit will be updated after every new point collected now taking into account the weights of each point. Uncertainty data is collected from Bluesky event documents after each new point.

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

| Trend | Class Name in [`fitting`](ibex_bluesky_core.fitting)          | Arguments | 
| ----- |---------------------------------------------------------------| ----------|
| Linear | [Linear](./standard_fits.md#linear)                           | None |
| Polynomial | [Polynomial](./standard_fits.md#polynomial)                   | Polynomial Degree (int) |
| Gaussian | [Gaussian](./standard_fits.md#gaussian)                       | None |
| Lorentzian | [Lorentzian](./standard_fits.md#lorentzian)                   | None |
| Damped Oscillator | [DampedOsc](./standard_fits.md#damped-oscillator-dampedosc)   | None |
| Slit Scan Fit | [SlitScan](./standard_fits.md#slit-scan-slitscan)             | None |
| Error Function | [ERF](./standard_fits.md#error-function-erf)                  | None |
| Complementary Error Function | [ERFC](./standard_fits.md/#complementary-error-function-erfc) | None |
| Top Hat | [TopHat](./standard_fits.md#top-hat-tophat)                   | None |
| Trapezoid | [Trapezoid](./standard_fits.md#trapezoid)                     | None |
| PeakStats (COM) **\*** | -                                                             | -

\* Native to Bluesky there is support for `PeakStats` which "computes peak statsitics after a run finishes." See [Bluesky docs](https://blueskyproject.io/bluesky/main/callbacks.html#peakstats) for more information on this. Similar to [`LiveFit`](ibex_bluesky_core.callbacks.LiveFit) and `LiveFitPLot`, `PeakStats` is a callback and must be passed to `PeakStatsPlot` to be plotted on a set of axes, which is subscribed to by the `RunEngine`.

-------

Each of the above fit classes has a `.fit()` which returns an object of type [`FitMethod`](ibex_bluesky_core.fitting.FitMethod). This tells [`LiveFit`](ibex_bluesky_core.callbacks.LiveFit) how to perform fitting on the data. [`FitMethod`](ibex_bluesky_core.fitting.FitMethod) is defined in `ibex_bluesky_core.fitting`.

There are *two* ways that you can choose how to fit a model to your data:

### Option 1: Use the standard fits
When only using the standard fits provided by [`ibex_bluesky_core`](ibex_bluesky_core), the following syntax can be used, replacing `[FIT]` with your chosen one from `ibex_bluesky_core.fitting`:

```py
from bluesky.callbacks import LiveFitPlot
from ibex_bluesky_core.fitting import [FIT]

# Pass [FIT].fit() to the first parameter of LiveFit
lf = LiveFit([FIT].fit(), y="y_signal", x="x_signal", update_every=0.5)

# Then subscribe to LiveFitPlot(lf, ...)
```

The `[FIT].fit()` function will pass the [`FitMethod`](ibex_bluesky_core.fitting.FitMethod) object straight to the [`LiveFit`](ibex_bluesky_core.callbacks.LiveFit) class.

.. note::
  that for the fits in the above table that require parameters, you will need to pass value(s) to their `.fit` method. For example Polynomial fitting:

```py
lf = LiveFit(Polynomial.fit(3),  y="y_signal", x="x_signal", update_every=0.5)
# For a polynomial of degree 3
```

### Option 2: Use custom fits

If you wish, you can define your own non-standard [`FitMethod`](ibex_bluesky_core.fitting.FitMethod) object. The [`FitMethod`](ibex_bluesky_core.fitting.FitMethod) class takes two function arguments as follows:

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

.. note::
  that the parameters returned from the guess function must allocate to the arguments to the model function, ignoring the independant variable e.g `x` in this case. Array-like structures are not allowed. See the [lmfit documentation](https://lmfit.github.io/lmfit-py/parameters.html) for more information.

#### Option 2: Continued

Each `Fit` in `ibex_bluesky_core.callbacks.fitting` has a `.model()` and `.guess()`, which make up their fitting method. These are publically accessible class methods.

This means that aslong as the parameters returned from the guess function match to the arguments of the model function, you may mix and match user-made and standard, models and guess functions in the following manner:

```py
import lmfit
from ibex_bluesky_core.callbacks import LiveFit
from ibex_bluesky_core.fitting import FitMethod, Linear


def different_model(x: float, c1: float, c0: float) -> float:
    return c1 * x + c0 ** 2  # y = mx + (c ** 2)


fit_method = FitMethod(different_model, Linear.guess())
# Uses the user defined model and the standard Guessing. function for linear models

lf = LiveFit(fit_method, y="y_signal", x="x_signal", update_every=0.5)

# Then subscribe to LiveFitPlot(lf, ...)
```
... or the other way round ...

```py
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

.. note::
  that for fits that require arguments, you will need to pass values to their respecitive `.model` and `.guess` functions. E.g for `Polynomial` fitting:

```py
fit_method = FitMethod(Polynomial.model(3), different_guess) # If using a custom guess function
lf = LiveFit(fit_method, ...)
```
See the [standard fits](#models) list above for standard fits which require parameters. It gets more complicated if you want to define your own custom model or guess which you want to pass parameters to. You will have to define a function that takes these parameters and returns the model / guess function with the subsituted values.

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

## Chained Fitting

[`ChainedLiveFit`](ibex_bluesky_core.callbacks.ChainedLiveFit) is a specialised callback that manages multiple LiveFit instances in a chain, where each fit's results inform the next fit's initial parameters. This is particularly useful when dealing with complex data sets where subsequent fits depend on the parameters obtained from previous fits.

This is useful for when you need to be careful with your curve fitting due to the presence of noisy data. It allows you to fit your widest (full) wavelength band first and then using its fit parameters as the initial guess of the parameters for the next fit

# Usage
To show how we expect this to be used we will use the PolarisingDae and wavelength bands to highlight the need for the carry over of fitting parameters. Below shows two wavelength bands, first bigger than the second, we will fit to the data in the first and carry it over to the data in the second to improve its, otherwise worse, fit.

```python
# Needed for PolarisingDae
flipper = block_rw(float, "flipper")
total_flight_path_length = sc.scalar(value=10, unit=sc.units.m)

x_axis = block_rw(float, "x_axis", write_config=BlockWriteConfig(settle_time_s=0.5))
wavelength_band_0 = sc.array(dims=["tof"], values=[0, 9999999999.0], unit=sc.units.angstrom, dtype="float64")
wavelength_band_1 = sc.array(dims=["tof"], values=[0.0, 0.07], unit=sc.units.angstrom, dtype="float64")

dae = polarising_dae(det_pixels=[1], frames=50, flipper=flipper, flipper_states=(0.0, 1.0),
                     intervals=[wavelength_band_0, wavelength_band_1],
                     total_flight_path_length=total_flight_path_length, monitor=2)


def plan() -> Generator[Msg, None, None]:
  fig, (ax1, ax2) = yield from call_qt_aware(plt.subplots, 2)
  chained_fit = ChainedLiveFit(method=Linear.fit(), y=[dae.reducer.wavelength_bands[0].calculate_polarisation.name,
                                                       dae.reducer.wavelength_bands[1].calculate_polarisation.name],
                               x=bob.name, ax=[ax1, ax2])

  # Subscribe chained_fit to RE and run do a scan for example
  # chained_fit.get_livefits()[-1].result will give you the fitting results for the last wavelength band
```

- You are expected to pass in the list of signal names for each independent variable to `y` in order of how you want the subsequent fitting to go.
- You may also pass in a list of matplotlib axes, which will mean that LiveFitPlots are created per LiveFit, and it will plot the each respective fit to an axis. LiveFitPlots are not created if you do not pass `ax`.
- Similar to the `y` parameter, you may pass signal names which correspond to uncertainty values for each independent variable.

```{hint}
The method for fitting is the same across all independent variables.
```

```{note}
Parameter uncertainties are not carried over between fits 
```

```{important}
If a fit fails to converge, subsequent fits will use their default guess functions
```
