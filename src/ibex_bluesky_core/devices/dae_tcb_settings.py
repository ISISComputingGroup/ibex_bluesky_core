from dataclasses import dataclass

from ophyd_async.core import SignalRW, StandardReadable

from ibex_bluesky_core.utils.isis_epics_signals import isis_epics_signal_rw


@dataclass
class DaeTCBSettingsData:
    tcb_file = None
    tcb_tables = []
    tcb_calculation_method = None


class DaeTCBSettings(StandardReadable):
    def __init__(self, dae_prefix, name=""):
        with self.add_children_as_readables():
            self.tcb_settings: SignalRW[str] = isis_epics_signal_rw(str, f"{dae_prefix}TCBSETTINGS")
        super().__init__(name=name)
