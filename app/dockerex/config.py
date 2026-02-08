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
        tasks: list["Config.Task"] = field(default_factory=list)

    @dataclass
    class Task:
        name: str
        actions: list[str]
        containers: list[str] | None = None
        volumes: list[str] | None = None

    # defaults
    filename: str = "./run/dockerex.yml"

    projects: list[Project] = field(default_factory=list)

    # override default configs
    def load(self) -> str | None:
        sha256 = hashlib.sha256()
        file = Path(self.filename)

        try:
            data = file.read_bytes()
            sha256.update(data)
            configs: dict[str, Any] = yaml.safe_load(data.decode()) or {}

            # parse projects (with nested tasks)
            self.projects = []
            for project in configs.get("projects", []):
                tasks = []
                for t in project.get("tasks", []):
                    tasks.append(self.Task(**t))

                self.projects.append(self.Project(name=project["name"], tasks=tasks))

            return sha256.hexdigest()

        except FileNotFoundError:
            logger.error(f"config file {self.filename} not found, using defaults.")

        except yaml.YAMLError as err:
            logger.error(f"error parsing yml file: {err}")

        except Exception as err:
            logger.exception(f"unexpected {err=}, {type(err)=}")

        return None
