from ophyd_async.core import SignalR, StandardReadable
from ophyd_async.epics.signal import epics_signal_r


class DaeEventMode(StandardReadable):
    def __init__(self, dae_prefix: str, name: str = "") -> None:
        with self.add_children_as_readables():
            self.fraction: SignalR[float] = epics_signal_r(float, f"{dae_prefix}EVENTMODEFRACTION")
            self.buf_used: SignalR[float] = epics_signal_r(float, f"{dae_prefix}EVENTMODEBUFUSED")
            self.file_size: SignalR[float] = epics_signal_r(float, f"{dae_prefix}EVENTMODEFILEMB")
            self.data_rate: SignalR[float] = epics_signal_r(float, f"{dae_prefix}EVENTMODEDATARATE")
        super().__init__(name=name)
