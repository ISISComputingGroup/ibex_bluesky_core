from dataclasses import dataclass, field
from enum import Enum
from typing import List
from xml.etree.ElementTree import tostring

from bluesky.protocols import Locatable, Location
from ophyd_async.core import SignalRW, AsyncStatus, Device

import xml.etree.ElementTree as ET

from ibex_bluesky_core.devices import convert_xml_to_names_and_values, isis_epics_signal_rw

from ibex_bluesky_core.devices import get_all_elements_in_xml_with_child_called_name, set_value_in_dae_xml

OUTPUT_DELAY = "Output Delay (us)"
PERIOD_SEQUENCES = "Hardware Period Sequences"
PERIOD_FILE = "Period File"
PERIOD_SETUP_SOURCE = "Period Setup Source"
PERIOD_TYPE = "Period Type"
PERIODS_SOFT_NUM = "Number Of Software Periods"


class PeriodType(Enum):
    SOFTWARE = 0
    HARDWARE_DAE = 1
    HARDWARE_EXTERNAL = 2


class PeriodSource(Enum):
    PARAMETERS = 0
    FILE = 1


@dataclass
class SinglePeriodSettings:
    type: int | None = None
    frames: int | None = None
    output: int | None = None
    label: str | None = None


@dataclass
class DaePeriodSettingsData:
    periods_soft_num: None | int = None
    periods_type: PeriodType | None = None
    periods_src: PeriodSource | None = None
    periods_file: None | str = None
    periods_seq: None | int = None
    periods_delay: None | int = None
    periods_settings: List[SinglePeriodSettings] = field(default_factory=lambda: [])


def convert_xml_to_period_settings(value: str) -> DaePeriodSettingsData:
    root = ET.fromstring(value)
    settings_from_xml = convert_xml_to_names_and_values(root)
    return DaePeriodSettingsData(
        periods_soft_num=int(settings_from_xml[PERIODS_SOFT_NUM]),
        periods_type=PeriodType(int(settings_from_xml[PERIOD_TYPE])),
        periods_src=PeriodSource(int(settings_from_xml[PERIOD_SETUP_SOURCE])),
        periods_file=settings_from_xml[PERIOD_FILE],
        periods_seq=int(settings_from_xml[PERIOD_SEQUENCES]),
        periods_delay=int(settings_from_xml[OUTPUT_DELAY]),
        periods_settings=[
            SinglePeriodSettings(
                type=int(settings_from_xml[f"Type {i}"]),
                frames=int(settings_from_xml[f"Frames {i}"]),
                output=int(settings_from_xml[f"Output {i}"]),
                label=settings_from_xml[f"Label {i}"],
            )
            for i in range(1, 8+1)
        ],
    )


def convert_period_settings_to_xml(current_xml: str, value: DaePeriodSettingsData):
    # get xml here, then substitute values from the dataclasses
    root = ET.fromstring(current_xml)
    elements  = get_all_elements_in_xml_with_child_called_name(root)
    # yuck, use a for loop
    set_value_in_dae_xml(elements, PERIODS_SOFT_NUM, value.periods_soft_num)
    set_value_in_dae_xml(elements, PERIOD_TYPE, value.periods_type)
    set_value_in_dae_xml(elements, PERIOD_SETUP_SOURCE, value.periods_src)
    set_value_in_dae_xml(elements, PERIOD_FILE, value.periods_file)
    set_value_in_dae_xml(elements, PERIOD_SEQUENCES, value.periods_seq)
    set_value_in_dae_xml(elements, OUTPUT_DELAY, value.periods_delay)
    for i in range(1,8+1):
        set_value_in_dae_xml(elements, f"Type {i}", value.periods_settings[i - 1].type)
        set_value_in_dae_xml(elements, f"Frames {i}", value.periods_settings[i - 1].frames)
        set_value_in_dae_xml(elements, f"Output {i}", value.periods_settings[i - 1].output)
        set_value_in_dae_xml(elements, f"Label {i}", value.periods_settings[i - 1].type)
    print(tostring(root, encoding="unicode"))
    return tostring(root, encoding="unicode")




class DaePeriodSettings(Device, Locatable):
    async def locate(self) -> Location:
        value = await self.period_settings.get_value()
        period_settings = convert_xml_to_period_settings(value)
        return {"setpoint": period_settings, "readback": period_settings}

    def __init__(self, dae_prefix, name=""):
        self.period_settings: SignalRW[str] = isis_epics_signal_rw(
            str, f"{dae_prefix}HARDWAREPERIODS"
        )
        super().__init__(name=name)

    @AsyncStatus.wrap
    async def set(self, value: DaePeriodSettingsData) -> None:
        # the_value_to_write = convert_period_settings_to_xml(value)
        # current_location = await self.locate()
        # current_settings = current_location["readback"]
        current_xml = await self.period_settings.get_value()
        to_write = convert_period_settings_to_xml(current_xml, value)

        await self.period_settings.set(to_write, wait=True)
