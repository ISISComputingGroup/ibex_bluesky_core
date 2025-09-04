# Chained Fitting (`ChainedLiveFit`)

[`ChainedLiveFit`](ibex_bluesky_core.callbacks.ChainedLiveFit) is a specialised callback that manages multiple LiveFit instances in a chain, where each fit's results inform the next fit's initial parameters. This is particularly useful when dealing with complex data sets where subsequent fits depend on the parameters obtained from previous fits.

This is useful for when you need to be careful with your curve fitting due to the presence of noisy data. It allows you to fit your widest (full) wavelength band first and then using its fit parameters as the initial guess of the parameters for the next fit

To show how we expect this to be used, we will use the PolarisingDae and wavelength bands to highlight the need for the carry over of fitting parameters. Below shows two wavelength bands, first bigger than the second, we will fit to the data in the first and carry it over to the data in the second to improve its, otherwise worse, fit.

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
