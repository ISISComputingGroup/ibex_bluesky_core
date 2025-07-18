# DAE (Data Acquisition Electronics)

The [`SimpleDae`](ibex_bluesky_core.devices.simpledae.SimpleDae) class is designed to be a configurable DAE object, which will cover the
majority of DAE use-cases within bluesky.

This class uses several objects to configure its behaviour:
- The [`Controller`](ibex_bluesky_core.devices.simpledae.Controller)  is responsible for beginning and ending acquisitions.
- The [`Waiter`](ibex_bluesky_core.devices.simpledae.Waiter) is responsible for waiting for an acquisition to be "complete".
- The [`Reducer`](ibex_bluesky_core.devices.simpledae.Reducer) is responsible for publishing data from an acquisition that has 
  just been completed.

This means that [`SimpleDae`](ibex_bluesky_core.devices.simpledae.SimpleDae) is generic enough to cope with most typical DAE use-casess, for
example running using either one DAE run per scan point, or one DAE period per scan point.

For complex use-cases, particularly those where the DAE may need to start and stop multiple 
acquisitions per scan point (e.g. Polarisation measurements), [`SimpleDae`](ibex_bluesky_core.devices.simpledae.SimpleDae) is unlikely to be 
suitable; instead the [`Dae`](ibex_bluesky_core.devices.dae.Dae) class should be subclassed directly to allow for finer control.

## Example configurations

### Run-per-point

```python

from ibex_bluesky_core.utils import get_pv_prefix
from ibex_bluesky_core.devices.simpledae import SimpleDae, RunPerPointController, PeriodGoodFramesWaiter, PeriodGoodFramesNormalizer
prefix = get_pv_prefix()
# One DAE run for each scan point, save the runs after each point.
controller = RunPerPointController(save_run=True)
# Wait for 500 good frames on each run. 
# Note despite using RunPerPointController here we are still using PeriodGoodFramesWaiter and PeriodGoodFramesNormalizer.
waiter = PeriodGoodFramesWaiter(500)
# Sum spectra 1..99 inclusive, then normalize by total good frames
reducer = PeriodGoodFramesNormalizer(
  prefix=prefix,
  detector_spectra=[i for i in range(1, 100)],
)

dae = SimpleDae(
  prefix=prefix,
  controller=controller,
  waiter=waiter,
  reducer=reducer,
)

# Can give signals user-friendly names if desired
controller.run_number.set_name("run number")
reducer.intensity.set_name("normalized counts")
```

### Period-per-point

```python

from ibex_bluesky_core.utils import get_pv_prefix
from ibex_bluesky_core.devices.simpledae import SimpleDae, PeriodPerPointController, PeriodGoodFramesWaiter, PeriodGoodFramesNormalizer

prefix = get_pv_prefix()
# One DAE period for each scan point, save the runs after the scan.
controller = PeriodPerPointController(save_run=True)
# Wait for 500 period good frames on each point
waiter = PeriodGoodFramesWaiter(500)
# Sum spectra 1..99 inclusive, then normalize by period good frames
reducer = PeriodGoodFramesNormalizer(
  prefix=prefix,
  detector_spectra=[i for i in range(1, 100)],
)

dae = SimpleDae(
  prefix=prefix,
  controller=controller,
  waiter=waiter,
  reducer=reducer,
)
```

```{note}
You will also need to set up the DAE in advance with enough periods. This can be done from a
plan using `yield from bps.mv(dae.number_of_periods, num_points)` before starting the scan.
```

## Mapping to bluesky device model

### Start of scan (`stage`)

[`SimpleDae`](ibex_bluesky_core.devices.simpledae.SimpleDae) will call [`controller.setup()`](ibex_bluesky_core.devices.simpledae.Controller.setup) to allow any pre-scan setup to be done.

For example, this is where the period-per-point controller object will begin a DAE run.

### Each scan point (`trigger`)

[`SimpleDae`](ibex_bluesky_core.devices.simpledae.SimpleDae) will call:
- [`controller.start_counting()`](ibex_bluesky_core.devices.simpledae.Controller.start_counting) to begin counting for a single scan point.
- [`waiter.wait()`](ibex_bluesky_core.devices.simpledae.Waiter.wait) to wait for that acquisition to complete
- [`controller.stop_counting()`](ibex_bluesky_core.devices.simpledae.Controller.stop_counting) to finish counting for a single scan point.
- [`reducer.reduce_data()`](ibex_bluesky_core.devices.simpledae.Reducer.reduce_data) to do any necessary post-processing on 
  the raw DAE data (e.g. normalization)

### Each scan point (`read`)

Any signals marked as "interesting" by the controller, reducer or waiter will be published
in the top-level documents published when `read()`ing the [`SimpleDae`](ibex_bluesky_core.devices.simpledae.SimpleDae) object.

These may correspond to EPICS signals directly from the DAE (e.g. good frames), or may be 
soft signals derived at runtime (e.g. normalized intensity).

This means that the [`SimpleDae`](ibex_bluesky_core.devices.simpledae.SimpleDae) object is suitable for use as a detector in most bluesky
plans, and will make an appropriate set of data available in the emitted documents.

### End of scan (`unstage`)

[`SimpleDae`](ibex_bluesky_core.devices.simpledae.SimpleDae) will call [`controller.teardown()`](ibex_bluesky_core.devices.simpledae.Controller.teardown) to allow any post-scan teardown to be done.

For example, this is where the period-per-point controller object will end a DAE run.

## Controllers

The [`Controller`]( ibex_bluesky_core.devices.simpledae.Controller) class is responsible for starting and stopping acquisitions, in a generic
way.

### RunPerPointController

This controller starts and stops a new DAE run for each scan point. It can be configured to 
either end runs or abort them on completion.

This controller causes the following signals to be published by `SimpleDae`:

- [`controller.run_number`](ibex_bluesky_core.devices.simpledae.RunPerPointController) - The run number into which data was collected. Only published 
  if runs are being saved.

### PeriodPerPointController

This controller begins a single DAE run at the start of a scan, and then counts into a new
DAE period for each individual scan point.

The DAE must be configured with enough periods in advance. This is possible to do from a
plan as follows:

```python
import bluesky.plan_stubs as bps
import bluesky.plans as bp
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.block import BlockRw


def plan():
    dae: SimpleDae = ...
    block: BlockRw = ...
    num_points = 20
    yield from bps.mv(dae.number_of_periods, num_points)
    yield from bp.scan([dae], block, 0, 10, num=num_points)
```

The controller causes the following signals to be published by [`SimpleDae`](ibex_bluesky_core.devices.simpledae.SimpleDae) :

- [`simpledae.period_num`]( ibex_bluesky_core.devices.simpledae.PeriodPerPointController) - the period number into which this scan point was counted.

## Reducers

A [`Reducer`](ibex_bluesky_core.devices.simpledae.Reducer) for a [`SimpleDae`](ibex_bluesky_core.devices.simpledae.SimpleDae) is responsible for publishing any data derived from the raw
DAE signals. For example, normalizing intensities are implemented as a reducer.

A reducer may produce any number of reduced signals.

### {py:obj}`PeriodGoodFramesNormalizer<ibex_bluesky_core.devices.simpledae.PeriodGoodFramesNormalizer>`

Uses good frames only from the current period.
This should be used if a controller which counts into multiple periods is being used OR if a
controller counts into multiple runs.

Published signals:
- `simpledae.period.good_frames` - the number of good frames reported by the DAE
- `reducer.det_counts` - summed detector counts for all of the user-provided spectra
- `reducer.intensity` - normalized intensity (`det_counts / good_frames`)
- `reducer.det_counts_stddev` - uncertainty (standard deviation) of the summed detector counts
- `reducer.intensity_stddev` - uncertainty (standard deviation) of the normalised intensity

### {py:obj}`MonitorNormalizer<ibex_bluesky_core.devices.simpledae.MonitorNormalizer>`

This normalizer sums a set of user-defined detector spectra, and then divides by the sum
of a set of user-defined monitor spectra.

Published signals:
- `reducer.det_counts` - summed detector counts for the user-provided detector spectra
- `reducer.mon_counts` - summed monitor counts for the user-provided monitor spectra
- `reducer.intensity` - normalized intensity (`det_counts / mon_counts`)
- `reducer.det_counts_stddev` - uncertainty (standard deviation) of the summed detector counts
- `reducer.mon_counts_stddev` - uncertainty (standard deviation) of the summed monitor counts
- `reducer.intensity_stddev` - uncertainty (standard deviation) of the normalised intensity

### {py:obj}`PeriodSpecIntegralsReducer<ibex_bluesky_core.devices.simpledae.PeriodSpecIntegralsReducer>`

This reducer exposes the raw integrals of the configured detector and monitor spectra, as
numpy arrays. By itself, this reducer is not useful in a scan, but is useful for downstream
processing as performed by reflectometry detector-mapping alignment for
example.

Published signals:
- `reducer.mon_integrals` - `numpy` array of integrated counts on each configured monitor pixel.
- `reducer.det_integrals` - `numpy` array of integrated counts on each configured detector pixel.

### {py:obj}`DSpacingMappingReducer<ibex_bluesky_core.devices.simpledae.DSpacingMappingReducer>`

This reducer exposes a numpy array of counts against d-spacing at each scan point.
It requires geometry information for each configured detector pixel:
- `l_total`: the total flight path length between source and detector
- `two_theta`: the scattering angle

:::{important}
All configured detectors are assumed to use the same time-of-flight boundaries. The results from
this reducer will be incorrect if this assumption is not true. In practice, detectors are almost
always configured with the same time-channel boundaries; monitors may have a different set.
:::

The process implemented by this reducer is:
- Read the entire spectrum-data map from the DAE.
- Convert the time channel boundaries for each pixel into d-spacing, using
{py:obj}`scippneutron.conversion.tof.dspacing_from_tof`, using the provided `l_total` and `two_theta`
geometry information for each pixel.
- Rebin all pixels into a consistent, user-specified, set of d-spacing bins.
- Sum over all pixels to get a 1-d array of counts against d-spacing.

The resulting array represents total counts that were measured by _any_ detector in the given d-spacing
bin. These counts may be fractional due to rebinning.

Published signals:
- `reducer.dspacing` - `numpy` array of counts in each d-spacing bin.

### Time of Flight and Wavelength Bounding Spectra

Scalar Normalizers (such as 
{py:obj}`PeriodGoodFramesNormalizer<ibex_bluesky_core.devices.simpledae.PeriodGoodFramesNormalizer>` or 
{py:obj}`GoodFramesNormalizer<ibex_bluesky_core.devices.simpledae.GoodFramesNormalizer>`) can be passed a
summing function which can optionally sum spectra between provided time of flight or wavelength bounds.

Monitor Normalizers, which have both monitors and detectors, can be passed a summing function for each of
these components independently, e.g. the detector can use time of flight while the monitor uses wavelength.
{py:obj}`tof_bounded_spectra<ibex_bluesky_core.devices.simpledae.tof_bounded_spectra>`
assumes that all pixels being summed share the same flight-path length. Where two separate
instances of {py:obj}`tof_bounded_spectra<ibex_bluesky_core.devices.simpledae.tof_bounded_spectra>` are used, 
such as in {py:obj}`MonitorNormalizer<ibex_bluesky_core.devices.simpledae.MonitorNormalizer>`, 
these may have different flight path lengths from each other.

Here is an example showing creating a scalar normalizer with time of flight bounds from 15000 to 25000 μs, 
and summing 2 detectors, using
{py:obj}`PeriodGoodFramesNormalizer<ibex_bluesky_core.devices.simpledae.PeriodGoodFramesNormalizer>`
as a reducer and passing 
{py:obj}`tof_bounded_spectra<ibex_bluesky_core.devices.simpledae.tof_bounded_spectra>`
as the summation function:

```python
import scipp

bounds=scipp.array(dims=["tof"], values=[15000.0, 25000.0], unit=scipp.units.us)

reducer = PeriodGoodFramesNormalizer(
    prefix=get_pv_prefix(),
    detector_spectra=[1, 2],
    summer=tof_bounded_spectra(bounds)
)
```

Here is an example with wavelength bounding, using 
{py:obj}`wavelength_bounded_spectra<ibex_bluesky_core.devices.simpledae.wavelength_bounded_spectra>`
used to sum the monitor component, and time of flight bounding for the detector summing spectra: 

```python
import scipp

wavelength_bounds = scipp.array(dims=["tof"], values=[0.0, 5.1], unit=scipp.units.angstrom, dtype="float64")
total_flight_path_length = scipp.scalar(value=85.0, unit=sc.units.m),
tof_bounds = scipp.array(dims=["tof"], values=[15000, 25000], unit=scipp.units.us)

reducer = MonitorNormalizer(
    prefix=get_pv_prefix(),
    detector_spectra=[1],
    monitor_spectra=[2],
    detector_summer=wavelength_bounded_spectra(wavelength_bounds, total_flight_path_length),
    monitor_summer=tof_bounded_spectra(tof_bounds)
)
```

In either case, the bounds are passed as a scipp array, which needs a `dims` attribute, `values` passed
as a list, and `units` (μs/microseconds for time of flight bounding, and angstrom for wavelength bounding)

If you don't specify either of these options, they will default to summing over the entire spectrum.

### Polarisation/Asymmetry

ibex_bluesky_core provides a helper method,
{py:obj}`ibex_bluesky_core.utils.calculate_polarisation`, for calculating the quantity (a-b)/(a+b). This quantity is used, for example, in neutron polarisation measurements, and in calculating asymmetry for muon measurements.

For this expression, scipp's default uncertainty propagation rules cannot be used as the uncertainties on (a-b) are correlated with those of (a+b) in the division step - but scipp assumes uncorrelated data. This helper method calculates the uncertainties following linear error propagation theory, using the partial derivatives of the above expression.

The partial derivatives are:

$ \frac{\delta}{\delta a}\Big(\frac{a - b}{a + b}) = \frac{2b}{(a+b)^2} $

$ \frac{\delta}{\delta b}\Big(\frac{a - b}{a + b}) = -\frac{2a}{(a+b)^2} $


Which then means the variances computed by this helper function are:

$ Variance = (\frac{\delta}{\delta a}^2 * variance_a) + (\frac{\delta}{\delta b}^2 * variance_b)  $ 


The polarisation function provided will calculate the polarisation between two values, A and B, which 
have different definitions based on the instrument context.

Instrument-Specific Interpretations
SANS Instruments (e.g., LARMOR)
A: Intensity in DAE period before switching a flipper.
B: Intensity in DAE period after switching a flipper.

Reflectometry Instruments (e.g., POLREF)
Similar to LARMOR, A and B represent intensities before and after flipper switching.

Muon Instruments
A and B refer to Measurements from different detector banks.

{py:obj}`ibex_bluesky_core.utils.calculate_polarisation`

See [`PolarisationReducer`](#PolarisationReducer) for how this is integrated into DAE behaviour. 

## Waiters

A [`waiter`](ibex_bluesky_core.devices.simpledae.Waiter) defines an arbitrary strategy for how long to count at each point.

Some waiters may be very simple, such as waiting for a fixed amount of time or for a number
of good frames or microamp-hours. However, it is also possible to define much more 
sophisticated waiters, for example waiting until sufficient statistics have been collected.

### GoodUahWaiter

[`GoodUahWaiter`](ibex_bluesky_core.devices.simpledae.GoodUahWaiter)

Waits for a user-specified number of microamp-hours.

Published signals:
- `simpledae.good_uah` - actual good uAh for this run.

### PeriodGoodFramesWaiter

[`PeriodGoodFramesWaiter`](ibex_bluesky_core.devices.simpledae.PeriodGoodFramesWaiter)

Waits for a user-specified number of good frames (in the current period) - this should be used even if the controller is splitting up points into separate runs.

Published signals:
- `simpledae.period.good_frames` - actual period good frames for this run.

### MEventsWaiter

[`MEventsWaiter`](ibex_bluesky_core.devices.simpledae.MEventsWaiter)

Waits for a user-specified number of millions of events

Published signals:
- `simpledae.m_events` - actual period good frames for this run.

### TimeWaiter

[`TimeWaiter`](ibex_bluesky_core.devices.simpledae.TimeWaiter)

Waits for a user-specified time duration, irrespective of DAE state.

Does not publish any additional signals.

## Polarising DAE

The polarising DAE provides specialised functionality for taking data whilst taking into account the polarity of the beam.

### DualRunDae

[`DualRunDae`](ibex_bluesky_core.devices.polarisingdae.DualRunDae) is a more complex version of [`SimpleDae`](ibex_bluesky_core.devices.simpledae.SimpleDae), designed specifically for taking polarisation measurements. It requires a flipper device and uses it to flip from one neutron state to the other between runs.

Key features:
- Controls a flipper device to switch between neutron states
- Handles three separate reduction strategies 
  - Up & Down Reducers, which run after each run
  - Main reducer, which runs after everything else

### polarising_dae

[`polarising_dae`](ibex_bluesky_core.devices.polarisingdae.polarising_dae) is a helper function that creates a configured `PolarisingDae` instance with wavelength binning based normalisation and polarisation calculation capabilities.

The following is how you may want to use `polarising_dae`:
```python
import scipp

flipper = block_rw(float, "alice")
wavelength_interval = scipp.array(dims=["tof"], values=[0, 9999999999.0], unit=scipp.units.angstrom, dtype="float64") # Creates a wavelength interval of the whole sprectrum
total_flight_path_length = sc.scalar(value=10, unit=sc.units.m)

dae = polarising_dae(det_pixels=[1], frames=500, flipper=flipper, flipper_states=(0.0, 1.0), intervals=[wavelength_interval], total_flight_path_length=total_flight_path_length, monitor=2)
```

:::{note}
  Notice how you must define what the `flipper_states` are to the polarising dae. This is so that it knows what to assign to the `flipper` device to move it to the "up state" and "down state"
  .
:::

### Polarising Reducers

#### MultiWavelengthBandNormalizer

[`MultiWavelengthBandNormalizer`](ibex_bluesky_core.devices.polarisingdae.MultiWavelengthBandNormalizer) sums wavelength-bounded spectra and normalises by monitor intensity.

Published signals:
- `wavelength_bands`: DeviceVector containing wavelength band measurements
  - `det_counts`: detector counts in the wavelength band
  - `mon_counts`: monitor counts in the wavelength band
  - `intensity`: normalised intensity in the wavelength band
  - Associated uncertainty measurements for each value

#### PolarisingReducer

[`PolarisationReducer`](ibex_bluesky_core.devices.polarisingdae.PolarisationReducer) calculates polarisation from 'spin-up' and 'spin-down' states of a polarising DAE. Uses the [`Polarisation`](#polarisationasymmetry) algorithm.

Published signals:
- `wavelength_bands`: DeviceVector containing polarisation measurements
  - `polarisation`: The calculated polarisation value for that wavelength band
  - `polarisation_ratio`: Ratio between up and down states for that wavelength band
  - Associated uncertainty measurements for each value

---

## `Dae` (base class, advanced)

[`Dae`](ibex_bluesky_core.devices.dae.Dae) is the principal class in ibex_bluesky_core which exposes configuration settings
and controls from the ISIS data acquisition electronics (DAE). [`SimpleDae`](ibex_bluesky_core.devices.simpledae.SimpleDae) derives from
DAE, so all of the signals available on [`Dae`](ibex_bluesky_core.devices.dae.Dae) are also available on [`SimpleDae`](ibex_bluesky_core.devices.simpledae.SimpleDae).

```{note}
 The `Dae` class is not intended to be used directly in scans - it is a low-level class
 which directly exposes functionality from the DAE, but has no scanning functionality by
 itself.
 
 It is intended that this object is only used directly when:
 - Configuring DAE settings within a plan.
 - For advanced use-cases, if arbitrary DAE control is required from a plan - but note 
   that it will usually be better to implement functionality at the device level rather 
   than the plan level.
 
 For other use-cases, a user-facing DAE class such as `SimpleDae` is likely to be more 
 appropriate to use as a detector in a scan - this class cannot be used by itself.
```

### Top-level signals

Some DAE parameters, particularly metadata parameters, are exposed as simple signals, 
for example [`dae.title`](ibex_bluesky_core.devices.dae.Dae) or [`dae.good_uah`](ibex_bluesky_core.devices.dae.Dae).

These signals are directly readable and settable from plans:

```python
import bluesky.plan_stubs as bps
from ibex_bluesky_core.devices.dae import Dae


def plan(dae: Dae):
    current_title = yield from bps.rd(dae.title)
    yield from bps.mv(dae.title, "new title")
```

### Period-specific signals

For signals which apply to the current period, see [`dae.period`](ibex_bluesky_core.devices.dae.DaePeriod), which contains signals
such as [`dae.period.good_uah`](ibex_bluesky_core.devices.dae.DaePeriod) (the number of good uamp-hours collected in the current period).


### Controlling the DAE directly

It is possible to control the DAE directly using the signals provided by [`dae.controls`](ibex_bluesky_core.devices.dae.DaeControls).

The intention is that these signals should be used by higher-level _devices_, rather than being
used by plans directly.

For example, beginning a run is possible via [`dae.controls.begin_run.trigger()`](ibex_bluesky_core.devices.dae.DaeControls).

### Additional begin_run flags

Options on `begin` (for example, beginning a run in paused mode) can be specified
using the [`dae.controls.begin_run_ex`](ibex_bluesky_core.devices.dae.DaeControls) signal.

Unlike the standard `begin_run` signal, this needs to be `set()` rather than simply
`trigger()`ed, the value on set is a combination of flags from [`BeginRunExBits`](ibex_bluesky_core.devices.dae.BeginRunExBits) .


### DAE Settings

Many signals on the DAE are only available as composite signals - this includes most DAE 
configuration parameters which are available under the "experiment setup" tab in IBEX, for
example wiring/detector/spectra tables, tcb settings, or vetos.

The classes implemented in this way are:
- `DaeTCBSettings` ([`dae.tcb_settings`](ibex_bluesky_core.devices.dae.DaeTCBSettings))
  - Parameters which appear under the "time channels" tab in IBEX
- `DaeSettings` ([`dae.dae_settings`](ibex_bluesky_core.devices.dae.DaeSettings))
  - Parameters which appear under the "data acquisition" tab in IBEX
- `DaePeriodSettings` ([`dae.period_settings`](ibex_bluesky_core.devices.dae.DaePeriodSettings)): 
  - Parameters which appear under the "periods" tab in IBEX

To read or change these settings from plans, use the associated dataclasses, which are
suffixed with `Data` (e.g. `DaeSettingsData` is the dataclass corresponding to `DaeSettings`):

```python
import bluesky.plan_stubs as bps
from ibex_bluesky_core.devices.dae import Dae
from ibex_bluesky_core.devices.dae._settings import DaeSettingsData


def plan(dae: Dae):
  # On read, settings are returned together as an instance of a dataclass.
  current_settings: DaeSettingsData = yield from bps.rd(dae.dae_settings)
  wiring_table: str = current_settings.wiring_filepath

  # On set, any unprovided settings are left unchanged.
  yield from bps.mv(dae.dae_settings, DaeSettingsData(
    wiring_filepath="a_new_wiring_table.dat",
    spectra_filepath="a_new_spectra_table.dat"
  ))
```


### DAE Spectra

Raw spectra are provided by the [`DaeSpectra`](ibex_bluesky_core.devices.dae.DaeSpectra) class. Not all spectra are automatically available
on the base DAE object - user classes will define the specific set of spectra which they are
interested in.

A [`DaeSpectra`](ibex_bluesky_core.devices.dae.DaeSpectra) object provides 3 arrays:
- `tof` (x-axis): time of flight.
- `counts` (y-axis): number of counts
  - Suitable for summing counts
  - Will give a discontinuous plot if plotted directly and bin widths are non-uniform.
- `counts_per_time` (y-axis): number of counts normalized by bin width
  - Not suitable for summing counts directly
  - Gives a continuous plot when plotted against x directly.

The [`Dae`](ibex_bluesky_core.devices.dae) base class does not provide any spectra by default. User-level classes should specify 
the set of spectra which they are interested in.

Spectra can be summed between two bounds based on time of flight bounds, or wavelength bounds, for both detector and monitor normalizers.

Both Scalar Normalizers (PeriodGoodFramesNormalizer, GoodFramesNormalizer) and MonitorNormalizers
accept the following arguments: 
- `detector_summer`: sums counts using pre-existing bounds, or sums using time of flight bounds,
or wavelength bounds.
- `monitor_summer` (MonitorNormalizer only): sums counts using pre-existing bounds,
or sums using time of flight bounds, or wavelength bounds.

For both options, the default, if none is specified, is to use pre-existing bounds.
