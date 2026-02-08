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
        path: str

    @dataclass
    class Target:
        hostname: str
        port: int
        username: str
        password: str
        projects: list["Config.Project"] = field(default_factory=list)

    # defaults
    filename: str = "./run/filesync.yml"

    excludes: list[str] = field(
        default_factory=lambda: ["__pycache__", r"\.(git|log|flake8|gitignore)$"]
    )
    projects: list[Project] = field(default_factory=list)
    targets: list[Target] = field(default_factory=list)

    # override default configs
    def load(self) -> str | None:
        sha256 = hashlib.sha256()
        file = Path(self.filename)

        try:
            data = file.read_bytes()
            sha256.update(data)
            configs: dict[str, Any] = yaml.safe_load(data.decode()) or {}

            settings = configs.get("settings", [])
            self.excludes = settings.get("excludes", self.excludes)

            # parse projects
            self.projects = [
                self.Project(**proj) for proj in configs.get("projects", [])
            ]

            # parse targets (with nested projects)
            self.targets = []
            for tgt in configs.get("targets", []):
                projects = [self.Project(**p) for p in tgt.get("projects", [])]
                self.targets.append(
                    self.Target(
                        hostname=tgt["hostname"],
                        port=tgt["port"],
                        username=tgt["username"],
                        password=tgt["password"],
                        projects=projects,
                    )
                )

            return sha256.hexdigest()

        except FileNotFoundError:
            logger.error(f"config file {self.filename} not found, using defaults.")

        except yaml.YAMLError as err:
            logger.error(f"error parsing yml file: {err}")

        except Exception as err:
            logger.exception(f"unexpected {err=}, {type(err)=}")

        return None
