"""Common utilities for use across devices."""

from __future__ import annotations

import binascii
import os
import zlib
from enum import Enum
from typing import Dict, Tuple, Type, List, Any
from xml.etree import ElementTree as ET

from ophyd_async.core import T, SignalRW
from ophyd_async.epics.signal import epics_signal_rw


def get_pv_prefix() -> str:
    """Return the PV prefix for the current instrument."""
    prefix = os.getenv("MYPVPREFIX")

    if prefix is None:
        raise EnvironmentError("MYPVPREFIX environment variable not available - please define")

    return prefix


def dehex_and_decompress(value: bytes) -> bytes:
    """Decompresses the inputted string, assuming it is in hex encoding.

    Args:
        value: The string to be decompressed, encoded in hex

    Returns A decompressed version of the inputted string
    """
    return zlib.decompress(binascii.unhexlify(value))


def convert_xml_to_names_and_values(xml) -> Dict[str, str]:
    names_and_values = dict()
    elements = get_all_elements_in_xml_with_child_called_name(xml)
    for element in elements:
        name, value = _get_names_and_values(element)
        names_and_values[name] = value
    return names_and_values


def get_all_elements_in_xml_with_child_called_name(xml):
    # This finds all elements with a "name" element, but ignores the first one as it's the root
    elements = xml.findall(".//Name/..")[1:]
    return elements


def _get_names_and_values(element) -> Tuple[str, str]:
    name = element.find("Name")
    if name is not None and hasattr(name, "text"):
        name = name.text
    value = element.find("Val")
    if value is not None and hasattr(value, "text"):
        value = value.text
    # TODO hmmmm, should we get choices here and store them somewhere? not sure.
    return name, value


def isis_epics_signal_rw(datatype: Type[T], read_pv: str, name: str = "") -> SignalRW[T]:
    """Utility function for making a RW signal using the ISIS PV naming standard ie. read_pv being TITLE,
    write_pv being TITLE:SP
    """
    write_pv = f"{read_pv}:SP"
    return epics_signal_rw(datatype, read_pv, write_pv, name)


def set_value_in_dae_xml(elements:List[ET.ElementTree], name:str, value:Any):
    """
    TODO add some docs here pls
    """
    if value is not None and (isinstance(value, list) and value):
        if isinstance(value, Enum):
            value = value.value
        for i in elements:
            if i.find("Name").text == name:
                i.find("Val").text = value
