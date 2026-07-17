import logging
import sys
import traceback

class CustomLogger(logging.Logger):
    def goodnews(self, msg, *args, **kwargs):
        # Translate goodnews to INFO level
        self.info(msg, *args, **kwargs)

# Register CustomLogger as the default logger class
logging.setLoggerClass(CustomLogger)

# Configure base logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stderr
)

logger = logging.getLogger("promexp")
logger.show_time = True  # Backward compatibility for logging.show_time = True

def log_traceback(message="Exception!", logger=logger):
    tb = traceback.format_exc()
    indented_tb = "\n".join("    " + line for line in tb.splitlines())
    msg = f"{message}\n\n{indented_tb}"
    logger.error(msg)
    return msg
