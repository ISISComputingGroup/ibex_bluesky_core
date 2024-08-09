from bluesky.protocols import Triggerable, Status
from ophyd_async.epics.signal import  epics_signal_x
import asyncio
from ophyd_async.core import AsyncStatus, SignalX
from ophyd_async.core import Device, StandardReadable


class DaeControls(StandardReadable):
    def __init__(self, dae_prefix, name=""):
        self.begin_run: SignalX = epics_signal_x(f"{dae_prefix}BEGINRUN")
        self.end_run: SignalX = epics_signal_x(f"{dae_prefix}ENDRUN")
        self.pause_run: SignalX = epics_signal_x(f"{dae_prefix}PAUSERUN")
        self.resume_run: SignalX = epics_signal_x(f"{dae_prefix}RESUMERUN")
        self.abort_run: SignalX = epics_signal_x(f"{dae_prefix}ABORTRUN")

        super().__init__(name=name)
