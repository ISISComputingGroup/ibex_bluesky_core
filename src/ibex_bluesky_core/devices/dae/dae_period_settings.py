"""ophyd-async devices and utilities for the DAE hardware period settings."""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from typing import List
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

OUTPUT_DELAY = "Output Delay (us)"
PERIOD_SEQUENCES = "Hardware Period Sequences"
PERIOD_FILE = "Period File"
PERIOD_SETUP_SOURCE = "Period Setup Source"
PERIOD_TYPE = "Period Type"
PERIODS_SOFT_NUM = "Number Of Software Periods"


class PeriodType(Enum):
    """General period type."""

    SOFTWARE = 0
    HARDWARE_DAE = 1
    HARDWARE_EXTERNAL = 2


class PeriodSource(Enum):
    """The period setup source, whether to use parameters or file."""

    PARAMETERS = 0
    FILE = 1


@dataclass(kw_only=True)
class SinglePeriodSettings:
    """Dataclass for the settings on a single period."""

    type: int | None = None
    frames: int | None = None
    output: int | None = None
    label: str | None = None


@dataclass(kw_only=True)
class DaePeriodSettingsData:
    """Dataclass for the hardware period settings."""

    periods_settings: List[SinglePeriodSettings] | None = None
    periods_soft_num: None | int = None
    periods_type: PeriodType | None = None
    periods_src: PeriodSource | None = None
    periods_file: None | str = None
    periods_seq: None | int = None
    periods_delay: None | int = None


def _convert_xml_to_period_settings(value: str) -> DaePeriodSettingsData:
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
            for i in range(1, 8 + 1)
        ],
    )


def _convert_period_settings_to_xml(current_xml: str, value: DaePeriodSettingsData) -> str:
    # get xml here, then substitute values from the dataclasses
    root = ET.fromstring(current_xml)
    elements = get_all_elements_in_xml_with_child_called_name(root)
    set_value_in_dae_xml(elements, PERIODS_SOFT_NUM, value.periods_soft_num)
    set_value_in_dae_xml(elements, PERIOD_TYPE, value.periods_type)
    set_value_in_dae_xml(elements, PERIOD_SETUP_SOURCE, value.periods_src)
    set_value_in_dae_xml(elements, PERIOD_FILE, value.periods_file)
    set_value_in_dae_xml(elements, PERIOD_SEQUENCES, value.periods_seq)
    set_value_in_dae_xml(elements, OUTPUT_DELAY, value.periods_delay)
    if value.periods_settings is not None:
        for i in range(1, 8 + 1):
            period = value.periods_settings[i - 1]
            set_value_in_dae_xml(elements, f"Type {i}", period.type)
            set_value_in_dae_xml(elements, f"Frames {i}", period.frames)
            set_value_in_dae_xml(elements, f"Output {i}", period.output)
            set_value_in_dae_xml(elements, f"Label {i}", period.label)
    return tostring(root, encoding="unicode")


class DaePeriodSettings(Device, Locatable, Movable):
    """Subdevice for the DAE hardware period settings."""

    def __init__(self, dae_prefix: str, name: str = "") -> None:
        """Set up signal for the DAE period settings.

        See DaePeriodSettingsData for options.
        """
        self._raw_period_settings: SignalRW[str] = isis_epics_signal_rw(
            str, f"{dae_prefix}HARDWAREPERIODS"
        )
        super().__init__(name=name)

    async def locate(self) -> Location[DaePeriodSettingsData]:
        """Retrieve and convert the current XML to DaePeriodSettingsData."""
        value = await self._raw_period_settings.get_value()
        period_settings = _convert_xml_to_period_settings(value)
        logger.debug("locate period settings: %s", period_settings)
        return {"setpoint": period_settings, "readback": period_settings}

    @AsyncStatus.wrap
    async def set(self, value: DaePeriodSettingsData) -> None:
        """Set any changes in the period settings to the XML."""
        current_xml = await self._raw_period_settings.get_value()
        to_write = _convert_period_settings_to_xml(current_xml, value)
        logger.info("set period settings: %s", to_write)
        await self._raw_period_settings.set(to_write, wait=True, timeout=None)
