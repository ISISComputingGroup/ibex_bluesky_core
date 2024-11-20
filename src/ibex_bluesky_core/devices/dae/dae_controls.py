"""ophyd-async devices and utilities for the DAE run controls."""

import logging
from enum import IntFlag

from bluesky.protocols import Movable
from ophyd_async.core import AsyncStatus, SignalW, SignalX, StandardReadable
from ophyd_async.epics.signal import epics_signal_w, epics_signal_x

logger = logging.getLogger(__name__)


class DaeControls(StandardReadable):
    """Subdevice for the DAE run controls."""

    def __init__(self, dae_prefix: str, name: str = "") -> None:
        """Set up write-only signals for DAE controls."""
        self.begin_run: SignalX = epics_signal_x(f"{dae_prefix}BEGINRUN")
        self.begin_run_ex: BeginRunEx = BeginRunEx(dae_prefix)
        self.end_run: SignalX = epics_signal_x(f"{dae_prefix}ENDRUN")
        self.pause_run: SignalX = epics_signal_x(f"{dae_prefix}PAUSERUN")
        self.resume_run: SignalX = epics_signal_x(f"{dae_prefix}RESUMERUN")
        self.abort_run: SignalX = epics_signal_x(f"{dae_prefix}ABORTRUN")
        self.recover_run: SignalX = epics_signal_x(f"{dae_prefix}RECOVERRUN")
        self.save_run: SignalX = epics_signal_x(f"{dae_prefix}SAVERUN")

        super().__init__(name=name)


class BeginRunExBits(IntFlag):
    """Bits for BEGINRUNEX."""

    NONE = 0
    BEGIN_PAUSED = 1
    BEGIN_DELAYED = 2


class BeginRunEx(StandardReadable, Movable):
    """Subdevice for the BEGINRUNEX signal to begin a run."""

    def __init__(self, dae_prefix: str, name: str = "") -> None:
        """Set up write-only signal for BEGINRUNEX."""
        self._raw_begin_run_ex: SignalW[int] = epics_signal_w(int, f"{dae_prefix}BEGINRUNEX")
        super().__init__(name=name)

    @AsyncStatus.wrap
    async def set(self, value: BeginRunExBits) -> None:
        """Start a run with the specified bits - See BeginRunExBits."""
        logger.info("starting run with options %s", value)
        await self._raw_begin_run_ex.set(value, wait=True, timeout=None)
        logger.info("start run complete")
