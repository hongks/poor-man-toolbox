import hashlib
import logging

from asyncio import DefaultEventLoopPolicy, SelectorEventLoop
from dataclasses import dataclass, field, fields, replace
from datetime import datetime, timezone
from pathlib import Path
from selectors import SelectSelector
from typing import Any, TypeVar

import yaml

from .sqlite import Setting


T = TypeVar("T")


class ConfigSelectorPolicy(DefaultEventLoopPolicy):
    def new_event_loop(self):
        selector = SelectSelector()
        return SelectorEventLoop(selector)


# default configs, override as needed
@dataclass
class Config:
    @dataclass
    class Logging:
        level: str = "INFO"
        retention: int = 7

        filename: str = "./run/poor-man-toolbox.log"
        format: str = "%(asctime)s  %(levelname)-7s  %(name)s.%(module)s:  %(message)s"

        def __post_init__(self):
            self.level = str(self.level).upper()

    @dataclass
    class SQLite:
        echo: bool = False
        track_modifications: bool = False
        uri: str = "sqlite:///./run/cache.sqlite"

    filename: str = "./run/config.yml"
    filepath: Path = Path(".").resolve()
    secret_key: str = "the-quick-brown-fox-jumps-over-the-lazy-dog!"
    template: str = "./app/templates/config.yml"
    version: str = "0.5.5"

    logging: Logging = field(default_factory=Logging)
    sqlite: SQLite = field(default_factory=SQLite)

    # override default configs
    def load(self) -> str | None:
        sha256 = hashlib.sha256()
        file = Path(self.filename)

        try:
            data = file.read_bytes()
            sha256.update(data)
            configs: dict[str, Any] = yaml.safe_load(data.decode()) or {}

            dataclass_map = {
                "logging": self.logging,
            }

            for key, cls in dataclass_map.items():
                cfg = configs.get(key, {})
                setattr(self, key, self.parse(cls, cfg))

        except FileNotFoundError:
            logging.error(f"config file {self.filename} not found, using defaults.")
            return None

        except yaml.YAMLError as err:
            logging.error(f"error parsing yml file: {err}")
            return None

        except Exception as err:
            logging.exception(f"unexpected {err=}, {type(err)=}")
            return None

        return sha256.hexdigest()

    # helpers
    def parse(self, instance: T, cfg: dict) -> T:
        updates = {
            f.name: cfg[f.name]
            for f in fields(instance)
            if f.name in cfg and cfg[f.name] is not None
        }
        return replace(instance, **updates)

    # in case config file is different
    def sync(self, session) -> datetime | None:
        sha256 = self.load()
        if not sha256:
            return None

        row = session.query(Setting).filter_by(key="config-sha256").first()
        if row and sha256 == row.value:
            return None  # no changes detected

        now = datetime.now(tz=timezone.utc)
        if not row:
            row = Setting(key="config-sha256", created_on=now)
            session.add(row)

        row.value = sha256
        row.updated_on = now

        session.commit()
        return now
