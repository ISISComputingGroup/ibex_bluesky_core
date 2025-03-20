import os
import logging
from datetime import datetime
from pathlib import Path
from platform import node
from typing import Union
from zoneinfo import ZoneInfo

from event_model import Event, RunStart, RunStop

logger = logging.getLogger(__name__)

OUTPUT_DIR_ENV_VAR = "IBEX_BLUESKY_CORE_OUTPUT"

# Common document metadata
UID = "uid"
TIME = "time"
DATA = "data"
RB = "rb_number"
START_TIME = "start_time"
NAME = "name"
SEQ_NUM = "seq_num"
DATA_KEYS = "data_keys"
DESCRIPTOR = "descriptor"
UNITS = "units"
PRECISION = "precision"
MOTORS = "motors"
UNKNOWN_RB = "Unknown RB"


def get_instrument() -> str:
    return node()


def get_default_output_path() -> Path:
    output_dir_env = os.environ.get(OUTPUT_DIR_ENV_VAR)
    return (
        Path("//isis.cclrc.ac.uk/inst$") / node() / "user" / "TEST" / "scans"
        if output_dir_env is None
        else Path(output_dir_env)
    )


def format_time(doc: Union[Event, RunStart, RunStop]):
    datetime_obj = datetime.fromtimestamp(doc[TIME])
    title_format_datetime = datetime_obj.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d_%H-%M-%S")
    return title_format_datetime


def _get_rb_num(doc):
    rb_num = doc.get(RB, UNKNOWN_RB)
    if rb_num == UNKNOWN_RB:
        logger.warning('No RB number found, saving to "%s"', UNKNOWN_RB)
    return rb_num
