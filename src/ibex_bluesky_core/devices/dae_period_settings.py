from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List

from bluesky.protocols import Movable, Status
from ophyd_async.core import SignalRW, StandardReadable, AsyncStatus

import xml.etree.ElementTree as ET

from ibex_bluesky_core.devices import convert_xml_to_names_and_values, isis_epics_signal_rw


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
        periods_soft_num=int(settings_from_xml["Number Of Software Periods"]),
        periods_type=PeriodType(int(settings_from_xml["Period Type"])),
        periods_src=PeriodSource(int(settings_from_xml["Period Setup Source"])),
        periods_file=settings_from_xml["Period File"],
        periods_seq=int(settings_from_xml["Hardware Period Sequences"]),
        periods_delay=int(settings_from_xml["Output Delay (us)"]),
        periods_settings=[
            SinglePeriodSettings(
                type=int(settings_from_xml[f"Type {i}"]),
                frames=int(settings_from_xml[f"Frames {i}"]),
                output=int(settings_from_xml[f"Output {i}"]),
                label=settings_from_xml[f"Label {i}"],
            )
            for i in range(1, 9)
        ],
    )


def convert_period_settings_to_xml(value: DaePeriodSettingsData):
    return ET.fromstring("")


class DaePeriodSettings(StandardReadable, Movable):
    def __init__(self, dae_prefix, name=""):
        with self.add_children_as_readables():
            self.period_settings: SignalRW[str] = isis_epics_signal_rw(
                str, f"{dae_prefix}HARDWAREPERIODS"
            )
        super().__init__(name=name)

    async def read(self) -> Dict[str, Any]:
        value = await self.period_settings.get_value()

        # This is wrong, read() needs to return dict[str, Reading], where the below should be the value of the reading

        return {self.period_settings.name: convert_xml_to_period_settings(value)}

    @AsyncStatus.wrap
    async def set(self, value: DaePeriodSettingsData) -> Status:
        the_value_to_write = convert_period_settings_to_xml(value)
        await self.period_settings.set(the_value_to_write, wait=True)
