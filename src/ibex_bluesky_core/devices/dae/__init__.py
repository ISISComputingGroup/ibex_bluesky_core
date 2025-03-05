"""Utilities for the DAE device - mostly XML helpers."""

from enum import Enum
from typing import Any
from xml.etree.ElementTree import Element

from ibex_bluesky_core.devices import get_pv_prefix
from ibex_bluesky_core.devices.simpledae import SimpleDae
from ibex_bluesky_core.devices.simpledae.controllers import (
    PeriodPerPointController,
    RunPerPointController,
)
from ibex_bluesky_core.devices.simpledae.reducers import MonitorNormalizer
from ibex_bluesky_core.devices.simpledae.waiters import GoodFramesWaiter, PeriodGoodFramesWaiter


def convert_xml_to_names_and_values(xml: Element) -> dict[str, str]:
    """Convert an XML element's children to a dict containing <Name>.text:<Val>.text."""
    names_and_values = dict()
    elements = get_all_elements_in_xml_with_child_called_name(xml)
    for element in elements:
        name, value = _get_names_and_values(element)
        if name is not None:
            names_and_values[name] = value
    return names_and_values


def get_all_elements_in_xml_with_child_called_name(xml: Element) -> list[Element]:
    """Find all elements with a "name" element, but ignore the first one as it's the root."""
    elements = xml.findall("*/Name/..")
    return elements


def _get_names_and_values(element: Element) -> tuple[Any, Any] | tuple[None, None]:
    name = element.find("Name")
    if name is not None and name.text is not None:
        name = name.text
        value = element.find("Val")
        return name, value.text if value is not None else None
    return None, None


def set_value_in_dae_xml(
    elements: list[Element], name: str, value: str | Enum | int | float | None
) -> None:
    """Find and set a value in the DAE XML, given a name and value.

    Do nothing (by design) if value is None to leave value unchanged.
    """
    if value is not None:
        if isinstance(value, Enum):
            value = value.value
        for i in elements:
            name_element = i.find("Name")
            value_element = i.find("Val")
            if name_element is not None and value_element is not None and name_element.text == name:
                value_element.text = str(value)
                return


def monitor_normalising_dae(
    *,
    det_pixels: list[int],
    frames: int,
    periods: bool = True,
    monitor: int = 1,
    save_run: bool = False,
) -> SimpleDae:
    """Create a simple DAE which normalises using a monitor and waits for frames.

    This is really a shortcut to reduce code in plans used on the majority of instruments that
       normalise using a monitor, wait for a number of frames and optionally use hardware periods.

    Args:
        det_pixels: list of detector pixel to use for scanning.
        frames: number of frames to wait for.
        periods: whether or not to use hardware periods.
        monitor: the monitor spectra number.
        save_run: whether or not to save the run of the DAE.

    """
    prefix = get_pv_prefix()

    if periods:
        controller = PeriodPerPointController(save_run=save_run)
        waiter = PeriodGoodFramesWaiter(frames)
    else:
        controller = RunPerPointController(save_run=save_run)
        waiter = GoodFramesWaiter(frames)

    reducer = MonitorNormalizer(
        prefix=prefix,
        detector_spectra=det_pixels,
        monitor_spectra=[monitor],
    )

    dae = SimpleDae(
        prefix=prefix,
        controller=controller,
        waiter=waiter,
        reducer=reducer,
    )

    dae.reducer.intensity.set_name("intensity")  # type: ignore
    dae.reducer.intensity_stddev.set_name("intensity_stddev")  # type: ignore
    return dae
