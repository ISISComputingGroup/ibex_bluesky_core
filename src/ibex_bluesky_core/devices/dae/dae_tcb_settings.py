"""ophyd-async devices and utilities for the DAE time channel settings."""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from typing import Dict
from xml.etree.ElementTree import tostring

from bluesky.protocols import Locatable, Location, Movable
from ophyd_async.core import AsyncStatus, Device, SignalRW

from ibex_bluesky_core.devices import (
    compress_and_hex,
    dehex_and_decompress,
    isis_epics_signal_rw,
)
from ibex_bluesky_core.devices.dae import (
    convert_xml_to_names_and_values,
    get_all_elements_in_xml_with_child_called_name,
    set_value_in_dae_xml,
)

logger = logging.getLogger(__name__)

TIME_UNIT = "Time Unit"
CALCULATION_METHOD = "Calculation Method"
TIME_CHANNEL_FILE = "Time Channel File"


class TimeUnit(Enum):
    """Time unit for DAE TCB settings."""

    MICROSECONDS = 0
    NANOSECONDS = 1


class CalculationMethod(Enum):
    """Calculation method for DAE TCB settings."""

    SPECIFY_PARAMETERS = 0
    USE_TCB_FILE = 1


class TimeRegimeMode(Enum):
    """Time Regime Mode options for a single row."""

    BLANK = 0  # Blank
    DT = 1  # dT = C
    DTDIVT = 2  # dT/T = C
    DTDIVT2 = 3  # dT/T**2 = C
    SHIFTED = 4  # Shifted


@dataclass(kw_only=True)
class TimeRegimeRow:
    """A single time regime row."""

    from_: float | None = None
    to: float | None = None
    steps: float | None = None
    mode: TimeRegimeMode | None = None


@dataclass
class TimeRegime:
    """Time regime - contains a dict(rows) which is row_number:TimeRegimeRow."""

    rows: Dict[int, TimeRegimeRow]


@dataclass(kw_only=True)
class DaeTCBSettingsData:
    """Dataclass for the DAE TCB settings."""

    tcb_tables: Dict[int, TimeRegime] | None = None
    tcb_file: str | None = None
    time_unit: TimeUnit | None = None
    tcb_calculation_method: CalculationMethod | None = None


def _convert_xml_to_tcb_settings(value: str) -> DaeTCBSettingsData:
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


def _convert_tcb_settings_to_xml(current_xml: str, settings: DaeTCBSettingsData) -> str:
    # get xml here, then substitute values from the dataclasses
    root = ET.fromstring(current_xml)
    elements = get_all_elements_in_xml_with_child_called_name(root)
    set_value_in_dae_xml(elements, TIME_CHANNEL_FILE, settings.tcb_file)
    set_value_in_dae_xml(elements, CALCULATION_METHOD, settings.tcb_calculation_method)
    set_value_in_dae_xml(elements, TIME_UNIT, settings.time_unit)
    if settings.tcb_tables is not None:
        for tr, regime in settings.tcb_tables.items():
            for r, row in regime.rows.items():
                set_value_in_dae_xml(elements, f"TR{tr} From {r}", row.from_)
                set_value_in_dae_xml(elements, f"TR{tr} To {r}", row.to)
                set_value_in_dae_xml(elements, f"TR{tr} Steps {r}", row.steps)
                set_value_in_dae_xml(elements, f"TR{tr} In Mode {r}", row.mode)
    return tostring(root, encoding="unicode")


class DaeTCBSettings(Device, Locatable, Movable):
    """Subdevice for the DAE time channel settings."""

    def __init__(self, dae_prefix: str, name: str = "") -> None:
        """Set up signal for the DAE time channel settings.

        See DaeTCBSettingsData for options.
        """
        self._raw_tcb_settings: SignalRW[str] = isis_epics_signal_rw(
            str, f"{dae_prefix}TCBSETTINGS"
        )
        super().__init__(name=name)

    async def locate(self) -> Location[DaeTCBSettingsData]:
        """Retrieve and convert the current XML to DaeTCBSettingsData."""
        value = await self._raw_tcb_settings.get_value()
        value_dehexed = dehex_and_decompress(value.encode()).decode()
        tcb_settings = _convert_xml_to_tcb_settings(value_dehexed)
        logger.info("locate tcb settings: %s", tcb_settings)
        return {"setpoint": tcb_settings, "readback": tcb_settings}

    @AsyncStatus.wrap
    async def set(self, value: DaeTCBSettingsData) -> None:
        """Set any changes in the tcb settings to the XML."""
        current_xml = await self._raw_tcb_settings.get_value()
        current_xml_dehexed = dehex_and_decompress(current_xml.encode()).decode()
        xml = _convert_tcb_settings_to_xml(current_xml_dehexed, value)
        the_value_to_write = compress_and_hex(xml).decode()
        logger.info("set tcb settings: %s", the_value_to_write)
        await self._raw_tcb_settings.set(the_value_to_write, wait=True, timeout=None)
