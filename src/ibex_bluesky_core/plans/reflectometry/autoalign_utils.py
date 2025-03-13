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
from ibex_bluesky_core.devices.reflectometry import ReflParameter
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.utils import get_pv_prefix

FILE_OUTPUT_DIR = Path("C:\\") / "instrument" / "var" / "logs" / "bluesky" / "output_files"


@dataclass
class AlignmentParam:
    """Encapsulates information that is specific to each device/motor that needs optimising.

    Args:
        name (str): The name of the alignment parameter.
            Should be same as the respective relectometry parameter or read/write block.
        rel_scan_ranges (list[float]): Scan range relative to the current motor position.
            If the list has more than one element then it will rescan for each range.
            Scans between mot_pos - rel_scan_range / 2 -> mot_pos + rel_scan_range / 2
        fit_method (FitMethod): The relationship to expect between the alignment parameter
            and the beam. e.g Gaussian.
        fit_param (str): Which property of fit_method you aim to optimise. e.g centre (x0)
            of a Gaussian. See fitting/fitting_utils for the possible options for each fitting
            method.
        pre_align_param_positions (dict[str, float], optional): A dictionary of alignment
            parameter names to values. Before alignment, each supplied alignment parameter
            will be moved to their respective value.
        check_func (Callable[[ModelResult, float], bool], optional): Checks to ensure that the
            optimised value for this alignment parameter is sensible, must return True if NOT
            a sensible value.
        _prefix (str, optional): The PV prefix for the respective reflectometry parameter.
            Defaults to the current instrument PV prefix.
        _movable (ReflParameter, optional): A reflectometry parameter or block
            read/write signal. Use this if you want to create your own signal.

    """

    name: str
    rel_scan_ranges: list[float]
    fit_method: FitMethod
    fit_param: str
    pre_align_param_positions: dict[str, float] = field(default_factory=dict)
    check_func: Callable[[ModelResult, float], bool] | None = None
    _prefix: str = get_pv_prefix()
    _movable: ReflParameter | None = None

    def get_movable(self) -> ReflParameter:
        """Returns the encapsulated signal for this alignment parameter.

        If there is no signal attached then one is created as a reflectometry parameter.

        Returns:
            signal (ReflParameter)
        """

        if not self._movable:
            self._movable = ReflParameter(
                prefix=self._prefix, name=self.name, changing_timeout_s=60
            )

        return self._movable

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
                    (p.get_movable(), self.pre_align_param_positions[p.name])
                    for p in alignment_params
                ]
            )  # type: ignore
        )


def _add_fields(
    fields: list[str],
    dae: SimpleDae,
    periods: bool,
    save_run: bool,
    alignment_param_name: str,
) -> list[str]:
    """If no fields are supplied then use a standard set.

    Args:
        fields (list[str]): The fields to be added to.
        dae (SimpleDae): A readable DAE object.
        periods (bool): Are periods being used.
        save_run (bool): Should runs be saved.
        alignment_param_name (str): The name of the alignment parameter.
            Should be same as the respective relectometry parameter.

    Returns:
        fields (list[str])
    """

    if fields == []:
        fields.extend(
            [
                dae.reducer.intensity.name,  # type: ignore
                dae.reducer.intensity_stddev.name,  # type: ignore
            ]
        )

        if periods:
            fields.append(dae.period_num.name)  # type: ignore

        if save_run:
            fields.append(dae.controller.run_number.name)  # type: ignore

        fields.append(alignment_param_name)

    return fields


def _check_parameter(
    alignment_param_value: float,
    result: ModelResult,
    init_mot_pos: float,
    rel_scan_range: float,
    user_checks: Callable[[ModelResult, float], bool] | None = None,
) -> bool:
    """Check that the optimised value is within scan range and then runs user provided checks.

    Returns True means the found result was not sensible.

    Args:
        fit_param (float): The name of the optimised value.
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


def _get_alignment_param_value(icc: ISISCallbacks, alignment_param: AlignmentParam) -> float:
    return icc.live_fit.result.values[alignment_param.fit_param]


def _inner_loop(
    icc: ISISCallbacks,
    dae: SimpleDae,
    alignment_param: AlignmentParam,
    rel_scan_range: float,
    num_points: int,
    problem_found_plan: Callable[[], Generator[Msg, None, None]],
) -> Generator[Msg, None, bool]:
    """Functionality to perform on a per scan basis.

    Args:
        ISISCallbacks (ISISCallbacks): ISIS Callback Collection object.
        dae (SimpleDae): A readable DAE object.
        alignment_param (AlignmentParam): The alignment parameter to be scanned over and optimised.
        rel_scan_range (float): The current relative scan range.
        num_points (int): The number of points across the scan.
        problem_found_plan (Callable[[], Generator[Msg, None, None]] | Callable[[], None]):
            A callback for what to do if the optimised value is not found to be sensible.

    Returns:
        Whether there was a problem during runtime. Returns True if there was. (bool).
    """

    print(f"Scanning over {alignment_param.name} with a relative scan range of {rel_scan_range}.")

    init_mot_pos: float = yield from bps.rd(alignment_param.get_movable())  #  type: ignore

    @icc
    def _inner() -> Generator[Msg, None, None]:
        yield from bp.rel_scan(
            [dae],
            alignment_param.get_movable(),
            -rel_scan_range / 2,
            rel_scan_range / 2,
            num=num_points,
        )

    yield from _inner()

    print(f"Files written to {FILE_OUTPUT_DIR}\n")
    alignment_param_value = _get_alignment_param_value(icc, alignment_param)

    if _check_parameter(
        alignment_param_value=alignment_param_value,
        result=icc.live_fit.result,
        init_mot_pos=init_mot_pos,
        rel_scan_range=rel_scan_range,
        user_checks=alignment_param.check_func,
    ):
        print(
            f"""This failed one or more of the checks on {alignment_param.name}"""
            f""" with a scan range of {rel_scan_range}."""
        )
        print(f"Value found for {alignment_param.fit_param} was {alignment_param_value}.")

        yield from problem_found_plan()

        def inp() -> str:
            choice = input(
                """Type '1' if you would like to re-scan or type '2' to re-zero"""
                """ at {alignment_param_value} and keep going."""
            )

            if choice not in ["1", "2"]:
                return inp()

            return choice

        if inp() == "1":
            return True

    print(f"Moving {alignment_param.name} to {alignment_param_value} and rezeroing...")
    yield from bps.mv(alignment_param.get_movable(), alignment_param_value)  # type: ignore
    yield from bps.mv(
        alignment_param.get_movable().redefine, 0.0
    )  # Redefine current motor position to be 0

    return False


class OptimiseAxisParams(TypedDict):
    num_points: NotRequired[int]
    fields: NotRequired[list[str]]
    periods: NotRequired[bool]
    save_run: NotRequired[bool]
    files_output_dir: NotRequired[Path]
    problem_found_plan: NotRequired[Callable[[], Generator[Msg, None, None]]]
    pre_align_plan: NotRequired[Callable[[], Generator[Msg, None, None]]]
    post_align_plan: NotRequired[Callable[[], Generator[Msg, None, None]]]
    ax: NotRequired[Axes | None]


def optimise_axis_against_intensity(
    dae: SimpleDae,
    alignment_param: AlignmentParam,
    **kwargs: Unpack[OptimiseAxisParams],
) -> Generator[Msg, None, ISISCallbacks]:
    """Optimise a motor/device to the intensity of the beam.

    Scan between two symmetrical points relative to alignment_param's current motor position,
    to find where the point of hightest beam intensity, move to it, then optionally repeat
    the process for a smaller range and higher granularity.

    Args:
        dae (SimpleDae | BlockR[float]): A readable signal that represents beam intensity.
        alignment_param (AlignmentParam): The alignment parameter to be scanned over and optimised.

    **kwargs:
        num_points (int): The number of points across the scan. Defaults to 10.
        fields (list[str]): Fields to measure and document in outputted files.
        periods (bool): Are periods being used. Defaults to True.
        save_run (bool): Should runs be saved. Defaults to True.
        files_output_dir (Path): Where to save any outputted files. Defaults to
            C:/instrument/var/logs/bluesky/output_files.
        problem_found_plan (Callable[[], Generator[Msg, None, None]] | None):
            Either a plan or standard function, called if optimised value is not found to be
            sensible.
        pre_align_plan (Callable[[], Generator[Msg, None, None]] | None):
            Either a plan or standard function, called before all scans.
        post_align_plan (Callable[[], Generator[Msg, None, None]] | None):
            Either a plan or standard function, called after all scans.
        ax (matplotlib.axes.Axes): The Axes to plot points and fits to.

    Returns:
        an :obj:`ibex_bluesky_core.callbacks.ISISCallbacks` instance.
    """

    num_points = kwargs.get("num_points", 10)
    fields = kwargs.get("fields", [])
    periods = kwargs.get("periods", True)
    save_run = kwargs.get("save_run", True)
    files_output_dir = kwargs.get("files_output_dir", FILE_OUTPUT_DIR)
    problem_found_plan = kwargs.get("problem_found_plan", lambda: bps.null())
    pre_align_plan = kwargs.get("pre_align_plan", lambda: bps.null())
    post_align_plan = kwargs.get("post_align_plan", lambda: bps.null())
    ax = kwargs.get("ax", None)

    fields = _add_fields(
        fields=fields,
        dae=dae,
        periods=periods,
        save_run=save_run,
        alignment_param_name=alignment_param.name,
    )
    postfix = f"{alignment_param.name}_{datetime.now().strftime('%H%M%S')}"
    yerr = dae.reducer.intensity_stddev.name  # type: ignore

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

    yield from pre_align_plan()

    problem_loop = True
    while problem_loop:  # If a problem is found, then start the alignment again
        problem_loop = False

        for rel_scan_range in alignment_param.rel_scan_ranges:
            problem_loop = yield from _inner_loop(
                icc,
                dae,
                alignment_param,
                rel_scan_range,
                num_points,
                problem_found_plan,
            )

    yield from post_align_plan()

    return icc
