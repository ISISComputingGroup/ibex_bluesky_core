"""Device for IBEX manager mode."""

from bluesky.protocols import NamedMovable
from ophyd_async.core import AsyncStatus, StandardReadable, StandardReadableFormat, StrictEnum
from ophyd_async.epics.core import epics_signal_rw

from ibex_bluesky_core.utils import get_pv_prefix


class ManagerModeChoices(StrictEnum):
    """Choices for the manager mode PV."""

    NO = "No"
    YES = "Yes"


class ManagerMode(StandardReadable, NamedMovable[ManagerModeChoices]):
    """Device for setting the IBEX manager mode."""

    def __init__(self, prefix: str) -> None:
        """Device for setting the IBEX manager mode.

        Args:
            prefix: The PV prefix to use.

        """
        with self.add_children_as_readables(StandardReadableFormat.HINTED_SIGNAL):
            self.mode = epics_signal_rw(ManagerModeChoices, f"{prefix}CS:MANAGER")
        super().__init__()

    @AsyncStatus.wrap
    async def set(self, value: ManagerModeChoices) -> None:
        """Set the manager mode value.

        Args:
            value: The new manager mode value.

        """
        await self.mode.set(value)


def manager_mode() -> ManagerMode:
    """Get a device for manager mode of the current instrument."""
    prefix = get_pv_prefix()
    return ManagerMode(prefix)
