from dataclasses import dataclass

from ophyd_async.core import SignalR, StandardReadable
from ophyd_async.epics.signal import epics_signal_r

@dataclass
class DaeSettingsData:
    wiring = None
    detector = None
    spectra = None
    mon_spect = None
    mon_from = None
    mon_to = None
    dae_sync = None
    smp_veto = None
    ts2_veto = None
    hz50_veto = None
    ext0_veto = None
    ext1_veto = None
    ext2_veto = None
    ext3_veto = None
    fermi_veto = None
    fermi_delay = None
    fermi_width = None


class DaeSettings(StandardReadable):
    def __init__(self, dae_prefix, name=""):


        super().__init__(name=name)
