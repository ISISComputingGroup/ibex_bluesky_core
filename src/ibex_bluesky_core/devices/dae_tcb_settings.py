from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any

from ophyd_async.core import SignalRW, StandardReadable, AsyncStatus


import xml.etree.ElementTree as ET

from ibex_bluesky_core.devices import (
    convert_xml_to_names_and_values,
    isis_epics_signal_rw,
    dehex_and_decompress,
)

from src.ibex_bluesky_core.devices import get_all_elements_in_xml_with_child_called_name

TIME_UNIT = "Time Unit"
CALCULATION_METHOD = "Calculation Method"
TIME_CHANNEL_FILE = "Time Channel File"


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
class TimeRegimeRow:
    from_: float | None = None
    to: float | None = None
    steps: float | None = None
    mode: TimeRegimeMode | None = None


@dataclass
class TimeRegime:
    rows: Dict[int, TimeRegimeRow] = field(
        default_factory=lambda: {i: TimeRegimeRow() for i in range(1, 6)}
    )


@dataclass
class DaeTCBSettingsData:
    tcb_file: str | None = None
    time_unit: TimeUnit | None = None
    tcb_tables: Dict[int, TimeRegime] = field(
        default_factory=lambda: {i: TimeRegime() for i in range(1, 7)}
    )
    tcb_calculation_method: CalculationMethod | None = None


def convert_xml_to_tcb_settings(value: str) -> DaeTCBSettingsData:
    root = ET.fromstring(value)
    settings_from_xml = convert_xml_to_names_and_values(root)

    return DaeTCBSettingsData(
        tcb_file=settings_from_xml[TIME_CHANNEL_FILE],
        tcb_calculation_method=CalculationMethod(int(settings_from_xml[CALCULATION_METHOD])),
        time_unit=TimeUnit(int(settings_from_xml[TIME_UNIT])),
        tcb_tables={
            tr: TimeRegime(
                rows={
                    r: TimeRegimeRow(
                        from_=float(settings_from_xml[f"TR{tr} From {r}"]),
                        to=float(settings_from_xml[f"TR{tr} To {r}"]),
                        steps=float(settings_from_xml[f"TR{tr} Steps {r}"]),
                        mode=TimeRegimeMode(int(settings_from_xml[f"TR{tr} In Mode {r}"])),
                    )
                    for r in range(1, 6)
                }
            )
            for tr in range(1, 7)
        },
    )


def convert_tcb_settings_to_xml(current_xml: str, value: DaeTCBSettingsData) -> str:
    # get xml here, then substitute values from the dataclasses
    root = ET.fromstring(current_xml)

    elements  = get_all_elements_in_xml_with_child_called_name(root)

    for i in elements:
        if elements.find("Name") == TIME_UNIT:
            i.text = value.time_unit

    return root.tostring()


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
