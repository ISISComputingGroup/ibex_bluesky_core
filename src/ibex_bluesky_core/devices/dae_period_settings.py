from dataclasses import dataclass
from typing import Dict, Any

from ophyd_async.core import SignalRW, StandardReadable, AsyncStatus

from ibex_bluesky_core.utils.dae_xml_utils import convert_xml_to_names_and_values
from ibex_bluesky_core.utils.isis_epics_signals import isis_epics_signal_rw
import xml.etree.ElementTree as ET


@dataclass
class SinglePeriodSettings:
    type: int | None = None
    frames: int | None = None
    output: int | None = None
    label: str | None = None


@dataclass
class DaePeriodSettingsData:
    periods_soft_num: None | int = None
    periods_type = None  # TODO add enum for this based on choices?
    periods_src = None  # TODO add enum for this based on choices?
    periods_file: None | str = None
    periods_seq: None | int = None
    periods_delay: None | int = None
    periods_settings = []


def convert_xml_to_period_settings(value: str) -> DaePeriodSettingsData:
    root = ET.fromstring(value)
    settings_from_xml = convert_xml_to_names_and_values(root)
    print(settings_from_xml)
    settings = DaePeriodSettingsData()
    settings.periods_soft_num = int(settings_from_xml["Number Of Software Periods"])
    settings.periods_type = int(settings_from_xml["Period Type"])
    settings.periods_src = int(settings_from_xml["Period Setup Source"])
    settings.periods_file = settings_from_xml["Period File"]
    settings.periods_seq = int(settings_from_xml["Hardware Period Sequences"])
    settings.periods_delay = int(settings_from_xml["Output Delay (us)"])
    period_settings = []
    for i in range(1, 9):
        single_period = SinglePeriodSettings()
        single_period.type = int(settings_from_xml[f"Type {i}"])
        single_period.frames = int(settings_from_xml[f"Frames {i}"])
        single_period.output = int(settings_from_xml[f"Output {i}"])
        single_period.label = settings_from_xml[f"Label {i}"]
        period_settings.append(single_period)
    settings.periods_settings = period_settings

    print(settings)

    return settings


def convert_period_settings_to_xml(value: DaePeriodSettingsData):
    return ET.fromstring("")


class DaePeriodSettings(StandardReadable):
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
    async def set(self, value: DaePeriodSettingsData) -> None:
        the_value_to_write = convert_period_settings_to_xml(value)
        await self.period_settings.set(the_value_to_write, wait=True)
