"""ophyd-async devices and utilities for the DAE run controls."""

import logging
from enum import IntFlag

from bluesky.protocols import Movable
from ophyd_async.core import AsyncStatus, SignalW, SignalX, StandardReadable
from ophyd_async.epics.core import epics_signal_w, epics_signal_x

logger = logging.getLogger(__name__)


class DaeControls(StandardReadable):
    """DAE run control signals."""

    def __init__(self, dae_prefix: str, name: str = "") -> None:
        """DAE run controls, for example to begin and end runs."""
        self.begin_run: SignalX = epics_signal_x(f"{dae_prefix}BEGINRUN")
        """
        Begin a run.
        """
        self.begin_run_ex: BeginRunEx = BeginRunEx(dae_prefix)
        """
        Begin a run, with options.
        """
        self.end_run: SignalX = epics_signal_x(f"{dae_prefix}ENDRUN")
        """
        End a run.
        """
        self.pause_run: SignalX = epics_signal_x(f"{dae_prefix}PAUSERUN")
        """
        Pause the current run.
        """
        self.resume_run: SignalX = epics_signal_x(f"{dae_prefix}RESUMERUN")
        """
        Resume the current run.
        """
        self.abort_run: SignalX = epics_signal_x(f"{dae_prefix}ABORTRUN")
        """
        Abort the current run (does not save data files).
        """
        self.recover_run: SignalX = epics_signal_x(f"{dae_prefix}RECOVERRUN")
        """
        Recover a previously-aborted run.
        """
        self.save_run: SignalX = epics_signal_x(f"{dae_prefix}SAVERUN")
        """
        Save a data file for the current run (equivalent to update & store).
        """
        self.update_run: SignalX = epics_signal_x(f"{dae_prefix}UPDATERUN")
        """
        Ensure that data in the DAE has been downloaded to the ICP.
        """
        self.store_run: SignalX = epics_signal_x(f"{dae_prefix}STORERUN")
        """
        Write data currently in-memory in the ICP to a data file.
        """

        super().__init__(name=name)


class BeginRunExBits(IntFlag):
    """Bit-flags for :py:obj:`BeginRunEx`.

    These flags control behaviour such as beginning in 'paused' mode.
    """

    NONE = 0
    """
    Begin a run in the standard way.
    """

    BEGIN_PAUSED = 1
    """
    Begin a run in the 'paused' state.
    """

    BEGIN_DELAYED = 2
    """
    Allow 'delayed' begin commands.
    """


class BeginRunEx(StandardReadable, Movable[BeginRunExBits]):
    """Subdevice for the ``BEGINRUNEX`` signal to begin a run."""

    def __init__(self, dae_prefix: str, name: str = "") -> None:
        """Set up write-only signal for ``BEGINRUNEX``."""
        self._raw_begin_run_ex: SignalW[int] = epics_signal_w(int, f"{dae_prefix}BEGINRUNEX")
        super().__init__(name=name)

    @AsyncStatus.wrap
    async def set(self, value: BeginRunExBits) -> None:
        """Start a run with the specified behaviour flags.

        See Also:
            :py:obj:`BeginRunExBits` for a description of the behaviour flags.

        """
        logger.info("starting run with options %s", value)
        await self._raw_begin_run_ex.set(value, wait=True, timeout=None)
        logger.info("start run complete")
