# DAE Settings

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