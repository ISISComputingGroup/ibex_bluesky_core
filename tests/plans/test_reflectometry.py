# pyright: reportMissingParameterType=false

from collections.abc import Generator
from unittest.mock import MagicMock, call, patch

import bluesky.plan_stubs as bps
import pytest
from bluesky.utils import Msg
from lmfit.model import ModelResult

from ibex_bluesky_core.callbacks.fitting import LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Gaussian, SlitScan
from ibex_bluesky_core.devices.reflectometry import ReflParameter
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import RunPerPointController
from ibex_bluesky_core.devices.simpledae.reducers import MonitorNormalizer
from ibex_bluesky_core.devices.simpledae.strategies import Waiter
from ibex_bluesky_core.plans.reflectometry import refl_adaptive_scan, refl_scan
from ibex_bluesky_core.plans.reflectometry.autoalign_utils import (
    AlignmentParam,
    _check_parameter,
    _get_alignment_param_value,
    optimise_axis_against_intensity,
)


@pytest.fixture
def prefix():
    return "UNITTEST:"


def test_refl_scan_creates_refl_param_device_and_dae(RE, prefix):
    param_name = "theta"
    with (
        patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.devices.simpledae.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.plans.reflectometry.scan") as scan,
    ):
        RE(
            refl_scan(
                param=param_name,
                start=0,
                stop=2,
                num=3,
                frames=200,
                det=1,
                mon=3,
                model=Gaussian().fit(),
            )
        )
        scan.assert_called_once()
        assert isinstance(scan.call_args[1]["dae"], SimpleDae)
        assert isinstance(scan.call_args[1]["block"], ReflParameter)
        assert scan.call_args[1]["block"].name == param_name


def test_refl_adaptive_scan_creates_refl_param_device_and_dae(RE, prefix):
    param_name = "S1VG"
    with (
        patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.devices.simpledae.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.plans.reflectometry.adaptive_scan") as scan,
    ):
        RE(
            refl_adaptive_scan(
                param=param_name,
                start=0,
                stop=2,
                min_step=0.01,
                max_step=0.1,
                target_delta=0.5,
                frames=200,
                det=1,
                mon=3,
                model=Gaussian().fit(),
            )
        )
        scan.assert_called_once()
        assert isinstance(scan.call_args[1]["dae"], SimpleDae)
        assert isinstance(scan.call_args[1]["block"], ReflParameter)
        assert scan.call_args[1]["block"].name == param_name


# Auto-Alignment Utils


@pytest.fixture
async def dae():
    controller = RunPerPointController(save_run=True)
    noop_waiter = Waiter()
    reducer = MonitorNormalizer(prefix="UNITTEST:", detector_spectra=[1, 2, 3], monitor_spectra=[4])

    dae = SimpleDae(
        prefix="UNITTEST:",
        name="dae",
        controller=controller,
        waiter=noop_waiter,
        reducer=reducer,
    )
    await dae.connect(mock=True)
    return dae


def test_get_movable_on_alignment_param_returns_reflparam(prefix):
    """Test that calling get_movable on an AlignmentParam returns a ReflParameter object."""

    param_name = "S1VG"

    with patch(
        "ibex_bluesky_core.plans.reflectometry.autoalign_utils.get_pv_prefix", return_value=prefix
    ):
        param = AlignmentParam(
            name=param_name, rel_scan_ranges=[0.0], fit_method=SlitScan().fit(), fit_param=""
        )

        assert type(param.get_movable()) is ReflParameter
        assert param.get_movable().name == param_name


def test_alignment_param_pre_alignment_plan(RE, prefix):
    """Test that given a set of motor positions, calling pre_align_params
    will move the specified ReflParameters to respective positions."""

    with (
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils.get_pv_prefix",
            return_value=prefix,
        ),
        patch("bluesky.plan_stubs.mv") as mv,
    ):
        params = [
            AlignmentParam(
                name="S1VG",
                rel_scan_ranges=[0.0],
                fit_method=SlitScan().fit(),
                fit_param="",
                pre_align_param_positions={"S1VG": 1.0, "S2VG": 2.0, "S3VG": 3.0},
            ),
            AlignmentParam(
                name="S2VG", rel_scan_ranges=[0.0], fit_method=SlitScan().fit(), fit_param=""
            ),
            AlignmentParam(
                name="S3VG",
                rel_scan_ranges=[5.0, 1.0, 0.1],
                fit_method=SlitScan().fit(),
                fit_param="",
            ),
        ]

        RE(params[0].pre_align_params(params))

        mv.assert_called_once()
        assert mv.call_args[0] == (
            params[0].get_movable(),
            1.0,
            params[1].get_movable(),
            2.0,
            params[2].get_movable(),
            3.0,
        )


def test_that_if_fields_supplied_they_are_unchanged(RE, prefix, dae):
    """Test that if you pass some fields, then they are
    left unchanged as they are passed to the ICC"""

    param_name = "S1VG"
    fit_method = SlitScan().fit()

    def gen() -> Generator[Msg, None, float]:
        yield from bps.null()
        return 0.0

    with (
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils.get_pv_prefix",
            return_value=prefix,
        ),
        patch("ibex_bluesky_core.plans.ISISCallbacks.__init__", return_value=None) as icc,
        patch(
            "ibex_bluesky_core.plans.ISISCallbacks.live_fit",
            return_value=LiveFit(fit_method, dae.name, param_name),
        ),
        patch("bluesky.plan_stubs.rd", return_value=gen()),
    ):
        param = AlignmentParam(
            name=param_name, rel_scan_ranges=[], fit_method=fit_method, fit_param=""
        )
        RE(optimise_axis_against_intensity(dae, alignment_param=param, fields=["octopus"]))

        icc.assert_called_once()
        assert ["octopus"] == icc.call_args[1]["measured_fields"]  # type: ignore


def test_when_no_fields_provided_then_fields_added(RE, prefix, dae):
    """Test that if you do not pass any fields then some
    essential ones are added before passing off to the ICC"""

    param_name = "S1VG"
    fit_method = SlitScan().fit()

    def gen() -> Generator[Msg, None, float]:
        yield from bps.null()
        return 0.0

    with (
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils.get_pv_prefix",
            return_value=prefix,
        ),
        patch("ibex_bluesky_core.plans.ISISCallbacks.__init__", return_value=None) as icc,
        patch(
            "ibex_bluesky_core.plans.ISISCallbacks.live_fit",
            return_value=LiveFit(fit_method, dae.name, param_name),
        ),
        patch("bluesky.plan_stubs.rd", return_value=gen()),
    ):
        param = AlignmentParam(name="S1VG", rel_scan_ranges=[], fit_method=fit_method, fit_param="")
        RE(optimise_axis_against_intensity(dae, alignment_param=param))

        icc.assert_called_once()
        assert [
            dae.reducer.intensity.name,
            dae.reducer.intensity_stddev.name,
            dae.period_num.name,
            dae.controller.run_number.name,
            param_name,
        ] == icc.call_args[1]["measured_fields"]  # type: ignore


def test_when_no_periods_no_save_run_then_not_added_to_fields(RE, prefix, dae):
    """Test that if save_run and periods are set
    to False then they are not included in the fields"""

    param_name = "S1VG"
    fit_method = SlitScan().fit()

    def gen() -> Generator[Msg, None, float]:
        yield from bps.null()
        return 0.0

    with (
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils.get_pv_prefix",
            return_value=prefix,
        ),
        patch("ibex_bluesky_core.plans.ISISCallbacks.__init__", return_value=None) as icc,
        patch(
            "ibex_bluesky_core.plans.ISISCallbacks.live_fit",
            return_value=LiveFit(fit_method, dae.name, param_name),
        ),
        patch("bluesky.plan_stubs.rd", return_value=gen()),
    ):
        param = AlignmentParam(
            name="S1VG", rel_scan_ranges=[], fit_method=SlitScan().fit(), fit_param=""
        )
        RE(
            optimise_axis_against_intensity(
                dae, alignment_param=param, periods=False, save_run=False
            )
        )

        icc.assert_called_once()
        assert [
            dae.reducer.intensity.name,
            dae.reducer.intensity_stddev.name,
            param_name,
        ] == icc.call_args[1]["measured_fields"]  # type: ignore


def test_pre_post_align_callbacks_are_called(RE, prefix, dae):
    """Test that pre/post alignment callback plans are ran at the appropriate time"""

    def plan(mock) -> Generator[Msg, None, None]:
        mock()
        yield from bps.null()

    def gen() -> Generator[Msg, None, bool]:
        yield from bps.null()
        return True

    mock_a = MagicMock()
    mock_b = MagicMock()

    with (
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils.get_pv_prefix",
            return_value=prefix,
        ),
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils._inner_loop", return_value=gen()
        ),
    ):
        param = AlignmentParam(
            name="S1VG", rel_scan_ranges=[], fit_method=SlitScan().fit(), fit_param=""
        )
        RE(
            optimise_axis_against_intensity(
                dae,
                alignment_param=param,
                pre_align_plan=lambda: plan(mock_a),
                post_align_plan=lambda: plan(mock_b),
            )
        )

        mock_a.assert_called_once()
        mock_b.assert_called_once()


def test_found_problem_callback_is_called_if_problem(RE, prefix, dae, monkeypatch):
    """Test that if a problem is found then the problem callback plan is run"""

    def plan(mock) -> Generator[Msg, None, None]:
        mock()
        yield from bps.null()

    def gen() -> Generator[Msg, None, float]:
        yield from bps.null()
        return 0.0

    mock = MagicMock()

    with (
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils.get_pv_prefix",
            return_value=prefix,
        ),
        patch("bluesky.plans.rel_scan", return_value=bps.null()),
        patch("bluesky.plan_stubs.mv", return_value=bps.null()),
        patch("bluesky.plan_stubs.rd", return_value=gen()),
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils._check_parameter",
            return_value=True,
        ),
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils._get_alignment_param_value",
            return_value=0.0,
        ),
    ):
        param = AlignmentParam(
            name="S1VG", rel_scan_ranges=[0.0], fit_method=SlitScan().fit(), fit_param=""
        )

        monkeypatch.setattr("builtins.input", lambda _: "2")
        RE(
            optimise_axis_against_intensity(
                dae, alignment_param=param, problem_found_plan=lambda: plan(mock)
            )
        )

        mock.assert_called_once()


@pytest.mark.parametrize(("param_value", "problem"), [(-5, True), (5, True), (0.0, False)])
def test_alignment_param_value_outside_of_scan_range_returns_problem(param_value, problem):
    """Test that if the optimised value is outside of the scan range then it is reported"""

    with (
        patch("lmfit.model.ModelResult") as mr,
    ):
        mr.values = {"x0": param_value}
        assert (
            _check_parameter(
                alignment_param_value=param_value, result=mr, init_mot_pos=0.0, rel_scan_range=1.0
            )
            == problem
        )


@pytest.mark.parametrize("problem", [True, False])
def test_that_user_checks_are_called_when_provided(problem):
    """Test that a user provided check function on the optimised value is always ran"""

    mock = MagicMock()

    def my_check(model: ModelResult, param_val: float):
        mock()
        return problem

    with patch("lmfit.model.ModelResult") as mr:
        mr.values = {"x0": 0.0}
        assert (
            _check_parameter(
                alignment_param_value=0.0,
                result=mr,
                init_mot_pos=0.0,
                rel_scan_range=1.0,
                user_checks=my_check,
            )
            == problem
        )


def test_that_if_no_problem_found_then_motor_is_moved_and_rezeroed(RE, prefix, dae):
    """Test that if no problems are found with the optimised
    value then move the motor to it and redefine this as 0"""

    sp = 5.0

    def gen() -> Generator[Msg, None, float]:
        yield from bps.null()
        return 0.0

    with (
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils.get_pv_prefix",
            return_value=prefix,
        ),
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils._check_parameter",
            return_value=False,
        ) as check,
        patch("bluesky.plans.rel_scan", return_value=bps.null()),
        patch("bluesky.plan_stubs.mv", return_value=bps.null()) as mv,
        patch("bluesky.plan_stubs.rd", return_value=gen()),
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils._get_alignment_param_value",
            return_value=sp,
        ),
    ):
        param = AlignmentParam(
            name="S1VG", rel_scan_ranges=[0.0], fit_method=SlitScan().fit(), fit_param=""
        )

        RE(optimise_axis_against_intensity(dae, alignment_param=param))

        check.assert_called_once()
        mv.assert_has_calls(
            [call(param.get_movable(), sp), call(param.get_movable().redefine, 0.0)]
        )


def test_that_if_problem_found_and_type_1_then_re_scan(RE, prefix, dae, monkeypatch):
    """Test that if a problem is found, and the user types 1, then rescan.
    Then if they type 2, moves to value and redefines as 0."""

    def counter(str: str):
        counter.call_count += 1  # type: ignore

        if counter.call_count == 1:  # type: ignore
            return "1"
        else:
            return "2"

    def gen() -> Generator[Msg, None, float]:
        yield from bps.null()
        return 0.0

    with (
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils.get_pv_prefix",
            return_value=prefix,
        ),
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils._check_parameter",
            return_value=True,
        ),
        patch("bluesky.plans.rel_scan", return_value=bps.null()) as scan,
        patch("bluesky.plan_stubs.mv", return_value=bps.null()),
        patch("bluesky.plan_stubs.rd", return_value=gen()),
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils._get_alignment_param_value",
            return_value=0.0,
        ),
    ):
        param = AlignmentParam(
            name="S1VG", rel_scan_ranges=[0.0], fit_method=SlitScan().fit(), fit_param=""
        )
        counter.call_count = 0  # type: ignore

        monkeypatch.setattr("builtins.input", counter)
        RE(optimise_axis_against_intensity(dae, alignment_param=param))

        assert scan.call_count == 2


def test_that_if_problem_found_and_type_random_then_re_ask(RE, prefix, dae, monkeypatch):
    """Test that if a problem is found, and the user types gibberish, then ask again.
    Then if they type 1, it rescans. If they type 2, it moves to value and redefines as 0."""

    def counter(str: str):
        counter.call_count += 1  # type: ignore

        if counter.call_count == 1:  # type: ignore
            return "platypus"
        elif counter.call_count == 2:  # type: ignore
            return "1"
        else:
            return "2"

    def gen() -> Generator[Msg, None, float]:
        yield from bps.null()
        return 0.0

    with (
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils.get_pv_prefix",
            return_value=prefix,
        ),
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils._check_parameter",
            return_value=True,
        ),
        patch("bluesky.plans.rel_scan", return_value=bps.null()) as scan,
        patch("bluesky.plan_stubs.mv", return_value=bps.null()),
        patch("bluesky.plan_stubs.rd", return_value=gen()),
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils._get_alignment_param_value",
            return_value=0.0,
        ),
    ):
        param = AlignmentParam(
            name="S1VG", rel_scan_ranges=[0.0], fit_method=SlitScan().fit(), fit_param=""
        )
        counter.call_count = 0  # type: ignore

        monkeypatch.setattr("builtins.input", counter)
        RE(optimise_axis_against_intensity(dae, alignment_param=param))

        assert scan.call_count == 2


def test_get_alignment_param_value(prefix):
    """Test that the _get_alignment_param_value is able to retrieve
    alignment_param_value from the icc"""

    param_value = 0.0

    with (
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils.get_pv_prefix",
            return_value=prefix,
        ),
        patch("ibex_bluesky_core.plans.ISISCallbacks") as icc,
        patch("ibex_bluesky_core.callbacks.fitting.LiveFit") as lf,
        patch("lmfit.model.ModelResult") as mr,
    ):
        param = AlignmentParam(
            name="S1VG", rel_scan_ranges=[], fit_method=SlitScan().fit(), fit_param="x0"
        )
        mr.values = {"x0": param_value}
        lf.result = mr
        icc.live_fit = lf

        assert _get_alignment_param_value(icc, param) == param_value
