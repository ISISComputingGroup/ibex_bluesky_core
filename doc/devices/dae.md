# DAE

## DaeBase (base class)

`Dae` is the principal class in ibex_bluesky_core which exposes configuration settings
and controls from the ISIS data acquisition electronics (DAE).

```{note}
 The `Dae` class is not intended to be used directly in scans - it is a low-level class
 which directly exposes functionality from the DAE, but has no scanning functionality by
 itself.
 
 It is intended that this object is only used directly when:
 - Configuring DAE settings within a plan.
 - For advanced use-cases, if arbitrary DAE control is required from a plan - but note 
   that it will usually be better to implement functionality at the device level rather 
   than the plan level.
 
 For other use-cases, a user-facing DAE class is likely to be more appropriate to use
 as a detector in a scan - this class cannot be used by itself.
```

## Top-level signals

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

## Period-specific signals

For signals which apply to the current period, see `dae.period`, which contains signals
such as `dae.period.good_uah` (the number of good uamp-hours collected in the current period).


## Controlling the DAE directly

It is possible to control the DAE directly using the signals provided by `dae.controls`.

The intention is that these signals should be used by higher-level _devices_, rather than being
used by plans directly.

For example, beginning a run is possible via `dae.controls.begin_run.trigger()`.

### Advanced options

Options on `begin` (for example, beginning a run in paused mode) can be specified
using the `dae.controls.begin_run_ex` signal.

Unlike the standard `begin_run` signal, this needs to be `set()` rather than simply
`trigger()`ed, the value on set is a combination of flags from `BeginRunExBits`.


## DAE Settings

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


## DAE Spectra

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
