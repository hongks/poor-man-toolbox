import filecmp
import logging
import os
import re

from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import click

from .sqlite import SQLiteHandler


# typing annotations to avoid circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .configs import Config
    from .sqlite import SQLite


def compare_the_path(excludes: list[str], path: str, uri: str):
    filecmp.clear_cache()

    base_path = Path(path).resolve()
    exclude_patterns = [re.compile(ele) for ele in excludes]

    for file in base_path.rglob("*"):
        if file.is_dir():
            continue

        if any(pat.search(part) for part in file.parts for pat in exclude_patterns):
            # logging.debug(f"skipping {file}")
            continue

        relative_path = file.relative_to(base_path)
        counterpart = Path(uri) / relative_path

        result = counterpart.exists() and filecmp.cmp(file, counterpart, shallow=False)
        if not result:
            fn = str(file).replace(os.getcwd(), ".")
            logging.info(f"compared: {result!s:^5}, {fn}")


def echo(level: str, message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    click.echo(f"{timestamp}  {level.upper():7}  main      {message}")


def setup_logging(config: "Config", sqlite: "SQLite"):
    # set up logging
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    logging.basicConfig(
        format=config.logging.format,
        level=getattr(logging, config.logging.level, logging.INFO),
        handlers=[
            console_handler,
            RotatingFileHandler(config.logging.filename),
            SQLiteHandler(sqlite),
        ],
    )

    # ... and silent the others
    for logger in ["httpcore", "httpx", "paramiko", "urllib3", "watchdog", "werkzeug"]:
        logging.getLogger(logger).setLevel(logging.WARNING)

    # misc
    # logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)


def walk_the_path(
    excludes: list[str], sftp: str, local_path: str, remote_path: str, counts: int = 0
):
    try:
        items = sftp.listdir_attr(remote_path)
    except FileNotFoundError:
        logging.warning(f"remote path not found: {remote_path}")
        return counts

    local_path = Path(local_path)
    local_path.mkdir(parents=True, exist_ok=True)

    exclude_patterns = [re.compile(ele) for ele in excludes]

    for item in items:
        if any(pat.search(item.filename) for pat in exclude_patterns):
            logging.debug(f"skipping {item.filename}")
            continue

        local_file = local_path / item.filename
        remote_file = f"{remote_path.rstrip('/')}/{item.filename}"

        if item.longname.startswith("d"):  # directory
            counts = walk_the_path(
                excludes, sftp, local_file, remote_file, counts=counts
            )

        else:
            try:
                sftp.get(remote_file, str(local_file))
                os.utime(local_file, (item.st_mtime, item.st_mtime))

                counts += 1
                logging.debug(f"copied {remote_file}")

            except (OSError, IOError) as e:
                logging.error(f"failed to copy {remote_file}: {e}")

    return counts
