from typing import Dict, Tuple


def convert_xml_to_names_and_values(xml) -> Dict[str, str]:
    names_and_values = dict()
    # This finds all elements with a "name" element, but ignores the first one as it's the root
    elements = xml.findall(".//Name/..")[1:]
    for element in elements:
        name, value = _get_names_and_values(element)
        names_and_values[name] = value
    return names_and_values


def _get_names_and_values(element) -> Tuple[str, str]:
    name = element.find("Name")
    if name is not None and hasattr(name, "text"):
        name = name.text
    value = element.find("Val")
    if value is not None and hasattr(value, "text"):
        value = value.text
    # TODO hmmmm, should we get choices here and store them somewhere? not sure.
    return name, value
