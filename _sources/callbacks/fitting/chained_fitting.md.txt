# Chained Fitting ({py:obj}`~ibex_bluesky_core.callbacks.ChainedLiveFit`)

{py:obj}`~ibex_bluesky_core.callbacks.ChainedLiveFit` is a specialised callback that manages multiple {py:obj}`~ibex_bluesky_core.callbacks.LiveFit` instances in a chain, where each fit's results inform the next fit's initial parameters. This is particularly useful when fitting datasets where the initial guess for each fit depends on the parameters obtained from a previous fit.

This is useful for when you need to be careful with your curve fitting due to the presence of noisy data. It allows you to fit your widest (full) wavelength band first and then using its fit parameters as the initial guess of the parameters for the next fit

To show how we expect this to be used, we will use a {py:obj}`~ibex_bluesky_core.devices.polarisingdae.DualRunDae` configured with multiple wavelength bands, to highlight the need to carry over fitting parameters. The example below shows two wavelength bands, first wider than the second. We will fit to the data in the widest wavelength band first, and carry over the results of that fit to the guess of the next fit, to improve the chances of that fit converging.

```python
from typing import Generator
import scipp as sc
import matplotlib.pyplot as plt
from ibex_bluesky_core.devices.block import block_rw, BlockWriteConfig
from ibex_bluesky_core.devices.polarisingdae import polarising_dae
from ibex_bluesky_core.plan_stubs import call_qt_aware
from ibex_bluesky_core.fitting import Linear
from ibex_bluesky_core.callbacks import ChainedLiveFit
from bluesky.utils import Msg


# Needed for PolarisingDae
flipper = block_rw(float, "flipper")
total_flight_path_length = sc.scalar(value=10, unit=sc.units.m)

x_axis = block_rw(float, "x_axis", write_config=BlockWriteConfig(settle_time_s=0.5))
wavelength_band_0 = sc.array(dims=["tof"], values=[0, 9999999999.0], unit=sc.units.angstrom, dtype="float64")
wavelength_band_1 = sc.array(dims=["tof"], values=[0.0, 0.07], unit=sc.units.angstrom, dtype="float64")

dae = polarising_dae(det_pixels=[1], frames=50, movable=flipper, movable_states=[0.0, 1.0],
                     intervals=[wavelength_band_0, wavelength_band_1],
                     total_flight_path_length=total_flight_path_length, monitor=2)


def plan() -> Generator[Msg, None, None]:
    fig, (ax1, ax2) = yield from call_qt_aware(plt.subplots, 2)
    chained_fit = ChainedLiveFit(method=Linear.fit(), y=[dae.reducer.wavelength_bands[0].calculate_polarisation.name,
                                                       dae.reducer.wavelength_bands[1].calculate_polarisation.name],
                               x=x_axis.name, ax=[ax1, ax2])
    
    ...  # perform a scan with chained_fit subscribed
    
    # will give you the fitting results for the last wavelength band
    chained_fit.get_livefits()[-1].result
```

The list of signal names for each independent variable should be passed in the same order that the fits are to be applied.

A list of matplotlib axes is accepted, which will mean that {external+bluesky:py:obj}`LiveFitPlots <bluesky.callbacks.mpl_plotting.LiveFitPlot>` are created per {py:obj}`~ibex_bluesky_core.callbacks.LiveFit`, and it will plot the each respective fit to an axis. {external+bluesky:py:obj}`LiveFitPlots <bluesky.callbacks.mpl_plotting.LiveFitPlot>` are not created if you do not pass `ax`.

Similar to the `y` parameter, uncertainties for each dependent variable are accepted in `yerr`.

{py:obj}`~ibex_bluesky_core.callbacks.ChainedLiveFit` currently has the following limitations:
- The method for fitting must be the same across all dependent variables.
- Parameter uncertainties are not carried over between fits
- If a fit fails to converge, the next fits will use their default guess functions
