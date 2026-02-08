import hashlib
import logging
import platform

from datetime import datetime
from grp import getgrgid
from pathlib import Path
from pwd import getpwuid

from .sqlite import FileAttribute, Group, Owner


class Crawler:
    def __init__(self, session):
        self.session = session
        self.path = None

    def get_sha256(self, file):
        sha256 = hashlib.sha256()

        with open(file, "rb") as f:
            while True:
                chunk = f.read(1000000)  # 1MB
                if not chunk:
                    break

                sha256.update(chunk)

        return sha256.hexdigest()

    def get_or_set_user_group(self, uid, gid):
        owner_name = None
        group_name = None

        if platform.system().lower() == "linux":
            owner_name = getpwuid(uid).pw_name
            group_name = getgrgid(gid).gr_name

        elif platform.system().lower() == "windows":
            # TODO: to include windows api call
            # sd = win32security.GetFileSecurity (FILENAME, \
            #   win32security.OWNER_SECURITY_INFORMATION)
            # owner_sid = sd.GetSecurityDescriptorOwner ()
            # name, domain, type = win32security.LookupAccountSid (None, owner_sid)
            # print "File owned by %s\\%s" % (domain, name)
            pass

        else:
            logging.error("unsupported operating system!")

        if owner_name:
            owner = self.session.query(Owner).filter_by(name=owner_name).first()

            if not owner:
                dt = datetime.utcnow()
                owner = Owner(name=owner_name, created_on=dt, updated_on=dt)
                self.session.add(owner)
                self.session.commit()

        if group_name:
            group = self.session.query(Group).filter_by(name=group_name).first()

            if not group:
                dt = datetime.utcnow()
                group = Group(name=group_name, created_on=dt, updated_on=dt)
                self.session.add(group)
                self.session.commit()

        return owner.id if owner else None, group.id if group else None

    def recursive(self, path):
        for p in Path(path).iterdir():
            if p.is_dir():
                self.recursive(p)

            else:
                self.update(p)
                logging.info(f"+ {str(p).replace(self.path, '')}")

    def run(self, path):
        self.path = path
        logging.info(f"working on {path}/")

        self.recursive(path)

    def update(self, file):
        dt = datetime.utcnow()
        sha256 = self.get_sha256(file)
        user_id, group_id = self.get_or_set_user_group(
            file.stat().st_uid, file.stat().st_gid
        )

        row = (
            self.session.query(FileAttribute)
            .filter_by(path=str(file.parent), name=file.name)
            .first()
        )

        if row:
            row.sha256 = sha256
            row.path = str(file.parent)
            row.name = file.name
            row.suffixes = ", ".join(file.suffixes)
            row.size = file.stat().st_size
            row.atime = datetime.fromtimestamp(file.stat().st_atime)
            row.mtime = datetime.fromtimestamp(file.stat().st_mtime)
            row.ctime = datetime.fromtimestamp(file.stat().st_ctime)
            row.is_file = file.is_file()
            row.is_text = None
            row.encoding = None
            row.owner_id = user_id
            row.group_id = group_id
            row.updated_on = dt

        else:
            row = FileAttribute(
                sha256=sha256,
                path=str(file.parent),
                name=file.name,
                suffixes=", ".join(file.suffixes),
                size=file.stat().st_size,
                atime=datetime.fromtimestamp(file.stat().st_atime),
                mtime=datetime.fromtimestamp(file.stat().st_mtime),
                ctime=datetime.fromtimestamp(file.stat().st_ctime),
                is_file=file.is_file(),
                is_text=None,
                encoding=None,
                owner_id=user_id,
                group_id=group_id,
                created_on=dt,
                updated_on=dt,
            )

            self.session.add(row)

        self.session.commit()
