from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any

from ophyd_async.core import SignalRW, StandardReadable, AsyncStatus


import xml.etree.ElementTree as ET

from ibex_bluesky_core.devices import convert_xml_to_names_and_values, isis_epics_signal_rw, dehex_and_decompress

class TimeUnit(Enum):
    MICROSECONDS = 0
    NANOSECONDS = 1

class CalculationMethod(Enum):
    SPECIFY_PARAMETERS = 0
    USE_TCB_FILE = 1

class TimeRegimeMode(Enum):
    BLANK = 0
    DT = 1
    DTDIVT = 2
    DTDIVT2 = 3
    SHIFTED = 4


@dataclass
class TimeRegime:
    pass

class TimeRegimeRow:
    pass

@dataclass
class DaeTCBSettingsData:
    tcb_file: str|None = None
    tcb_tables = []
    tcb_calculation_method: CalculationMethod|None = None


def convert_xml_to_tcb_settings(value: str) -> DaeTCBSettingsData:
    root = ET.fromstring(value)
    settings_from_xml = convert_xml_to_names_and_values(root)
    print(settings_from_xml)
    settings = DaeTCBSettingsData()
    # TODO parse
    return settings


def convert_tcb_settings_to_xml(value: DaeTCBSettingsData):
    return ET.fromstring("")


class DaeTCBSettings(StandardReadable):
    def __init__(self, dae_prefix, name=""):
        with self.add_children_as_readables():
            self.tcb_settings: SignalRW[str] = isis_epics_signal_rw(str, f"{dae_prefix}TCBSETTINGS")
        super().__init__(name=name)

    async def read(self) -> Dict[str, Any]:
        value = await self.tcb_settings.get_value()
        value_dehexed = dehex_and_decompress(value.encode())
        return {self.tcb_settings.name: convert_xml_to_tcb_settings(value_dehexed)}

    @AsyncStatus.wrap
    async def set(self, value: DaeTCBSettingsData) -> None:
        the_value_to_write = convert_tcb_settings_to_xml(value)
        await self.tcb_settings.set(the_value_to_write, wait=True)
