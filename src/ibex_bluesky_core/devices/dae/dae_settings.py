"""ophyd-async devices and utilities for the general DAE settings."""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from xml.etree.ElementTree import tostring

from bluesky.protocols import Locatable, Location, Movable
from ophyd_async.core import AsyncStatus, Device, SignalRW

from ibex_bluesky_core.devices import (
    isis_epics_signal_rw,
)
from ibex_bluesky_core.devices.dae import (
    convert_xml_to_names_and_values,
    get_all_elements_in_xml_with_child_called_name,
    set_value_in_dae_xml,
)

logger = logging.getLogger(__name__)

VETO3_NAME = "Veto 3 Name"
VETO2_NAME = "Veto 2 Name"
VETO1_NAME = "Veto 1 Name"
VETO0_NAME = "Veto 0 Name"
MUON_CERENKOV_PULSE = "Muon Cerenkov Pulse"
MUON_MS_MODE = "Muon MS Mode"
FC_WIDTH = "FC Width"
FC_DELAY = "FC Delay"
VETO3 = "Veto 3"
VETO2 = "Veto 2"
VETO1 = "Veto 1"
VETO0 = "Veto 0"
# Yes, there is a space prefixing some of the vetos
ISIS_50HZ_VETO = " ISIS 50Hz Veto"
TS2_PULSE_VETO = " TS2 Pulse Veto"
FERMI_CHOPPER_VETO = " Fermi Chopper Veto"
SMP_CHOPPER_VETO = "SMP (Chopper) Veto"
DAE_TIMING_SOURCE = "DAETimingSource"
TO = "to"
FROM = "from"
MONITOR_SPECTRUM = "Monitor Spectrum"
SPECTRA_TABLE = "Spectra Table"
DETECTOR_TABLE = "Detector Table"
WIRING_TABLE = "Wiring Table"


class TimingSource(Enum):
    """The DAE timing source."""

    ISIS = 0
    INTERNAL_TEST_CLOCK = 1
    SMP = 2
    MUON_CERENKOV = 3
    MUON_MS = 4
    ISIS_FIRST_TS1 = 5
    ISIS_TS1_ONLY = 6


@dataclass(kw_only=True)
class DaeSettingsData:
    """Dataclass for the general DAE settings."""

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


def _convert_xml_to_dae_settings(value: str) -> DaeSettingsData:
    root = ET.fromstring(value)
    settings_from_xml = convert_xml_to_names_and_values(root)
    return DaeSettingsData(
        wiring_filepath=settings_from_xml[WIRING_TABLE],
        detector_filepath=settings_from_xml[DETECTOR_TABLE],
        spectra_filepath=settings_from_xml[SPECTRA_TABLE],
        mon_spect=int(settings_from_xml[MONITOR_SPECTRUM]),
        mon_from=int(settings_from_xml[FROM]),
        mon_to=int(settings_from_xml[TO]),
        timing_source=TimingSource(int(settings_from_xml[DAE_TIMING_SOURCE])),
        smp_veto=bool(int(settings_from_xml[SMP_CHOPPER_VETO])),
        ts2_veto=bool(int(settings_from_xml[TS2_PULSE_VETO])),
        hz50_veto=bool(int(settings_from_xml[ISIS_50HZ_VETO])),
        ext0_veto=bool(int(settings_from_xml[VETO0])),
        ext1_veto=bool(int(settings_from_xml[VETO1])),
        ext2_veto=bool(int(settings_from_xml[VETO2])),
        ext3_veto=bool(int(settings_from_xml[VETO3])),
        fermi_veto=bool(int(settings_from_xml[FERMI_CHOPPER_VETO])),
        fermi_delay=int(settings_from_xml[FC_DELAY]),
        fermi_width=int(settings_from_xml[FC_WIDTH]),
        muon_ms_mode=bool(int(settings_from_xml[MUON_MS_MODE])),
        muon_cherenkov_pulse=int(settings_from_xml[MUON_CERENKOV_PULSE]),
        veto_0_name=settings_from_xml[VETO0_NAME],
        veto_1_name=settings_from_xml[VETO1_NAME],
        veto_2_name=settings_from_xml[VETO2_NAME],
        veto_3_name=settings_from_xml[VETO3_NAME],
    )


def _bool_to_int_or_none(to_convert: bool | None) -> int | None:
    return to_convert if to_convert is None else int(to_convert)


def _convert_dae_settings_to_xml(current_xml: str, settings: DaeSettingsData) -> str:
    root = ET.fromstring(current_xml)
    elements = get_all_elements_in_xml_with_child_called_name(root)
    set_value_in_dae_xml(elements, WIRING_TABLE, settings.wiring_filepath)
    set_value_in_dae_xml(elements, DETECTOR_TABLE, settings.detector_filepath)
    set_value_in_dae_xml(elements, SPECTRA_TABLE, settings.spectra_filepath)
    set_value_in_dae_xml(elements, FROM, settings.mon_from)
    set_value_in_dae_xml(elements, TO, settings.mon_to)
    set_value_in_dae_xml(elements, MONITOR_SPECTRUM, settings.mon_spect)
    set_value_in_dae_xml(elements, DAE_TIMING_SOURCE, settings.timing_source)
    set_value_in_dae_xml(elements, SMP_CHOPPER_VETO, _bool_to_int_or_none(settings.smp_veto))
    set_value_in_dae_xml(elements, TS2_PULSE_VETO, _bool_to_int_or_none(settings.ts2_veto))
    set_value_in_dae_xml(elements, ISIS_50HZ_VETO, _bool_to_int_or_none(settings.hz50_veto))
    set_value_in_dae_xml(elements, VETO0, _bool_to_int_or_none(settings.ext0_veto))
    set_value_in_dae_xml(elements, VETO1, _bool_to_int_or_none(settings.ext1_veto))
    set_value_in_dae_xml(elements, VETO2, _bool_to_int_or_none(settings.ext2_veto))
    set_value_in_dae_xml(elements, VETO3, _bool_to_int_or_none(settings.ext3_veto))
    set_value_in_dae_xml(elements, FERMI_CHOPPER_VETO, _bool_to_int_or_none(settings.fermi_veto))
    set_value_in_dae_xml(elements, FC_DELAY, settings.fermi_delay)
    set_value_in_dae_xml(elements, FC_WIDTH, settings.fermi_width)
    set_value_in_dae_xml(elements, MUON_MS_MODE, _bool_to_int_or_none(settings.muon_ms_mode))
    set_value_in_dae_xml(elements, MUON_CERENKOV_PULSE, settings.muon_cherenkov_pulse)
    set_value_in_dae_xml(elements, VETO0_NAME, settings.veto_0_name)
    set_value_in_dae_xml(elements, VETO1_NAME, settings.veto_1_name)
    set_value_in_dae_xml(elements, VETO2_NAME, settings.veto_2_name)
    set_value_in_dae_xml(elements, VETO3_NAME, settings.veto_3_name)
    return tostring(root, encoding="unicode")


class DaeSettings(Device, Locatable, Movable):
    """Subdevice for the DAE general settings."""

    def __init__(self, dae_prefix: str, name: str = "") -> None:
        """Set up signals for the DAE general settings.

        See DaeSettingsData for options.
        """
        self._raw_dae_settings: SignalRW[str] = isis_epics_signal_rw(
            str, f"{dae_prefix}DAESETTINGS"
        )
        super().__init__(name=name)

    async def locate(self) -> Location[DaeSettingsData]:
        """Retrieve and convert the current XML to DaeSettingsData."""
        value = await self._raw_dae_settings.get_value()
        period_settings = _convert_xml_to_dae_settings(value)
        logger.info("locate dae settings: %s", period_settings)
        return {"setpoint": period_settings, "readback": period_settings}

    @AsyncStatus.wrap
    async def set(self, value: DaeSettingsData) -> None:
        """Set any changes in the DAE settings to the XML."""
        current_xml = await self._raw_dae_settings.get_value()
        to_write = _convert_dae_settings_to_xml(current_xml, value)
        logger.info("set dae settings: %s", to_write)
        await self._raw_dae_settings.set(to_write, wait=True, timeout=None)
