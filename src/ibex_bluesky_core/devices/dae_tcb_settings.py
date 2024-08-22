from dataclasses import dataclass
from typing import Dict, Any

from ophyd_async.core import SignalRW, StandardReadable, AsyncStatus

from ibex_bluesky_core.utils.dae_xml_utils import convert_xml_to_names_and_values
from ibex_bluesky_core.utils.dehex_and_decompress import dehex_and_decompress
from ibex_bluesky_core.utils.isis_epics_signals import isis_epics_signal_rw
import xml.etree.ElementTree as ET


@dataclass
class DaeTCBSettingsData:
    tcb_file = None
    tcb_tables = []
    tcb_calculation_method = None


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
