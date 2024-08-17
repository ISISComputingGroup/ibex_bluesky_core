from dataclasses import dataclass

from ophyd_async.core import SignalR, StandardReadable
from ophyd_async.epics.signal import epics_signal_r


@dataclass
class DaePeriodSettingsData:

    periods_soft_num = None
    periods_type = None
    periods_src = None
    periods_file = None
    periods_seq = None
    periods_delay = None
    periods_settings = []


class DaePeriodSettings(StandardReadable):
    def __init__(self, dae_prefix, name=""):


        super().__init__(name=name)