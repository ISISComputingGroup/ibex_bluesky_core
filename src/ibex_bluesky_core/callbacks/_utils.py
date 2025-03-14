import os
from pathlib import Path
from platform import node

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
