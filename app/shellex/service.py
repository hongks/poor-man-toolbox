import subprocess
import time

from pathlib import Path

from click import Context

from . import logger
from .config import Config


class ShellEX:
    def __init__(self, configs: Config, context: Context):
        self.configs = configs
        self.context = context

    def provision(self, task: Config.Task):
        workdir = None

        try:
            if task.workdir:
                workdir = Path(task.workdir).expanduser()
                if not workdir.exists():
                    raise FileNotFoundError(
                        f"Working directory does not exist: {workdir}"
                    )

            logger.info(f"exec [ {task.action} ]")
            result = subprocess.run(
                task.action,  # the shell command to execute (string or list)
                capture_output=True,  # collect stdout/stderr instead of printing to terminal
                check=True,  # raise CalledProcessError if command exits with non-zero status
                shell=True,  # run command through the shell (e.g. bash/sh)
                text=True,  # decode output as str (not bytes) using default encoding (UTF-8)
                timeout=task.timeout,  # kill process if it runs longer than 60 seconds
                cwd=workdir,
            )

            if not task.silent:
                logger.info(f"output: {result.stdout.strip()}")

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as err:
            logger.error(f"'{task.action}' failed. error: {err}")

        except Exception as err:
            logger.exception(f"unexpected {err=}, {type(err)=}, {task.action}")

    def run(self, target: str, list: bool):
        # logger.debug(self.configs.projects)

        if list:
            logger.info("retrieving available projects ...")
            tic = time.time()

            for project in self.configs.projects:
                logger.info(f"- {project.name}")

            logger.info(f"... done, retrieved in {time.time() - tic:.3f}s!")
            return

        if target:
            project = next((p for p in self.configs.projects if p.name == target), None)
            if project:
                logger.info(f"project selected: {project.name}.")
                for task in project.tasks:
                    self.provision(task)

            else:
                logger.warning(f"no project found with name: {target}")
