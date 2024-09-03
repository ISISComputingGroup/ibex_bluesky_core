from ophyd_async.core import SignalR, StandardReadable
from ophyd_async.epics.signal import epics_signal_r
import numpy as np

class DaeSpectra(StandardReadable):
    def __init__(self, dae_prefix, *, spectra, period, name=""):
        self.x: SignalR[np.typing.NDArray[np.float32]] = epics_signal_r(
            np.typing.NDArray[np.float32], f"{dae_prefix}DAE" f":SPEC:{period}:{spectra}:X"
        )
        self.y: SignalR[np.typing.NDArray[np.float32]] = epics_signal_r(
            np.typing.NDArray[np.float32], f"{dae_prefix}DAE" f":SPEC:{period}:{spectra}:Y"
        )
        self.yc: SignalR[np.typing.NDArray[np.float32]] = epics_signal_r(
            np.typing.NDArray[np.float32], f"{dae_prefix}DAE" f":SPEC:{period}:{spectra}:YC"
        )
        super().__init__(name=name)
