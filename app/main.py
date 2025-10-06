import logging
import sys
import time

from logging.handlers import RotatingFileHandler
from pathlib import Path

import click

from browsers.main import main as browsers
from dockerex.main import main as dockerex
from filesync.main import main as filesync
from folders.main import main as folders
from search.main import main as search
from shellex.main import main as shellex

from helpers.configs import Config
from helpers.sqlite import SQLite, SQLiteHandler


# ################################################################################
# sub routines


def setup_logging(config: "Config", sqlite: "SQLite", *, console_only: bool = False):
    # set up logging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    handlers = [console_handler]

    if not console_only:
        handlers.append(RotatingFileHandler(config.logging.filename))
        handlers.append(SQLiteHandler(sqlite))

    logging.basicConfig(
        format=config.logging.format,
        level=getattr(logging, config.logging.level, logging.INFO),
        handlers=handlers,
    )

    # ... and silent the others
    for logger in ["httpcore", "httpx", "paramiko", "urllib3", "watchdog", "werkzeug"]:
        logging.getLogger(logger).setLevel(logging.WARNING)

    # misc
    # logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


# ################################################################################
# main routine


@click.group()
@click.option(
    "--debug",
    "-d",
    is_flag=True,
    help="enable debug mode.",
)
@click.option(
    "--reset",
    "-e",
    is_flag=True,
    help="remove caches and generated logs.",
)
@click.option(
    "--version",
    "-v",
    is_flag=True,
    help="show the version and exit.",
)
@click.help_option(
    "--help",
    "-h",
    help="show this message and exit.",
)
@click.pass_context
def main(context, debug: bool, reset: bool, version: bool):
    context.ensure_object(dict)
    if any(arg in sys.argv for arg in ("-h", "--help")):
        return

    config = Config()
    if version:
        click.echo(f"version {config.version}")
        return

    sqlite = SQLite(config)
    config.sync(sqlite.Session())
    if debug:
        config.logging.level = "DEBUG"

    setup_logging(config, sqlite, console_only=reset)
    if debug:
        logging.info("debug mode on!")

    if reset:
        logging.info("resetting, removing caches and logs ...")
        tic = time.time()

        Path("./run").mkdir(parents=True, exist_ok=True)
        for pattern in ["cache.sqlite*", "poor-man-toolbox.log*"]:
            for file in Path("./run").glob(pattern):
                if file.exists():
                    file.unlink()
                    logging.info(f"- deleted: {file}")

        logging.info(f"... done, reset in {time.time() - tic:.3f}s!")
        return

    logging.info("initialized!")
    logging.info(f"local temp path: {Path('./run').absolute()}/")


@main.result_callback()
def after_command(result, **kwargs):
    logging.info("sayonara!")


# ################################################################################
# where it all begins

main.add_command(browsers, name="browsers")
main.add_command(dockerex, name="dockerex")
main.add_command(filesync, name="filesync")
main.add_command(folders, name="folders")
main.add_command(search, name="search")
main.add_command(shellex, name="shellex")

if __name__ == "__main__":
    main()
