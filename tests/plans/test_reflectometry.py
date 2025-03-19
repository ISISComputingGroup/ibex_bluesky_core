# pyright: reportMissingParameterType=false

from collections.abc import Generator
from unittest.mock import MagicMock, call, patch

import bluesky.plan_stubs as bps
import pytest
from bluesky.utils import Msg
from lmfit.model import ModelResult

from ibex_bluesky_core.callbacks import ISISCallbacks
from ibex_bluesky_core.callbacks.fitting import LiveFit
from ibex_bluesky_core.callbacks.fitting.fitting_utils import Gaussian, SlitScan
from ibex_bluesky_core.devices.reflectometry import ReflParameter
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.plans.reflectometry import refl_adaptive_scan, refl_scan
from ibex_bluesky_core.plans.reflectometry.autoalign_utils import (
    _check_parameter,
    _get_alignment_param_value,
    optimise_axis_against_intensity,
)


@pytest.fixture
def prefix():
    return "UNITTEST:"


def _plan_return_0() -> Generator[Msg, None, float]:
    yield from bps.null()
    return 0.0


def _fake_scan() -> Generator[Msg, None, ISISCallbacks]:
    yield from bps.null()
    icc = MagicMock()
    icc.live_fit.result = "foo"
    return icc


def test_refl_scan_creates_refl_param_device_and_simpledae(RE, prefix):
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


def test_refl_adaptive_scan_creates_refl_param_device_and_simpledae(RE, prefix):
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

def test_found_problem_callback_is_called_if_problem(RE, simpledae, prefix, monkeypatch):
    """Test that if a problem is found then the problem callback plan is run"""

    def plan(mock) -> Generator[Msg, None, None]:
        mock()
        yield from bps.null()

    mock = MagicMock()

    with (
        patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.plans.reflectometry.autoalign_utils.scan", return_value=_fake_scan()),
        patch("ibex_bluesky_core.plans.reflectometry.autoalign_utils.bps.mv", return_value=bps.null()),
        patch("ibex_bluesky_core.plans.reflectometry.autoalign_utils.bps.rd", return_value=_plan_return_0()),
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils._check_parameter",
            return_value=False,
        ),
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils._get_alignment_param_value",
            return_value=0.0,
        ),
    ):
        param = ReflParameter(
            prefix=prefix, name="S1VG", changing_timeout_s=60
        )

        monkeypatch.setattr("builtins.input", lambda _: "2")
        RE(
            optimise_axis_against_intensity(
                dae=simpledae,
                alignment_param=param,
                problem_found_plan=lambda: plan(mock),
                rel_scan_ranges=[0.0],
                fit_method=SlitScan().fit(),
                fit_param=""
            )
        )

        mock.assert_called_once()


@pytest.mark.parametrize(("param_value", "problem"), [(-5, False), (5, False), (0.0, True)])
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


@pytest.mark.parametrize("problem", [False, True])
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
                is_good_fit=my_check,
            )
            == problem
        )


def test_that_if_no_problem_found_then_motor_is_moved_and_rezeroed(RE, prefix, simpledae):
    """Test that if no problems are found with the optimised
    value then move the motor to it and redefine this as 0"""

    sp = 5.0

    with (
        patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix),
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils._check_parameter",
            return_value=True,
        ) as check,
        patch("ibex_bluesky_core.plans.reflectometry.autoalign_utils.scan", return_value=_fake_scan()),
        patch("ibex_bluesky_core.plans.reflectometry.autoalign_utils.bps.mv", return_value=bps.null()) as mv,
        patch("ibex_bluesky_core.plans.reflectometry.autoalign_utils.bps.rd", return_value=_plan_return_0()),
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils._get_alignment_param_value",
            return_value=sp,
        ),
    ):
        param = ReflParameter(
            prefix=prefix,
            name="S1VG",
            changing_timeout_s=60
        )

        RE(optimise_axis_against_intensity(simpledae, alignment_param=param, rel_scan_ranges=[0.0], fit_method=SlitScan().fit(), fit_param=""))

        check.assert_called_once()
        mv.assert_called_once()


def test_that_if_problem_found_and_type_1_then_re_scan(RE, prefix, simpledae, monkeypatch):
    """Test that if a problem is found, and the user types 1, then rescan.
    Then if they type 2, moves to value."""

    def counter(str: str):
        counter.call_count += 1  # type: ignore

        if counter.call_count == 1:  # type: ignore
            return "1"
        else:
            return "2"

    with (
        patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix),
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils._check_parameter",
            return_value=False,
        ),
        patch("ibex_bluesky_core.plans.reflectometry.autoalign_utils.scan", side_effect=[_fake_scan(), _fake_scan()]) as scan,
        patch("ibex_bluesky_core.plans.reflectometry.autoalign_utils.bps.mv", return_value=bps.null()),
        patch("ibex_bluesky_core.plans.reflectometry.autoalign_utils.bps.rd", return_value=_plan_return_0()),
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils._get_alignment_param_value",
            return_value=0,
        ),
    ):
        param = ReflParameter(
            prefix=prefix,
            name="S1VG",
            changing_timeout_s=60
        )
        counter.call_count = 0  # type: ignore

        monkeypatch.setattr("builtins.input", counter)
        RE(optimise_axis_against_intensity(simpledae, alignment_param=param, rel_scan_ranges=[0.0], fit_method=SlitScan().fit(), fit_param=""))

        assert scan.call_count == 2


def test_that_if_problem_found_and_type_random_then_re_ask(RE, prefix, simpledae, monkeypatch):
    """Test that if a problem is found, and the user types gibberish, then ask again.
    Then if they type 1, it rescans. If they type 2, it moves to value."""

    def counter(str: str):
        counter.call_count += 1  # type: ignore

        if counter.call_count == 1:  # type: ignore
            return "platypus"
        elif counter.call_count == 2:  # type: ignore
            return "1"
        else:
            return "2"

    with (
        patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix),
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils._check_parameter",
            return_value=False,
        ),
        patch("ibex_bluesky_core.plans.reflectometry.autoalign_utils.scan", side_effect=[_fake_scan(), _fake_scan()]) as scan,
        patch("ibex_bluesky_core.plans.reflectometry.autoalign_utils.bps.mv", return_value=bps.null()),
        patch("ibex_bluesky_core.plans.reflectometry.autoalign_utils.bps.rd", return_value=_plan_return_0()),
        patch(
            "ibex_bluesky_core.plans.reflectometry.autoalign_utils._get_alignment_param_value",
            return_value=0,
        ),
    ):
      
        param = ReflParameter(
            prefix=prefix,
            name="S1VG",
            changing_timeout_s=60
        )
        counter.call_count = 0  # type: ignore

        monkeypatch.setattr("builtins.input", counter)
        RE(optimise_axis_against_intensity(simpledae, alignment_param=param, rel_scan_ranges=[0.0], fit_method=SlitScan().fit(), fit_param=""))

        assert scan.call_count == 2


def test_get_alignment_param_value(prefix):
    """Test that the _get_alignment_param_value is able to retrieve
    alignment_param_value from the icc"""

    param_value = 0.0
    fit_param = "x0"

    with (
        patch("ibex_bluesky_core.devices.reflectometry.get_pv_prefix", return_value=prefix),
        patch("ibex_bluesky_core.plans.ISISCallbacks") as icc,
    ):

        icc.live_fit.result.values = {fit_param: param_value}
        assert _get_alignment_param_value(icc, fit_param) == param_value
