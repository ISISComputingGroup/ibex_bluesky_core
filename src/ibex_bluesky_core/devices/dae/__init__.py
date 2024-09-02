from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Tuple
from xml.etree import ElementTree as ET


def convert_xml_to_names_and_values(xml) -> Dict[str, str]:
    names_and_values = dict()
    elements = get_all_elements_in_xml_with_child_called_name(xml)
    for element in elements:
        name, value = _get_names_and_values(element)
        if name is not None:
            names_and_values[name] = value
    return names_and_values


def get_all_elements_in_xml_with_child_called_name(xml):
    # This finds all elements with a "name" element, but ignores the first one as it's the root
    elements = xml.findall(".//Name/..")[1:]
    return elements


def _get_names_and_values(element) -> tuple[Any, Any] | tuple[None, None]:
    name = element.find("Name")
    if name is not None and name.text is not None:
        name = name.text
        value = element.find("Val")
        return name, value.text
    return None, None


def set_value_in_dae_xml(elements: List[ET.ElementTree], name: str, value: Any):
    """TODO add some docs here pls"""
    if value is not None:
        if isinstance(value, Enum):
            value = value.value
        for i in elements:
            if i.find("Name").text == name:
                i.find("Val").text = str(value)
                return
