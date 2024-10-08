from typing import Generator

from bluesky import Msg, plan_stubs as bps, preprocessors as bpp
from ophyd_async.epics.signal import epics_signal_r
from ophyd_async.plan_stubs import ensure_connected

from ibex_bluesky_core.devices import get_pv_prefix


def add_rb_number_processor(msg: Msg) -> tuple[Generator[Msg, None, None] | None, None]:
    if msg.command == "open_run" and "rb_number" not in msg.kwargs:

        def _before() -> Generator[Msg, None, None]:
            rb_number = epics_signal_r(str, f"{get_pv_prefix()}ED:RBNUMBER", name="rb_number")

            def _read_rb() -> Generator[Msg, None, str]:
                yield from ensure_connected(rb_number)
                return (yield from bps.rd(rb_number))

            def _cant_read_rb(e: Exception) -> Generator[Msg, None, str]:
                yield from bps.null()
                return "(unknown)"

            rb = yield from bpp.contingency_wrapper(
                _read_rb(), except_plan=_cant_read_rb, auto_raise=False
            )
            return (yield from bpp.inject_md_wrapper(bpp.single_gen(msg), md={"rb_number": rb}))

        return _before(), None
    return None, None
