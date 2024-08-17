from dataclasses import dataclass

from ophyd_async.core import SignalR, StandardReadable
from ophyd_async.epics.signal import epics_signal_r


@dataclass
class DaeTCBSettingsData:
    tcb_file = None
    tcb_tables = []
    tcb_calculation_method = None


class DaeTCBSettings(StandardReadable):
    def __init__(self, dae_prefix, name=""):
        super().__init__(name=name)
