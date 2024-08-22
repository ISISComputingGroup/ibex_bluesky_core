from dataclasses import dataclass
from ophyd_async.core import SignalRW, StandardReadable, AsyncStatus
from ibex_bluesky_core.utils.dae_xml_utils import convert_xml_to_names_and_values
from ibex_bluesky_core.utils.isis_epics_signals import isis_epics_signal_rw
import xml.etree.ElementTree as ET


@dataclass
class DaeSettingsData:
    wiring_filepath: str|None = None
    detector_filepath: str|None = None
    spectra_filepath: str|None = None
    mon_spect: int|None = None
    mon_from: int|None = None
    mon_to: int|None = None
    dae_sync = None
    smp_veto = None
    ts2_veto = None
    hz50_veto = None
    ext0_veto = None
    ext1_veto = None
    ext2_veto = None
    ext3_veto = None
    fermi_veto = None
    fermi_delay: int|None = None
    fermi_width: int|None = None


def convert_xml_to_dae_settings(value: str) -> DaeSettingsData:
    root = ET.fromstring(value)
    settings_from_xml = convert_xml_to_names_and_values(root)
    print(settings_from_xml)
    settings = DaeSettingsData()
    # TODO parse the keys and values
    return settings


def convert_dae_settings_to_xml(settings: DaeSettingsData) -> str:
    pass


class DaeSettings(StandardReadable):
    def __init__(self, dae_prefix, name=""):
        with self.add_children_as_readables():
            self.dae_settings: SignalRW[str] = isis_epics_signal_rw(str, f"{dae_prefix}DAESETTINGS")

        super().__init__(name=name)

    async def read(self) -> DaeSettingsData:
        the_xml = await self.dae_settings.get_value()

        # This is wrong, read() needs to return dict[str, Reading], where the below should be the value of the reading
        return convert_xml_to_dae_settings(the_xml)

    @AsyncStatus.wrap
    async def set(self, value: DaeSettingsData) -> None:
        the_value_to_write = convert_dae_settings_to_xml(value)
        await self.dae_settings.set(the_value_to_write, wait=True)
