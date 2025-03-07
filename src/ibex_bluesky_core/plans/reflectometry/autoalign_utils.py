from dataclasses import dataclass, field
from itertools import chain
from pathlib import Path
from typing import Callable, NotRequired, TypedDict, Unpack
import bluesky.plans as bp
import bluesky.plan_stubs as bps
from bluesky.utils import Msg
from collections.abc import Generator
from lmfit.model import ModelResult
from ibex_bluesky_core.callbacks import ISISCallbacks as ICC
from ibex_bluesky_core.callbacks.fitting import FitMethod
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import BlockR, BlockRw
from ibex_bluesky_core.devices.reflectometry.refl_param import ReflParameter
from ibex_bluesky_core.devices.simpledae import SimpleDae
from datetime import datetime
from matplotlib.axes import Axes

FILE_OUTPUT_DIR = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files"


@dataclass
class AlignmentParam:
    name: str
    rel_scan_ranges: list[float]
    fit_method: FitMethod
    fit_param: str
    pre_align_param_positions: dict[str, float] = field(default_factory=dict)
    do_checks: Callable[[ModelResult, float], bool] | None = None
    _pos: float = 0.0
    _prefix: str = get_pv_prefix()
    _alignment_param: ReflParameter | BlockRw[float] | None = None

    def get_signal(self):
        if not self._alignment_param:
            self._alignment_param = ReflParameter(prefix=self._prefix, name=self.name)
        return self._alignment_param

    def pre_align_params(
        self,
        alignment_params: list["AlignmentParam"],
    ) -> Generator[Msg, None, None]:
        yield from bps.mv(
            *chain(
                *[
                    (p.get_signal(), self.pre_align_param_positions[p.name])
                    for p in alignment_params
                ]
            )  # type: ignore
        )


def _add_fields(
    fields: list[str],
    dae: SimpleDae | BlockR[float],
    periods: bool,
    save_run: bool,
    alignment_param_name: str,
) -> list[str]:
    if fields is []:
        if type(dae) is SimpleDae:
            fields.append(
                [
                    dae.reducer.intensity.name,  # type: ignore
                    dae.reducer.intensity_stddev.name,  # type: ignore
                ]
            )

            if periods:
                fields.append(dae.period_num.name)  # type: ignore
            elif save_run:
                fields.append(dae.controller.run_number.name)  # type: ignore

        else:
            fields.append(dae.name)

        fields.append(alignment_param_name)

    return fields


def _check_parameter(
    alignment_param_value: float,
    result: ModelResult,
    init_mot_pos: float,
    rel_scan_range: float,
    user_checks: Callable[[ModelResult, float], bool] | None, # True means problem found.
) -> bool:
    # Check that found param is within scan range. True means problem.

    if init_mot_pos + rel_scan_range < alignment_param_value:
        return True

    elif init_mot_pos - rel_scan_range > alignment_param_value:
        return True

    if user_checks is None:
        return False
    return user_checks(result, alignment_param_value)


def _inner_loop(
    icc: ICC,
    dae: SimpleDae | BlockR[float],
    alignment_param: AlignmentParam,
    rel_scan_range: float,
    num_points: int,
    callback_if_problem: Callable[[], Generator[Msg, None, None]] | Callable[[], None],
) -> Generator[Msg, None, bool]:
    print(f"Scanning over {alignment_param.name} with a relative scan range of {rel_scan_range}.")

    init_mot_pos: float = yield from bps.rd(alignment_param.get_signal())

    @icc
    def _inner() -> Generator[Msg, None, None]:
        yield from bp.rel_scan(
            [dae],
            alignment_param.get_signal(),
            -rel_scan_range,
            rel_scan_range,
            num=num_points,
        )

    yield from _inner()

    found_problem = True
    if icc.live_fit.result is not None:
        print(icc.live_fit.result.fit_report())
        print(f"Files written to {FILE_OUTPUT_DIR}\n")
        alignment_param_value = icc.live_fit.result.values[alignment_param.fit_param]

        found_problem = _check_parameter(
            alignment_param_value=alignment_param_value,
            result=icc.live_fit.result,
            init_mot_pos=init_mot_pos,
            rel_scan_range=rel_scan_range,
            user_checks=alignment_param.do_checks,
        )

    if found_problem:
        if type(callback_if_problem) is Callable[[], Generator[Msg, None, None]]:
            yield from callback_if_problem()
        else:
            callback_if_problem()

        print(
            f"This failed one or more of the checks on {alignment_param.name} with a scan range of {rel_scan_range}."
        )
        print(f"Value found for {alignment_param.fit_param} was {alignment_param_value}.")
        input("Check your setup and checking function then press enter to go again...")

        return True

    else:
        print(f"Moving {alignment_param.name} to {alignment_param_value} and rezeroing...")
        yield from bps.mv(alignment_param.get_signal(), alignment_param_value)  # type: ignore
        # redefine motor pos to be 0 TODODDDDDDDDDDDDDDODODODOD!!!!!!!!!!!!!!!!!!!!!!!!!
        return False


class OptimiseAxisParams(TypedDict):
    num_points: NotRequired[int]
    fields: NotRequired[list[str]]
    periods: NotRequired[bool]
    save_run: NotRequired[bool]
    files_output_dir: NotRequired[Path]
    callback_if_problem: NotRequired[Callable[[], Generator[Msg, None, None]] | Callable[[], None]]
    callback_pre_align: NotRequired[Callable[[], Generator[Msg, None, None]] | Callable[[], None]]
    callback_post_align: NotRequired[Callable[[], Generator[Msg, None, None]] | Callable[[], None]]
    ax: NotRequired[Axes | None]


def optimise_axis_against_intensity(
    dae: SimpleDae | BlockR[float],
    alignment_param: AlignmentParam,
    **kwargs: Unpack[OptimiseAxisParams],
) -> Generator[Msg, None, ModelResult | None]:
    num_points = kwargs.get("num_points", 10)
    fields = kwargs.get("fields", [])
    periods = kwargs.get("periods", True)
    save_run = kwargs.get("save_run", True)
    files_output_dir = kwargs.get("files_output_dir", FILE_OUTPUT_DIR)
    callback_if_problem = kwargs.get("callback_if_problem", lambda: None)
    callback_pre_align = kwargs.get("callback_pre_align", lambda: None)
    callback_post_align = kwargs.get("callback_post_align", lambda: None)
    ax = kwargs.get("ax", None)

    fields = _add_fields(
        fields,
        dae=dae,
        periods=periods,
        save_run=save_run,
        alignment_param_name=alignment_param.name,
    )
    postfix = f"{alignment_param.name}_{datetime.now().strftime('%H%M%S')}"
    yerr = dae.reducer.intensity_stddev.name if type(dae) is SimpleDae else None  # type: ignore

    icc = ICC(
        x=alignment_param.name,
        y=dae.name,
        yerr=yerr,
        measured_fields=fields,
        live_fit_logger_output_dir=files_output_dir,
        human_readable_file_output_dir=files_output_dir,
        fields_for_hr_file=fields,
        fit=alignment_param.fit_method,
        live_fit_logger_postfix=postfix,
        ax=ax,
    )

    if type(callback_pre_align) is Callable[[], Generator[Msg, None, None]]:
        yield from callback_pre_align()
    else:
        callback_pre_align()

    problem_loop = True
    while problem_loop:
        problem_loop = False

        for rel_scan_range in alignment_param.rel_scan_ranges:
            problem_loop = yield from _inner_loop(
                icc,
                dae,
                alignment_param,
                rel_scan_range,
                num_points,
                callback_if_problem,
            )

    if type(callback_post_align) is Callable[[], Generator[Msg, None, None]]:
        yield from callback_post_align()
    else:
        callback_post_align()

    return icc.live_fit.result
