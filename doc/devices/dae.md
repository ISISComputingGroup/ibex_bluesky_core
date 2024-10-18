# DAE (Data Acquisition Electronics)

The `SimpleDae` class is designed to be a configurable DAE object, which will cover the
majority of DAE use-cases within bluesky.

This class uses several objects to configure its behaviour:
- The `Controller` is responsible for beginning and ending acquisitions.
- The `Waiter` is responsible for waiting for an acquisition to be "complete".
- The `Reducer` is responsible for publishing data from an acquisition that has 
  just been completed.

This means that `SimpleDae` is generic enough to cope with most typical DAE use-casess, for
example running using either one DAE run per scan point, or one DAE period per scan point.

For complex use-cases, particularly those where the DAE may need to start and stop multiple 
acquisitions per scan point (e.g. polarization measurements), `SimpleDae` is unlikely to be 
suitable; instead the `Dae` class should be subclassed directly to allow for finer control.

## Example configurations

### Run-per-point

```python
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import RunPerPointController
from ibex_bluesky_core.devices.simpledae.waiters import GoodFramesWaiter
from ibex_bluesky_core.devices.simpledae.reducers import GoodFramesNormalizer


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
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import PeriodPerPointController
from ibex_bluesky_core.devices.simpledae.waiters import PeriodGoodFramesWaiter
from ibex_bluesky_core.devices.simpledae.reducers import PeriodGoodFramesNormalizer


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

`SimpleDae` will call `controller.setup()` to allow any pre-scan setup to be done.

For example, this is where the period-per-point controller object will begin a DAE run.

### Each scan point (`trigger`)

`SimpleDae` will call:
- `controller.start_counting()` to begin counting for a single scan point.
- `waiter.wait()` to wait for that acquisition to complete
- `controller.stop_counting()` to finish counting for a single scan point.
- `reducer.reduce_data()` to do any necessary post-processing on 
  the raw DAE data (e.g. normalization)

### Each scan point (`read`)

Any signals marked as "interesting" by the controller, reducer or waiter will be published
in the top-level documents published when `read()`ing the `SimpleDae` object.

These may correspond to EPICS signals directly from the DAE (e.g. good frames), or may be 
soft signals derived at runtime (e.g. normalized intensity).

This means that the `SimpleDae` object is suitable for use as a detector in most bluesky
plans, and will make an appropriate set of data available in the emitted documents.

### End of scan (`unstage`)

`SimpleDae` will call `controller.teardown()` to allow any post-scan teardown to be done.

For example, this is where the period-per-point controller object will end a DAE run.

## Controllers

The `Controller` class is responsible for starting and stopping acquisitions, in a generic
way.

### RunPerPointController

This controller starts and stops a new DAE run for each scan point. It can be configured to 
either end runs or abort them on completion.

This controller causes the following signals to be published by `SimpleDae`:

- `controller.run_number` - The run number into which data was collected. Only published 
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

The controller causes the following signals to be published by `SimpleDae`:

- `simpledae.period_num` - the period number into which this scan point was counted.

## Reducers

A `Reducer` for a `SimpleDae` is responsible for publishing any data derived from the raw
DAE signals. For example, normalizing intensities are implemented as a reducer.

A reducer may produce any number of reduced signals.

### GoodFramesNormalizer

This normalizer sums a set of user-defined detector spectra, and then divides by the number
of good frames.

Published signals:
- `simpledae.good_frames` - the number of good frames reported by the DAE
- `reducer.det_counts` - summed detector counts for all of the user-provided spectra
- `reducer.intensity` - normalized intensity (`det_counts / good_frames`)
- `reducer.det_counts_stddev` - uncertainty (standard deviation) of the summed detector counts
- `reducer.intensity_stddev` - uncertainty (standard deviation) of the normalised intensity

### PeriodGoodFramesNormalizer

Equivalent to the `GoodFramesNormalizer` above, but uses good frames only from the current
period. This should be used if a controller which counts into multiple periods is being used.

Published signals:
- `simpledae.period.good_frames` - the number of good frames reported by the DAE
- `reducer.det_counts` - summed detector counts for all of the user-provided spectra
- `reducer.intensity` - normalized intensity (`det_counts / good_frames`)
- `reducer.det_counts_stddev` - uncertainty (standard deviation) of the summed detector counts
- `reducer.intensity_stddev` - uncertainty (standard deviation) of the normalised intensity

### DetectorMonitorNormalizer

This normalizer sums a set of user-defined detector spectra, and then divides by the sum
of a set of user-defined monitor spectra.

Published signals:
- `reducer.det_counts` - summed detector counts for the user-provided detector spectra
- `reducer.mon_counts` - summed monitor counts for the user-provided monitor spectra
- `reducer.intensity` - normalized intensity (`det_counts / mon_counts`)
- `reducer.det_counts_stddev` - uncertainty (standard deviation) of the summed detector counts
- `reducer.mon_counts_stddev` - uncertainty (standard deviation) of the summed monitor counts
- `reducer.intensity_stddev` - uncertainty (standard deviation) of the normalised intensity

## Waiters

A `waiter` defines an arbitrary strategy for how long to count at each point.

Some waiters may be very simple, such as waiting for a fixed amount of time or for a number
of good frames or microamp-hours. However, it is also possible to define much more 
sophisticated waiters, for example waiting until sufficient statistics have been collected.

### GoodUahWaiter

Waits for a user-specified number of microamp-hours.

Published signals:
- `simpledae.good_uah` - actual good uAh for this run.

### GoodFramesWaiter

Waits for a user-specified number of good frames (in total for the entire run)

Published signals:
- `simpledae.good_frames` - actual good frames for this run.

### GoodFramesWaiter

Waits for a user-specified number of good frames (in the current period)

Published signals:
- `simpledae.period.good_frames` - actual period good frames for this run.

### MEventsWaiter

Waits for a user-specified number of millions of events

Published signals:
- `simpledae.m_events` - actual period good frames for this run.

### TimeWaiter

Waits for a user-specified time duration, irrespective of DAE state.

Does not publish any additional signals.

---

## `Dae` (base class, advanced)

`Dae` is the principal class in ibex_bluesky_core which exposes configuration settings
and controls from the ISIS data acquisition electronics (DAE). `SimpleDae` derives from
DAE, so all of the signals available on `Dae` are also available on `SimpleDae`.

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
for example `dae.title` or `dae.good_uah`.

These signals are directly readable and settable from plans:

```python
import bluesky.plan_stubs as bps
from ibex_bluesky_core.devices.dae.dae import Dae

def plan(dae: Dae):
    current_title = yield from bps.rd(dae.title)
    yield from bps.mv(dae.title, "new title")
```

### Period-specific signals

For signals which apply to the current period, see `dae.period`, which contains signals
such as `dae.period.good_uah` (the number of good uamp-hours collected in the current period).


### Controlling the DAE directly

It is possible to control the DAE directly using the signals provided by `dae.controls`.

The intention is that these signals should be used by higher-level _devices_, rather than being
used by plans directly.

For example, beginning a run is possible via `dae.controls.begin_run.trigger()`.

### Additional begin_run flags

Options on `begin` (for example, beginning a run in paused mode) can be specified
using the `dae.controls.begin_run_ex` signal.

Unlike the standard `begin_run` signal, this needs to be `set()` rather than simply
`trigger()`ed, the value on set is a combination of flags from `BeginRunExBits`.


### DAE Settings

Many signals on the DAE are only available as composite signals - this includes most DAE 
configuration parameters which are available under the "experiment setup" tab in IBEX, for
example wiring/detector/spectra tables, tcb settings, or vetos.

The classes implemented in this way are:
- `DaeTCBSettings` (`dae.tcb_settings`)
  - Parameters which appear under the "time channels" tab in IBEX
- `DaeSettings` (`dae.dae_settings`)
  - Parameters which appear under the "data acquisition" tab in IBEX
- `DaePeriodSettings` (`dae.period_settings`): 
  - Parameters which appear under the "periods" tab in IBEX

To read or change these settings from plans, use the associated dataclasses, which are
suffixed with `Data` (e.g. `DaeSettingsData` is the dataclass corresponding to `DaeSettings`):

```python
import bluesky.plan_stubs as bps
from ibex_bluesky_core.devices.dae.dae import Dae
from ibex_bluesky_core.devices.dae.dae_settings import DaeSettingsData

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

Raw spectra are provided by the `DaeSpectra` class. Not all spectra are automatically available
on the base DAE object - user classes will define the specific set of spectra which they are
interested in.

A `DaeSpectrum` object provides 3 arrays:
- `tof` (x-axis): time of flight.
- `counts` (y-axis): number of counts
  - Suitable for summing counts
  - Will give a discontinuous plot if plotted directly and bin widths are non-uniform.
- `counts_per_time` (y-axis): number of counts normalized by bin width
  - Not suitable for summing counts directly
  - Gives a continuous plot when plotted against x directly.

The `Dae` base class does not provide any spectra by default. User-level classes should specify 
the set of spectra which they are interested in.
