import hashlib

from datetime import datetime, timezone
from pathlib import Path

import yaml

from .sqlite import Setting


# base class
class Base:
    def __str__(self):
        return str(self.__dict__)


# default configs, overide as needed
class Config(Base):
    class Logging(Base):
        def __init__(self):
            self.level = "INFO"
            self.retention = 7

            self.filename = "./run/poor-man-filesync.log"
            self.format = "%(asctime)s | %(levelname)s in %(module)s: %(message)s"

    class SQLite(Base):
        def __init__(self):
            self.echo = False
            self.track_modifications = False
            self.uri = "sqlite:///./run/cache.sqlite"

    def __init__(self):
        self.filename = "./run/config.yml"
        self.filepath = Path(".").resolve()
        self.secret_key = "the-quick-brown-fox-jumps-over-the-lazy-dog!"
        self.template = "./app/templates/config.yml"
        self.version = "0.3.0"

        self.logging = self.Logging()
        self.sqlite = self.SQLite()

        # miscellaneous
        self.excludes = ["__pycache__", r"\.(git|log|flake8|gitignore)$"]
        self.projects = None
        self.targets = None

    # override default configs
    def load(self):
        file = Path(self.filename)

        if not file.exists():
            print(f"config file {self.filename} not found, using defaults.")
            return None

        sha256 = hashlib.sha256()
        with file.open("rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)

        try:
            with file.open("r") as f:
                configs = yaml.safe_load(f)

                # logging
                self.logging.level = configs["logging"]["level"].upper()
                self.logging.retention = int(configs["logging"]["retention"])

                # miscellaneous
                self.excludes = configs["settings"]["excludes"]
                self.projects = configs["projects"]
                self.targets = configs["targets"]

        except yaml.YAMLError as err:
            print(f"error parsing yml file: {err}")
            return None

        except Exception as err:
            print(f"unexpected {err=}, {type(err)=}")
            return None

        return sha256.hexdigest()

    # in case config file is different
    def sync(self, session):
        sha256 = self.load()
        if not sha256:
            return None

        row = session.query(Setting).filter_by(key="config-sha256").first()
        dt = datetime.now(tz=timezone.utc)

        if row and sha256 == row.value:
            return None  # no changes detected

        if not row:
            row = Setting(key="config-sha256", created_on=dt)
            session.add(row)

        row.value = sha256
        row.updated_on = dt

        session.commit()
        return dt
