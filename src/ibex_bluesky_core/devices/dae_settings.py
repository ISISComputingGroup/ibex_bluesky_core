from dataclasses import dataclass

from ophyd_async.core import SignalRW, StandardReadable, AsyncStatus

from ibex_bluesky_core.devices.dae_period_settings import DaePeriodSettings
from ibex_bluesky_core.devices.dae_tcb_settings import DaeTCBSettings
from ibex_bluesky_core.utils.isis_epics_signals import isis_epics_signal_rw


@dataclass
class DaeSettingsData:
    wiring = None
    detector = None
    spectra = None
    mon_spect = None
    mon_from = None
    mon_to = None
    dae_sync = None
    smp_veto = None
    ts2_veto = None
    hz50_veto = None
    ext0_veto = None
    ext1_veto = None
    ext2_veto = None
    ext3_veto = None
    fermi_veto = None
    fermi_delay = None
    fermi_width = None


def convert_xml_to_dae_settings(xml: str) -> DaeSettingsData:
    pass


def convert_dae_settings_to_xml(settings: DaeSettingsData) -> str:
    pass


class DaeSettings(StandardReadable):
    def __init__(self, dae_prefix, name=""):
        with self.add_children_as_readables():
            self.the_big_horrible_xml: SignalRW[str] = isis_epics_signal_rw(
                str, f"{dae_prefix}DAESETTINGS"
            )

        super().__init__(name=name)

    async def read(self) -> DaeSettingsData:
        the_xml = await self.the_big_horrible_xml.get_value()

        # This is wrong, read() needs to return dict[str, Reading], where the below should be the value of the reading
        return convert_xml_to_dae_settings(the_xml)

    @AsyncStatus.wrap
    async def set(self, value: DaeSettingsData) -> None:
        the_value_to_write = convert_dae_settings_to_xml(value)
        await self.the_big_horrible_xml.set(the_value_to_write, wait=True)
