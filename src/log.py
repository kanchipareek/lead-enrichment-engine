"""One logger for the whole project. Stdlib only."""
import logging, os, sys

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)-7s %(name)-12s %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)


def get_logger(name):
    return logging.getLogger(name)
