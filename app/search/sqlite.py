from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker


Base = declarative_base()


class FileAttribute(Base):
    __tablename__ = "file_attributes"
    id = Column(Integer, primary_key=True)

    sha256 = Column(Text)
    path = Column(Text)
    name = Column(Text)
    suffixes = Column(Text)
    size = Column(Integer)
    atime = Column(DateTime)  # file last access
    mtime = Column(DateTime)  # file last modified
    ctime = Column(DateTime)  # file created on

    is_file = Column(Boolean)  # false for non-file types
    is_text = Column(Boolean)  # true for text file
    encoding = Column(Text)

    owner_id = Column(Integer, ForeignKey("owners.id"))
    group_id = Column(Integer, ForeignKey("groups.id"))

    created_on = Column(DateTime, default=datetime.now(tz=timezone.utc))
    updated_on = Column(DateTime, default=datetime.now(tz=timezone.utc))


class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)

    name = Column(Text)
    description = Column(Text)

    created_on = Column(DateTime, default=datetime.now(tz=timezone.utc))
    updated_on = Column(DateTime, default=datetime.now(tz=timezone.utc))


class Owner(Base):
    __tablename__ = "owners"
    id = Column(Integer, primary_key=True)

    name = Column(Text)
    description = Column(Text)

    created_on = Column(DateTime, default=datetime.now(tz=timezone.utc))
    updated_on = Column(DateTime, default=datetime.now(tz=timezone.utc))


class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)

    key = Column(Text)
    value = Column(Text)

    created_on = Column(DateTime, default=datetime.now(tz=timezone.utc))
    updated_on = Column(DateTime, default=datetime.now(tz=timezone.utc))


class SQLite:
    def __init__(self, uri):
        engine = create_engine(uri)
        Base.metadata.create_all(engine)

        Session = sessionmaker(bind=engine)
        self.session = Session()

    def update(self, key, value):
        row = self.session.query(Setting).filter_by(key=key).first()
        dt = datetime.now(tz=timezone.utc)

        if row:
            row.value = value
            row.updated_on = dt

        else:
            row = Setting(
                key=key,
                value=value,
                created_on=dt,
                updated_on=dt,
            )
            self.session.add(row)

        self.session.commit()
