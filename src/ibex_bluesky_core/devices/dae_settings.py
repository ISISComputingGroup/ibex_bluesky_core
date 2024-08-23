from dataclasses import dataclass
from enum import Enum

from ophyd_async.core import SignalRW, StandardReadable, AsyncStatus
import xml.etree.ElementTree as ET

from ibex_bluesky_core.devices import convert_xml_to_names_and_values, isis_epics_signal_rw


class TimingSource(Enum):
    ISIS = 0
    INTERNAL_TEST_CLOCK = 1
    SMP = 2
    MUON_CERENKOV = 3
    MUON_MS = 4
    ISIS_FIRST_TS1 = 5
    ISIS_TS1_ONLY = 6


@dataclass
class DaeSettingsData:
    wiring_filepath: str | None = None
    detector_filepath: str | None = None
    spectra_filepath: str | None = None
    mon_spect: int | None = None
    mon_from: int | None = None
    mon_to: int | None = None
    timing_source: TimingSource | None = None
    smp_veto: bool | None = None
    ts2_veto: bool | None = None
    hz50_veto: bool | None = None
    ext0_veto: bool | None = None
    ext1_veto: bool | None = None
    ext2_veto: bool | None = None
    ext3_veto: bool | None = None
    fermi_veto: bool | None = None
    fermi_delay: int | None = None
    fermi_width: int | None = None
    muon_ms_mode: bool | None = None
    muon_cherenkov_pulse: int | None = None
    veto_0_name: str | None = None
    veto_1_name: str | None = None
    veto_2_name: str | None = None
    veto_3_name: str | None = None


def convert_xml_to_dae_settings(value: str) -> DaeSettingsData:
    root = ET.fromstring(value)
    settings_from_xml = convert_xml_to_names_and_values(root)
    return DaeSettingsData(
        wiring_filepath=settings_from_xml["Wiring Table"],
        detector_filepath=settings_from_xml["Detector Table"],
        spectra_filepath=settings_from_xml["Spectra Table"],
        mon_spect=int(settings_from_xml["Monitor Spectrum"]),
        mon_from=int(settings_from_xml["from"]),
        mon_to=int(settings_from_xml["to"]),
        timing_source=TimingSource(int(settings_from_xml["DAETimingSource"])),
        smp_veto=bool(int(settings_from_xml["SMP (Chopper) Veto"])),
        # Yes, there is a space in some of the vetos
        ts2_veto=bool(int(settings_from_xml[" TS2 Pulse Veto"])),
        hz50_veto=bool(int(settings_from_xml[" ISIS 50Hz Veto"])),
        ext0_veto=bool(int(settings_from_xml["Veto 0"])),
        ext1_veto=bool(int(settings_from_xml["Veto 1"])),
        ext2_veto=bool(int(settings_from_xml["Veto 2"])),
        ext3_veto=bool(int(settings_from_xml["Veto 3"])),
        fermi_veto=bool(int(settings_from_xml[" Fermi Chopper Veto"])),
        fermi_delay=int(settings_from_xml["FC Delay"]),
        fermi_width=int(settings_from_xml["FC Width"]),
        muon_ms_mode=bool(int(settings_from_xml["Muon MS Mode"])),
        muon_cherenkov_pulse=int(settings_from_xml["Muon Cerenkov Pulse"]),
        veto_0_name=settings_from_xml["Veto 0 Name"],
        veto_1_name=settings_from_xml["Veto 1 Name"],
        veto_2_name=settings_from_xml["Veto 2 Name"],
        veto_3_name=settings_from_xml["Veto 3 Name"],
    )


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
