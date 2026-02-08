import hashlib

from datetime import datetime
from pathlib import Path

import yaml

from .sqlite import Setting


class Base:
    def __str__(self):
        return str([{i: f"{self.__dict__[i]}"} for i in self.__dict__])


# default configs, overide as needed
class Config(Base):
    class Logging(Base):
        def __init__(self):
            self.filename = "poor-man-search.log"
            self.format = "%(asctime)s | %(levelname)s in %(module)s: %(message)s"
            self.level = "INFO"

    def __init__(self):
        self.filename = "config.yml"
        self.secret_key = "the-quick-brown-fox-jumps-over-the-lazy-dog!"
        self.sqlite_uri = "sqlite:///cache.sqlite"

        self.logging = self.Logging()

    # override default configs
    def load(self):
        if not Path(self.filename).exists():
            return None

        sha256 = hashlib.sha256()
        with open(self.filename, "rb") as f:
            while True:
                chunk = f.read(1000000)  # 1MB
                if not chunk:
                    break
                sha256.update(chunk)

        with open(self.filename, "r") as f:
            configs = yaml.load(f, Loader=yaml.loader.SafeLoader)

            self.logging.level = configs["logging"]["level"].upper()

        return sha256.hexdigest()

    # in case config file is different
    def sync(self, session):
        row = session.query(Setting).filter_by(key="config-sha256").first()
        dt = datetime.utcnow()

        sha256 = self.load()
        if row and sha256:
            if sha256 != row.value:
                row.value = sha256
                row.updated_on = dt

        else:
            row = Setting(
                key="config-sha256",
                value=sha256,
                created_on=dt,
                updated_on=dt,
            )
            session.add(row)

        session.commit()
