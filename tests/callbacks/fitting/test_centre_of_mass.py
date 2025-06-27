# pyright: reportMissingParameterType=false
import pytest

from ibex_bluesky_core.callbacks import CentreOfMass


@pytest.mark.parametrize(
    ("data", "expected_area_under_curve_com"),
    [
        # Simplest possible case:
        # - Flat, non-zero Y data
        # - Perfectly evenly spaced, monotonically increasing X data
        ([(0, 1), (2, 1), (4, 1), (6, 1), (8, 1), (10, 1)], 5.0),
        # Simple triangular peak around x=2 over a base of y=0
        ([(0, 0), (1, 1), (2, 2), (3, 1), (4, 0), (5, 0)], 2.0),
        # Simple triangular peak around x=2 over a base of y=10
        # - area_under_curve_com is explicitly bounded by min(y) at the bottom of the area,
        #   so should be invariant with respect to Y translation.
        ([(0, 10), (1, 11), (2, 12), (3, 11), (4, 10), (5, 10)], 2.0),
        # No data at all
        ([], None),
        # Only one point. CoM should be at that one point's x-value.
        ([(5, 0)], 5.0),
        ([(5, 50)], 5.0),
        # Two points, flat data, com should be in the middle
        ([(0, 1), (10, 1)], 5.0),
        # Flat, logarithmically spaced data:
        # - area_under_curve_com should be in centre of x *range*
        ([(1, 3), (10, 3), (100, 3), (1000, 3), (10000, 3)], 5000.5),
        # Two measurements:
        # - area_under_curve_com should be com of a triangle under those two points
        #   (i.e. 1/3 along from right angle)
        ([(0, 0), (3, 6)], 2.0),
        ([(0, 6), (3, 0)], 1.0),
        # Cases adding extra measurements which don't change the shape of the measured data, and
        # make the first/last points not have equal spacings to each other.
        # - area_under_curve_com: adding extra measurements, which lie along straight lines between
        #   two other existing measurements, should not change the CoM
        ([(0, 1), (4, 1), (5, 0), (6, 1), (10, 1)], 5.0),
        ([(0, 1), (0.1, 1), (4, 1), (5, 0), (6, 1), (10, 1)], 5.0),
        ([(0, 1), (4, 1), (5, 0), (6, 1), (9.9, 1), (10, 1)], 5.0),
        # As above, but adding extra measurements along sloped sections as opposed to flat sections.
        # Triangular peak around x=2 over a background of y=0. All cases below have the same shape.
        ([(0, 0), (2, 2), (4, 0), (5, 0)], 2.0),
        ([(0, 0), (1, 1), (2, 2), (4, 0), (5, 0)], 2.0),
        ([(0, 0), (2, 2), (3, 1), (4, 0), (5, 0)], 2.0),
        # Two symmetrical triangular peaks next to each other, with different point spacings
        # but the same shapes, over a base of zero.
        # - area_under_curve_com: since the peaks are symmetrical,
        # com should lie exactly between them.
        ([(0, 0), (1, 1), (2, 2), (3, 1), (4, 0), (6, 2), (8, 0), (10, 0)], 4.0),
        ([(0, 0), (2, 2), (4, 0), (5, 1), (6, 2), (7, 1), (8, 0), (10, 0)], 4.0),
        # As above, but over a base of y=10.
        ([(0, 10), (1, 11), (2, 12), (3, 11), (4, 10), (6, 12), (8, 10), (10, 10)], 4.0),
        ([(0, 10), (2, 12), (4, 10), (5, 11), (6, 12), (7, 11), (8, 10), (10, 10)], 4.0),
        # "Narrow" peak at x=5.0, over a base of y=0
        ([(0, 0), (4.999, 0), (5.0, 10), (5.001, 0)], 5.0),
        # "Narrow" peak as above, at x=5.0, over a base of y=10
        ([(0, 10), (4.999, 10), (5.0, 20), (5.001, 10)], 5.0),
        # Non-monotonically increasing x data (e.g. from adaptive scan).
        # Simple triangular peak shape centred at x=2.
        ([(0, 0), (2, 2), (1, 1), (3, 1), (4, 0)], 2.0),
        # Overscanned data - all measurements duplicated - e.g. there-and-back scan
        ([(0, 0), (1, 1), (2, 0), (2, 0), (1, 1), (0, 0)], 1.0),
        # Mixed positive/negative Y data.
        # - area_under_curve_com is explicitly calculating area *under* the curve
        ([(0, -1), (1, 0), (2, -1), (3, -1)], 1.0),
        # Y data with a positive peak at x=1 over a base of y=-1
        ([(0, -1), (1, 3), (2, -1), (3, -1)], 1.0),
        # Y data happens to sum to *nearly* zero rather than exactly zero
        ([(0, -1), (1, 3.000001), (2, -1), (3, -1)], 1.0),
        ([(0, -1), (1, 2.999999), (2, -1), (3, -1)], 1.0),
    ],
)
def test_compute_com(data: list[tuple[float, float]], expected_area_under_curve_com: float):
    com = CentreOfMass("x", "y")
    com.start({})  # type: ignore

    for x, y in data:
        com.event({"data": {"x": x, "y": y}})  # type: ignore

    com.stop({})  # type: ignore

    assert com.result == pytest.approx(expected_area_under_curve_com)


def test_error_thrown_if_no_x_data_in_event():
    com = CentreOfMass(x="motor", y="invariant")
    com.event(
        {
            "data": {  # type: ignore
                "invariant": 2,
            }
        }
    )

    with pytest.raises(OSError, match=r"motor is not in event document."):
        com.compute()


def test_error_thrown_if_no_y_data_in_event():
    com = CentreOfMass(x="motor", y="invariant")
    com.event(
        {
            "data": {  # type: ignore
                "motor": 2,
            }
        }
    )

    with pytest.raises(OSError, match=r"invariant is not in event document."):
        com.compute()
