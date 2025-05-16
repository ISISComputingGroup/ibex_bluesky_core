"""Defines how strategies can provide interesting signals to the DAE."""

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
