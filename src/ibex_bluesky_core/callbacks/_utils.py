import os
from pathlib import Path
from platform import node

INSTRUMENT = node()
OUTPUT_DIR_ENV_VAR = "IBEX_BLUESKY_OUTPUT_DIR"

if env_path := os.environ.get(OUTPUT_DIR_ENV_VAR):
    DEFAULT_PATH = Path(env_path)
else:
    DEFAULT_PATH = Path("//isis.cclrc.ac.uk/inst$") / INSTRUMENT / "user" / "TEST" / "scans"

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
