from collections.abc import Generator
from dataclasses import dataclass, field
from datetime import datetime
from itertools import chain
from pathlib import Path
from typing import Callable, NotRequired, TypedDict, Unpack

import bluesky.plan_stubs as bps
import bluesky.plans as bp
from bluesky.utils import Msg
from lmfit.model import ModelResult
from matplotlib.axes import Axes

from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.callbacks.fitting import FitMethod
from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.block import BlockR, BlockRw
from ibex_bluesky_core.devices.reflectometry.refl_param import ReflParameter
from ibex_bluesky_core.devices.simpledae import SimpleDae

FILE_OUTPUT_DIR = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files"


@dataclass
class AlignmentParam:
    """Encapsulates information that is specific to each device/motor that needs optimising.

    Args:
        name (str): The name of the alignment parameter.
            Should be same as the respective relectometry parameter.
        rel_scan_ranges (list[float]): Scan range relative to the current motor position.
            If the list has more than one element then it will rescan for each range.
        fit_method (FitMethod): The relationship to expect between the alignment parameter
            and the beam. e.g Gaussian.
        fit_param (str): Which property of fit_method you aim to optimise. e.g centre (x0)
            of a Gaussian. See fitting/fitting_utils for the possible options for each fitting
            method.
        pre_align_param_positions (dict[str, float], optional): A dictionary of alignment
            parameter names to values. Before alignment, each supplied alignment parameter
            will be moved to their respective value.
        do_checks (Callable[[ModelResult, float], bool]): Checks to ensure that the optimised
            value for this alignment parameter is sensible, must return True if NOT a sensible
            value.
        _prefix (str): The PV prefix for the respective reflectometry parameter. Defaults to
            the current instrument PV prefix.
        _alignment_param (ReflParameter, BlockRw[float]): A reflectometry parameter or block
            read/write signal. Use this if you want to create your own signal.

    """

    name: str
    rel_scan_ranges: list[float]
    fit_method: FitMethod
    fit_param: str
    pre_align_param_positions: dict[str, float] = field(default_factory=dict)
    do_checks: Callable[[ModelResult, float], bool] | None = None
    _prefix: str = get_pv_prefix()
    _alignment_param: ReflParameter | BlockRw[float] | None = None

    def get_signal(self) -> ReflParameter | BlockRw[float]:
        """Returns the encapsulated signal for this alignment parameter.

        If there is no signal attached then one is created as a reflectometry parameter.

        Returns:
            signal (ReflParameter | BlockRw[float])
        """

        if not self._alignment_param:
            self._alignment_param = ReflParameter(prefix=self._prefix, name=self.name)

        return self._alignment_param

    def pre_align_params(
        self,
        alignment_params: list["AlignmentParam"],
    ) -> Generator[Msg, None, None]:
        """Moves the provided alignment parameters to their respective values in
        self.pre_align_param_positions.

        Args:
            alignment_params (list[AlignmentParam]): The alignment parameters to be moved.
        """

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
    """If no fields are supplied then use a standard set.

    Args:
        fields (list[str]): The fields to be added to.
        dae (SimpleDae | BlockR[float]): A readable signal.
        periods (bool): Are periods being used.
        save_run (bool): Should runs be saved.
        alignment_param_name (str): The name of the alignment parameter.
            Should be same as the respective relectometry parameter.

    Returns:
        fields (list[str])
    """

    if fields == []:
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
    user_checks: Callable[[ModelResult, float], bool] | None,
) -> bool:
    """Check that the optimised value is within scan range and then runs user provided checks.

    Returns True means the found result was not sensible.

    Args:
        alignment_param_value (float): The optimised value.
        result (ModelResult): The fitting resuls returned from lmfit.
        init_mot_pos (float): The initial motor position before scanning.
        rel_scan_range (float): The current relative scan range.
        user_checks (Callable[[ModelResult, float], bool] | None): User provided checks on the
            optimised value, must return True if result is not sensible.

    Returns:
        True if value is not sensible. False otherwise.
    """

    if init_mot_pos + rel_scan_range < alignment_param_value:
        return True

    elif init_mot_pos - rel_scan_range > alignment_param_value:
        return True

    if user_checks is None:
        return False

    return user_checks(result, alignment_param_value)


def _inner_loop(
    icc: ISISCallbacks,
    dae: SimpleDae | BlockR[float],
    alignment_param: AlignmentParam,
    rel_scan_range: float,
    num_points: int,
    callback_if_problem: Callable[[], Generator[Msg, None, None]] | Callable[[], None],
) -> Generator[Msg, None, bool]:
    """Functionality to perform on a per scan basis.

    Args:
        ISISCallbacks (ISISCallbacks): ISIS Callback Collection object.
        dae (SimpleDae | BlockR[float]): A readable signal.
        alignment_param (AlignmentParam): The alignment parameter to be scanned over and optimised.
        rel_scan_range (float): The current relative scan range.
        num_points (int): The number of points across the scan.
        callback_if_problem (Callable[[], Generator[Msg, None, None]] | Callable[[], None]):
            A callback for what to do if the optimised value is not found to be sensible.

    Returns:
        Whether there was a problem during runtime (bool).
    """

    print(f"Scanning over {alignment_param.name} with a relative scan range of {rel_scan_range}.")

    init_mot_pos: float = yield from bps.rd(alignment_param.get_signal())
    found_problem = True
    alignment_param_value = None

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
            yield from callback_if_problem()  # type: ignore
        else:
            callback_if_problem()

        print(
            f"""This failed one or more of the checks on {alignment_param.name}
             with a scan range of {rel_scan_range}."""
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
    """Optimise a motor/device to the intensity of the beam.

    Scan between two symmetrical points relative to alignment_param's current motor position,
    to find where the point of hightest beam intensity, move to it, then optionally repeat
    the process for a smaller range and higher granularity.

    Args:
        dae (SimpleDae | BlockR[float]): A readable signal that represents beam intensity.
        alignment_param (AlignmentParam): The alignment parameter to be scanned over and optimised.
        kwargs:
            num_points (int): The number of points across the scan. Defaults to 10.
            fields (list[str]): Fields to measure and document in outputted files.
            periods (bool): Are periods being used. Defaults to True.
            save_run (bool): Should runs be saved. Defaults to True.
            files_output_dir (Path): Where to save any outputted files. Defaults to
                C:/instrument/var/logs/bluesky/output_files.
            callback_if_problem (Callable[[], Generator[Msg, None, None]] | Callable[[], None]):
                Either a plan or standard function, called if optimised value is not found to be
                sensible.
            callback_pre_align (Callable[[], Generator[Msg, None, None]] | Callable[[], None]):
                Either a plan or standard function, called before all scans.
            callback_pre_align (Callable[[], Generator[Msg, None, None]] | Callable[[], None]):
                Either a plan or standard function, called after all scans.
            ax (matplotlib.axes.Axes): The Axes to plot points and fits to.

    Returns:
        An lmfit fitting result or nothing (ModelResult | None)
    """

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

    icc = ISISCallbacks(
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
        yield from callback_pre_align()  # type: ignore
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
        yield from callback_post_align()  # type: ignore
    else:
        callback_post_align()

    return icc.live_fit.result
