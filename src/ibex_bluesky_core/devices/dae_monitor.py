from ophyd_async.core import SignalR, StandardReadable
from ophyd_async.epics.signal import epics_signal_r


class DaeMonitor(StandardReadable):
    def __init__(self, dae_prefix, name=""):
        with self.add_children_as_readables():
            self.spectrum: SignalR[int] = epics_signal_r(int, f"{dae_prefix}MONITORCOUNTS")
            self.counts: SignalR[int] = epics_signal_r(int, f"{dae_prefix}MONITORSPECTRUM")
            self.to: SignalR[float] = epics_signal_r(float, f"{dae_prefix}MONITORTO")
            self.from_: SignalR[float] = epics_signal_r(float, f"{dae_prefix}MONITORFROM")

        super().__init__(name=name)
