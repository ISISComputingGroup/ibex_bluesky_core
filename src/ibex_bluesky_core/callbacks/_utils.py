from pathlib import Path
from platform import node

INSTRUMENT = node()
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
