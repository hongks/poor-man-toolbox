import logging
import shutil
import time

from datetime import datetime
from pathlib import Path

import click
import paramiko

from helpers.configs import Config
from helpers.sqlite import SQLite
from helpers.utilities import compare_the_path, echo, setup_logging, walk_the_path


# ################################################################################
# main routine


@click.command()
@click.option(
    "--download",
    "-w",
    is_flag=True,
    help="download files from remote server.",
)
@click.option(
    "--check",
    "-c",
    is_flag=True,
    help="check files downloaded from remote server.",
)
@click.option(
    "--target",
    "-t",
    help="run only selected target.",
)
@click.option(
    "--list",
    "-l",
    is_flag=True,
    help="list available targets.",
)
@click.option(
    "--generate",
    "-g",
    is_flag=True,
    help="generate skeleton config.xml.",
)
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
    help="remove downloaded files and generate logs.",
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
def main(download, check, target, list, generate, debug, reset, version):
    config = Config()
    if version:
        click.echo(f"version {config.version}")
        return

    sqlite = SQLite(config)
    config.sync(sqlite.Session())

    if reset:
        echo("info", "resetting, removing caches and logs ...")
        tic = time.time()

        Path("./run").mkdir(exist_ok=True)
        for target in config.targets:
            folder = Path(f"./run/{target['hostname']}")
            if folder.exists():
                shutil.rmtree(folder)
                echo("info", f"- deleted: {folder}/*")

        for pattern in ["cache.sqlite*", "poor-man-filesync.log*"]:
            for file in Path("./run").glob(pattern):
                if file.exists():
                    file.unlink()
                    echo("info", f"- deleted: {file}")

        echo("info", f"... done, reset in {time.time() - tic:.3f}s!")
        return

    if debug:
        config.logging.level = "DEBUG"
        echo("info", "debug mode on!")

    setup_logging(config, sqlite)
    logging.info("initialized!")
    logging.info(f"local temp path: {Path('./run').absolute()}/")

    if generate:
        file = Path(config.filename)
        if file.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file.rename(f"./run/config_{timestamp}.yml")
            logging.info(f"existing config file renamed to config_{timestamp}.yml")

        Path("./run").mkdir(exist_ok=True)
        shutil.copyfile(config.template, config.filename)
        logging.info("skeleton config file generated!")
        return

    if target:
        logging.info(f"target selected: {target}.")

    if list:
        logging.info("retrieving available targets ...")
        tic = time.time()

        for target in config.targets:
            logging.info(f"- {target['hostname']}")

        logging.info(f"... done, retrieved in {time.time() - tic:.3f}s!")
        return

    bingo = False
    if not any([download, check]):
        download = check = True

    if download:
        for host in config.targets:
            if target and target != host["hostname"]:
                continue

            bingo = True

            try:
                with paramiko.SSHClient() as ssh:
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(
                        host["hostname"],
                        port=host["port"],
                        username=host["username"],
                        password=host["password"],
                    )
                    logging.info(
                        f"connected to {host['username']}@{host['hostname']}:{host['port']}!"
                    )

                    with ssh.open_sftp() as sftp:
                        for project in host["projects"]:
                            tic = time.time()

                            if not any(
                                p["name"] == project["name"] for p in config.projects
                            ):
                                continue

                            logging.info(f"copying {project['name']} ...")
                            local_path = Path(
                                f"{Path('./run')}/{host['hostname']}/{project['name']}/"
                            )
                            if local_path.exists():
                                shutil.rmtree(local_path)

                            local_path.mkdir(parents=True, exist_ok=True)

                            counts = walk_the_path(
                                config.excludes, sftp, local_path, project["path"]
                            )
                            logging.info(
                                f"... {counts} files copied in {time.time() - tic:.3f}s!"
                            )

            except paramiko.AuthenticationException:
                logging.error(f"target selected: {target}, authentication failed!")
                return

            except Exception as err:
                logging.exception(f"unexpected {err=}, {type(err)=}")

    if check:
        for host in config.targets:
            if target and target != host["hostname"]:
                continue

            bingo = True

            for project in host["projects"]:
                tic = time.time()

                project_path = next(
                    (
                        p["path"]
                        for p in config.projects
                        if project["name"] == p["name"]
                    ),
                    None,
                )

                if not project_path:
                    continue

                logging.info(f"comparing {host['hostname']}'s {project['name']} ...")
                uri = f"./{Path('./run')}/{host['hostname']}/{project['name']}/"

                logging.debug(f"remote: {uri}")
                logging.debug(f"local: {project_path}")

                compare_the_path(config.excludes, project_path, uri)
                compare_the_path(config.excludes, uri, project_path)
                logging.info(f"... done in {time.time() - tic:.3f}s!")

    if not bingo:
        logging.info("nothing found!")


# ################################################################################
# where it all begins


if __name__ == "__main__":
    main()
