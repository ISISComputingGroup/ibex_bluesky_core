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
acquisitions per scan point (e.g. polarization measurements), [`SimpleDae`](ibex_bluesky_core.devices.simpledae.SimpleDae) is unlikely to be 
suitable; instead the [`Dae`](ibex_bluesky_core.devices.dae.Dae) class should be subclassed directly to allow for finer control.

## Example configurations

### Run-per-point

```python

from ibex_bluesky_core.utils import get_pv_prefix
from ibex_bluesky_core.devices.simpledae import SimpleDae, RunPerPointController, GoodFramesWaiter, GoodFramesNormalizer
prefix = get_pv_prefix()
# One DAE run for each scan point, save the runs after each point.
controller = RunPerPointController(save_run=True)
# Wait for 500 good frames on each run
waiter = GoodFramesWaiter(500)
# Sum spectra 1..99 inclusive, then normalize by total good frames
reducer = GoodFramesNormalizer(
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

### GoodFramesNormalizer

[`GoodFramesNormalizer`](ibex_bluesky_core.devices.simpledae.GoodFramesNormalizer)

This normalizer sums a set of user-defined detector spectra, and then divides by the number
of good frames.

Published signals:
- `simpledae.good_frames` - the number of good frames reported by the DAE
- `reducer.det_counts` - summed detector counts for all of the user-provided spectra
- `reducer.intensity` - normalized intensity (`det_counts / good_frames`)
- `reducer.det_counts_stddev` - uncertainty (standard deviation) of the summed detector counts
- `reducer.intensity_stddev` - uncertainty (standard deviation) of the normalised intensity

### PeriodGoodFramesNormalizer

[`PeriodGoodFramesNormalizer`](ibex_bluesky_core.devices.simpledae.PeriodGoodFramesNormalizer)

Equivalent to the `GoodFramesNormalizer` above, but uses good frames only from the current
period. This should be used if a controller which counts into multiple periods is being used.

Published signals:
- `simpledae.period.good_frames` - the number of good frames reported by the DAE
- `reducer.det_counts` - summed detector counts for all of the user-provided spectra
- `reducer.intensity` - normalized intensity (`det_counts / good_frames`)
- `reducer.det_counts_stddev` - uncertainty (standard deviation) of the summed detector counts
- `reducer.intensity_stddev` - uncertainty (standard deviation) of the normalised intensity

### DetectorMonitorNormalizer

[`DetectorMonitorNormalizer`](ibex_bluesky_core.devices.simpledae.MonitorNormalizer)

This normalizer sums a set of user-defined detector spectra, and then divides by the sum
of a set of user-defined monitor spectra.

Published signals:
- `reducer.det_counts` - summed detector counts for the user-provided detector spectra
- `reducer.mon_counts` - summed monitor counts for the user-provided monitor spectra
- `reducer.intensity` - normalized intensity (`det_counts / mon_counts`)
- `reducer.det_counts_stddev` - uncertainty (standard deviation) of the summed detector counts
- `reducer.mon_counts_stddev` - uncertainty (standard deviation) of the summed monitor counts
- `reducer.intensity_stddev` - uncertainty (standard deviation) of the normalised intensity

### PeriodSpecIntegralsReducer

This reducer exposes the raw integrals of the configured detector and monitor spectra, as
numpy arrays. By itself, this reducer is not useful in a scan, but is useful for downstream
processing as performed by reflectometry detector-mapping alignment for
example.

Published signals:
- `reducer.mon_integrals` - `numpy` array of integrated counts on each configured monitor pixel.
- `reducer.det_integrals` - `numpy` array of integrated counts on each configured detector pixel.

### Time of Flight and Wavelength Bounding Spectra

Scalar Normalizers (such as PeriodGoodFramesNormalizer, GoodFramesNormalizer) can be passed a
summing function which can optionally sum spectra between provided time of flight or wavelength bounds.

[`PeriodGoodFramesNormalizer`](ibex_bluesky_core.devices.simpledae.PeriodGoodFramesNormalizer)


Here is an example showing creating a scalar normalizer with time of flight bounds from 15000 to 25000 μs, and summing 2 detectors:
```
import scipp

bounds=scipp.array(dims=["tof"], values=[15000.0, 25000.0], unit=scipp.units.us)

reducer = PeriodGoodFramesNormalizer(
    prefix=get_pv_prefix(),
    detector_spectra=[1, 2],
    summer=tof_bounded_spectra(bounds)
)
```

[`tof_bounded_spectra`](ibex_bluesky_core.devices.simpledae.tof_bounded_spectra)


Monitor Normalizers, which have both a monitor as well as detector, can be passed a summing function for each of these components independently, e.g. the detector can use time of flight while the monitor uses wavelength. tof_bounded_spectra assumes that all pixels being summed share the same flight-path length. Where two separate instances of tof_bounded_spectra are used, such as in DetectorMonitorNormalizer, these may have different flight path lengths from each other.

Here is an example with wavelength bounding used to sum the monitor component, and time of flight bounding for the detector summing spectra: 

```
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
[`wavelength_bounded_spectra`](ibex_bluesky_core.devices.simpledae.wavelength_bounded_spectra)


- In either case, the bounds are passed as a scipp array, which needs a `dims` attribute, `values` passed
as a list, and `units` (μs/microseconds for time of flight bounding, and angstrom for wavelength bounding)

- If you don't specify either of these options, they will default to an summing over the entire spectrum.


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

### GoodFramesWaiter

[`GoodFramesWaiter`](ibex_bluesky_core.devices.simpledae.GoodFramesWaiter)

Waits for a user-specified number of good frames (in total for the entire run)

Published signals:
- `simpledae.good_frames` - actual good frames for this run.

### PeriodGoodFramesWaiter

[`PeriodGoodFramesWaiter`](ibex_bluesky_core.devices.simpledae.PeriodGoodFramesWaiter)

Waits for a user-specified number of good frames (in the current period)

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
