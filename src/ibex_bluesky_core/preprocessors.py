"""Bluesky plan preprocessors specific to ISIS."""

import logging
from typing import Generator

from bluesky import plan_stubs as bps
from bluesky import preprocessors as bpp
from bluesky.utils import Msg, single_gen
from ophyd_async.core import SignalR
from ophyd_async.epics.signal import epics_signal_r
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.devices import get_pv_prefix

logger = logging.getLogger(__name__)


def _get_rb_number_signal() -> SignalR[str]:
    return epics_signal_r(str, f"{get_pv_prefix()}ED:RBNUMBER", name="rb_number")


def add_rb_number_processor(msg: Msg) -> tuple[Generator[Msg, None, None] | None, None]:
    """Preprocessor for adding the current RB number to the plan's metadata."""
    if msg.command == "open_run" and "rb_number" not in msg.kwargs:
        logger.info("open_run without RB number, mutating to include RB number.")

        def _before() -> Generator[Msg, None, None]:
            rb_number: SignalR[str] = _get_rb_number_signal()

            def _read_rb() -> Generator[Msg, None, str]:
                yield from ensure_connected(rb_number)
                return (yield from bps.rd(rb_number))

            def _cant_read_rb(_: Exception) -> Generator[Msg, None, str]:
                yield from bps.null()
                return "(unknown)"

            rb = yield from bpp.contingency_wrapper(
                _read_rb(), except_plan=_cant_read_rb, auto_raise=False
            )
            logger.debug("Injected RB number: %s", rb)
            return (yield from bpp.inject_md_wrapper(single_gen(msg), md={"rb_number": rb}))

        return _before(), None
    return None, None
