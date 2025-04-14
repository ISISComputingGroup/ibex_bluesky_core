"""Base classes for DAE strategies."""

from typing import TYPE_CHECKING

from ophyd_async.core import (
    Device,
)

if TYPE_CHECKING:
    from ibex_bluesky_core.devices.simpledae import SimpleDae


class ProvidesExtraReadables:
    """Strategies may specify interesting DAE signals using this method.

    Those signals will then be added to read() and describe() on the top-level SimpleDae object.
    """

    def additional_readable_signals(self, dae: "SimpleDae") -> list[Device]:
        """Define signals that this strategy considers important.

        These will be added to the dae's default-read signals and made available by read() on the
        DAE object.
        """
        return []


class Controller(ProvidesExtraReadables):
    """Controller specifies how DAE runs should be started & stopped."""

    async def start_counting(self, dae: "SimpleDae") -> None:
        """Start counting for a single scan point."""

    async def stop_counting(self, dae: "SimpleDae") -> None:
        """Stop counting for a single scan point."""

    async def setup(self, dae: "SimpleDae") -> None:
        """Pre-scan setup."""

    async def teardown(self, dae: "SimpleDae") -> None:
        """Post-scan teardown."""


class Waiter(ProvidesExtraReadables):
    """Waiter specifies how the dae will wait for a scan point to complete counting."""

    async def wait(self, dae: "SimpleDae") -> None:
        """Wait for the acquisition to complete."""


class Reducer(ProvidesExtraReadables):
    """Reducer specifies any post-processing which needs to be done after a scan point completes."""

    async def reduce_data(self, dae: "SimpleDae") -> None:
        """Triggers a reduction of DAE data after a scan point has been measured.

        Data that should be published by this reducer should be added as soft signals, in
        a class which both implements this protocol and derives from StandardReadable.
        """
