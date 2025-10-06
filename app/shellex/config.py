import hashlib

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from . import logger


@dataclass
class Config:
    @dataclass
    class Project:
        name: str
        workdir: str | None = None
        tasks: list["Config.Task"] = field(default_factory=list)

    @dataclass
    class Task:
        action: str
        silent: bool = True
        timeout: int = 60
        workdir: str | None = None

    # defaults
    filename: str = "./run/shellex.yml"
    silent: bool = True
    timeout: int = 60

    projects: list[Project] = field(default_factory=list)

    # override default configs
    def load(self) -> str | None:
        sha256 = hashlib.sha256()
        file = Path(self.filename)

        try:
            data = file.read_bytes()
            sha256.update(data)
            configs: dict[str, Any] = yaml.safe_load(data.decode()) or {}

            settings = configs.get("settings", {}) or {}
            self.silent = settings.get("silent", self.silent)
            self.timeout = settings.get("timeout", self.timeout)

            # parse projects (with nested tasks)
            self.projects = []
            for project in configs.get("projects", []):
                workdir = project.get("workdir", None)

                tasks = []
                for t in project.get("tasks", []):
                    merged = {
                        "silent": self.silent,
                        "timeout": self.timeout,
                        "workdir": workdir,
                        **t,
                    }
                    tasks.append(self.Task(**merged))

                self.projects.append(
                    self.Project(name=project["name"], workdir=workdir, tasks=tasks)
                )

            return sha256.hexdigest()

        except FileNotFoundError:
            logger.error(f"config file {self.filename} not found, using defaults.")

        except yaml.YAMLError as err:
            logger.error(f"error parsing yml file: {err}")

        except Exception as err:
            logger.exception(f"unexpected {err=}, {type(err)=}")

        return None
