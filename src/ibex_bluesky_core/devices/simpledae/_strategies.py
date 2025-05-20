from ophyd_async.core import Device

from ibex_bluesky_core.devices.dae import Dae


class ProvidesExtraReadables:
    """Strategies may specify interesting DAE signals using this method.

    Those signals will then be added to read() and describe() on the top-level SimpleDae object.
    """

    def additional_readable_signals(self, dae: Dae) -> list[Device]:
        """Define signals that this strategy considers important.

        These will be added to the dae's default-read signals and made available by read() on the
        DAE object.
        """
        return []



class Waiter(ProvidesExtraReadables):
    """Waiter specifies how the dae will wait for a scan point to complete counting."""

    async def wait(self, dae: Dae) -> None:
        """Wait for the acquisition to complete."""


class Controller(ProvidesExtraReadables):
    """Controller specifies how DAE runs should be started & stopped.

    Controller specifies how DAE runs should be started & stopped.

    .. py:class:: Controller:
        :canonical: ibex_bluesky_core.devices.dae.strategies.Controller:
    """

    async def start_counting(self, dae: Dae) -> None:
        """Start counting for a single scan point."""

    async def stop_counting(self, dae: Dae) -> None:
        """Stop counting for a single scan point."""

    async def setup(self, dae: Dae) -> None:
        """Pre-scan setup."""

    async def teardown(self, dae: Dae) -> None:
        """Post-scan teardown."""


class Reducer(ProvidesExtraReadables):
    """Reducer specifies any post-processing which needs to be done after a scan point completes."""

    async def reduce_data(self, dae: Dae) -> None:
        """Triggers a reduction of DAE data after a scan point has been measured.

        Data that should be published by this reducer should be added as soft signals, in
        a class which both implements this protocol and derives from StandardReadable.
        """