import numpy as np
import pytest

from ibex_bluesky_core.callbacks.fitting import PeakStats

# Tests:
# Test with normal scan with gaussian data
# Check that asymmetrical data does not skew CoM
# Check that having a background on data does not skew CoM
# Check that order of documents does not skew CoM
# Check that point spacing does not skew CoM

def gaussian(x, amp, sigma, x0, bg):
    return (x, amp * np.exp(-((x - x0) ** 2) / (2 * sigma**2)) + bg)


def simulate_run_and_return_com(xy):

    ps = PeakStats("x", "y")

    ps.start({})

    for x, y in np.vstack(xy).T:
        ps.event({"data": {"x": x, "y": y}})

    ps.stop({})

    return ps["com"]


@pytest.mark.parametrize("x, amp, sigma, x0, bg", [

    (np.arange(-2, 3), 1, 1, 0, 0),
    (np.arange(-4, 1), 1, 1, -2, 0),

])
def test_normal_scan(x, amp, sigma, x0, bg):

    xy = gaussian(x, amp, sigma, x0, bg)
    com = simulate_run_and_return_com(xy)
    assert com == pytest.approx(x0, abs=1e-4)


@pytest.mark.parametrize("x, amp, sigma, x0, bg", [

    (np.arange(-4, 10), 1, 1, 0, 0),
    (np.arange(-6, 20), 1, 1, -2, 0),

])
def test_asymmetrical_scan(x, amp, sigma, x0, bg):

    xy = gaussian(x, amp, sigma, x0, bg)
    com = simulate_run_and_return_com(xy)
    assert com == pytest.approx(x0, abs=1e-4)


@pytest.mark.parametrize("x, amp, sigma, x0, bg", [

    (np.arange(-2, 3), 1, 1, 0, 3),
    (np.arange(-4, 1), 1, 1, -2, -0.5),
    (np.arange(-4, 1), 1, 1, -2, -3),

])
def test_background_gaussian_scan(x, amp, sigma, x0, bg):

    xy = gaussian(x, amp, sigma, x0, bg)
    com = simulate_run_and_return_com(xy)
    assert com == pytest.approx(x0, abs=1e-4)


@pytest.mark.parametrize("x, amp, sigma, x0, bg", [

    (np.array([0, -2, 2, -1, 1]), 1, 1, 0, 0),
    (np.array([-4, 0, -2, -3, -1]), 1, 1, -2, 0),

])
def test_non_continuous_scan(x, amp, sigma, x0, bg):

    xy = gaussian(x, amp, sigma, x0, bg)
    com = simulate_run_and_return_com(xy)
    assert com == pytest.approx(x0, abs=1e-4)


@pytest.mark.parametrize("x, amp, sigma, x0, bg", [

    (np.append(np.arange(-10, -2, 0.05), np.arange(-2, 4, 0.5)), 1, 0.5, 0, 0),
    (np.concatenate((np.arange(-5, -2.0, 0.5), np.arange(-2.5, -1.45, 0.05), np.arange(-1.5, 1, 0.5)), axis=0), 1, 0.25, 0, 0)
])
def test_non_constant_point_spacing_scan(x, amp, sigma, x0, bg):

    xy = gaussian(x, amp, sigma, x0, bg)
    com = simulate_run_and_return_com(xy)
    assert com == pytest.approx(x0, abs=1e-3)
