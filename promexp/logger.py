__all__ = ["log_traceback", "logger"]

import logging
import sys
import traceback

# Configure base logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr,
)

logger = logging.getLogger("promexp")


def log_traceback(message="Exception!", logger=logger):
    tb = traceback.format_exc()
    indented_tb = "\n".join("    " + line for line in tb.splitlines())
    msg = f"{message}\n\n{indented_tb}"
    logger.error(msg)
    return msg
