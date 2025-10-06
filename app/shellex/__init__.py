import logging
import sys


logger = logging.getLogger("shellex")
logger.addHandler(logging.NullHandler())


def setup_logging():
    if any(arg in sys.argv for arg in ("-h", "--help")):
        return

    if logging.getLogger().hasHandlers():
        return

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  %(levelname)-7s  %(module)s: %(message)s",
        handlers=[logging.StreamHandler()],
    )
    logging.info("running in sandbox mode ...")

    logger.setLevel(logging.DEBUG)


if __name__ == "__main__" or (__package__ and __package__.startswith("app.shellex")):
    setup_logging()
