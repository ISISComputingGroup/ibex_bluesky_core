"""ophyd-async devices and utilities for the general DAE settings."""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from xml.etree.ElementTree import tostring

from bluesky.protocols import Locatable, Location, Movable
from ophyd_async.core import AsyncStatus, SignalRW, StandardReadable

from ibex_bluesky_core.devices import (
    isis_epics_signal_rw,
)
from ibex_bluesky_core.devices.dae._helpers import (
    _convert_xml_to_names_and_values,
    _get_all_elements_in_xml_with_child_called_name,
    _set_value_in_dae_xml,
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


class DaeTimingSource(Enum):
    """The DAE timing source.

    See Also:
        :external+ibex_user_manual:ref:`concept_timing` in the IBEX user manual.

    """

    ISIS = 0
    """
    Timing pulse from the ISIS accelerator.
    """
    INTERNAL_TEST_CLOCK = 1
    """
    Timing pulse from the internal test clock.
    """
    SMP = 2
    """
    Timing source from a 'secondary master pulse' (usually a chopper).
    """
    MUON_CHERENKOV = 3
    """
    Cherenkov pulse timing (muon instruments only)
    """
    MUON_MS = 4
    """
    MS pulse timing (muon instruments only)
    """
    ISIS_FIRST_TS1 = 5
    """
    ISIS timing, but only counting on the first TS1 pulse after the 'missing' TS2 pulse.
    """
    ISIS_TS1_ONLY = 6
    """
    ISIS timing, but only counting TS1 pulses.
    """


@dataclass(kw_only=True)
class DaeSettingsData:
    """Dataclass for general DAE settings.

    All settings accept :py:obj:`None`, which means this setting will not be changed from
    the current setting.
    """

    wiring_filepath: str | None = None
    """
    Wiring table filepath.
    """
    detector_filepath: str | None = None
    """
    Detector table filepath.
    """
    spectra_filepath: str | None = None
    """
    Spectra table filepath.
    """
    mon_spect: int | None = None
    """
    Monitor spectrum number.
    """
    mon_from: int | None = None
    """
    Monitor integration lower bound (us).
    """
    mon_to: int | None = None
    """
    Monitor integration upper bound (us).
    """
    timing_source: DaeTimingSource | None = None
    """
    Dae timing source.
    """
    smp_veto: bool | None = None
    """
    SMP veto enabled.
    """
    ts2_veto: bool | None = None
    """
    TS2 veto enabled.
    """
    hz50_veto: bool | None = None
    """
    50Hz veto enabled.
    """
    ext0_veto: bool | None = None
    """
    External veto 0 enabled.
    """
    ext1_veto: bool | None = None
    """
    External veto 1 enabled.
    """
    ext2_veto: bool | None = None
    """
    External veto 2 enabled.
    """
    ext3_veto: bool | None = None
    """
    External veto 3 enabled.
    """
    fermi_veto: bool | None = None
    """
    Fermi chopper veto enabled.
    """
    fermi_delay: int | None = None
    """
    Fermi chopper veto desired delay (us).
    """
    fermi_width: int | None = None
    """
    Fermi chopper veto width (us).
    """
    muon_ms_mode: bool | None = None
    """
    MS mode enabled (muon instruments only).
    """
    muon_cherenkov_pulse: int | None = None
    """
    Cherenkov pulse selection (muon instruments only).
    """
    veto_0_name: str | None = None
    """
    Veto 0 name.
    """
    veto_1_name: str | None = None
    """
    Veto 1 name.
    """
    veto_2_name: str | None = None
    """
    Veto 2 name.
    """
    veto_3_name: str | None = None
    """
    Veto 3 name.
    """


def _convert_xml_to_dae_settings(value: str) -> DaeSettingsData:
    root = ET.fromstring(value)
    settings_from_xml = _convert_xml_to_names_and_values(root)
    return DaeSettingsData(
        wiring_filepath=settings_from_xml[WIRING_TABLE],
        detector_filepath=settings_from_xml[DETECTOR_TABLE],
        spectra_filepath=settings_from_xml[SPECTRA_TABLE],
        mon_spect=int(settings_from_xml[MONITOR_SPECTRUM]),
        mon_from=int(settings_from_xml[FROM]),
        mon_to=int(settings_from_xml[TO]),
        timing_source=DaeTimingSource(int(settings_from_xml[DAE_TIMING_SOURCE])),
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
    elements = _get_all_elements_in_xml_with_child_called_name(root)
    _set_value_in_dae_xml(elements, WIRING_TABLE, settings.wiring_filepath)
    _set_value_in_dae_xml(elements, DETECTOR_TABLE, settings.detector_filepath)
    _set_value_in_dae_xml(elements, SPECTRA_TABLE, settings.spectra_filepath)
    _set_value_in_dae_xml(elements, FROM, settings.mon_from)
    _set_value_in_dae_xml(elements, TO, settings.mon_to)
    _set_value_in_dae_xml(elements, MONITOR_SPECTRUM, settings.mon_spect)
    _set_value_in_dae_xml(elements, DAE_TIMING_SOURCE, settings.timing_source)
    _set_value_in_dae_xml(elements, SMP_CHOPPER_VETO, _bool_to_int_or_none(settings.smp_veto))
    _set_value_in_dae_xml(elements, TS2_PULSE_VETO, _bool_to_int_or_none(settings.ts2_veto))
    _set_value_in_dae_xml(elements, ISIS_50HZ_VETO, _bool_to_int_or_none(settings.hz50_veto))
    _set_value_in_dae_xml(elements, VETO0, _bool_to_int_or_none(settings.ext0_veto))
    _set_value_in_dae_xml(elements, VETO1, _bool_to_int_or_none(settings.ext1_veto))
    _set_value_in_dae_xml(elements, VETO2, _bool_to_int_or_none(settings.ext2_veto))
    _set_value_in_dae_xml(elements, VETO3, _bool_to_int_or_none(settings.ext3_veto))
    _set_value_in_dae_xml(elements, FERMI_CHOPPER_VETO, _bool_to_int_or_none(settings.fermi_veto))
    _set_value_in_dae_xml(elements, FC_DELAY, settings.fermi_delay)
    _set_value_in_dae_xml(elements, FC_WIDTH, settings.fermi_width)
    _set_value_in_dae_xml(elements, MUON_MS_MODE, _bool_to_int_or_none(settings.muon_ms_mode))
    _set_value_in_dae_xml(elements, MUON_CERENKOV_PULSE, settings.muon_cherenkov_pulse)
    _set_value_in_dae_xml(elements, VETO0_NAME, settings.veto_0_name)
    _set_value_in_dae_xml(elements, VETO1_NAME, settings.veto_1_name)
    _set_value_in_dae_xml(elements, VETO2_NAME, settings.veto_2_name)
    _set_value_in_dae_xml(elements, VETO3_NAME, settings.veto_3_name)
    return tostring(root, encoding="unicode")


class DaeSettings(StandardReadable, Locatable[DaeSettingsData], Movable[DaeSettingsData]):
    """Subdevice for the DAE general settings."""

    def __init__(self, dae_prefix: str, name: str = "") -> None:
        """DAE settings interface.

        See Also:
            :py:obj:`DaeSettingsData` for options.

        """
        self._raw_dae_settings: SignalRW[str] = isis_epics_signal_rw(
            str, f"{dae_prefix}DAESETTINGS"
        )
        super().__init__(name=name)

    async def locate(self) -> Location[DaeSettingsData]:
        """Retrieve the current DAE settings."""
        value = await self._raw_dae_settings.get_value()
        period_settings = _convert_xml_to_dae_settings(value)
        logger.info("locate dae settings: %s", period_settings)
        return {"setpoint": period_settings, "readback": period_settings}

    @AsyncStatus.wrap
    async def set(self, value: DaeSettingsData) -> None:
        """Change any modified DAE settings."""
        current_xml = await self._raw_dae_settings.get_value()
        to_write = _convert_dae_settings_to_xml(current_xml, value)
        logger.info("set dae settings: %s", to_write)
        await self._raw_dae_settings.set(to_write, wait=True, timeout=None)
