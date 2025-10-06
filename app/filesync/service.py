import filecmp
import re
import shutil
import time

from datetime import datetime
from os import getcwd, utime
from pathlib import Path
from stat import S_ISDIR

from click import Context
from paramiko import AuthenticationException, AutoAddPolicy, SFTPClient, SSHClient

from . import logger
from .config import Config


class FileSync:
    def __init__(self, configs: Config, context: Context):
        self.configs = configs
        self.context = context
        self.patterns = [re.compile(ele) for ele in self.configs.excludes]

    def check(self, target: str) -> bool:
        found = False

        for host in self.configs.targets:
            if target and target != host.hostname:
                continue

            found = True
            for project in host.projects:
                tic = time.time()

                project_path = next(
                    (p.path for p in self.configs.projects if project.name == p.name),
                    None,
                )

                if not project_path:
                    continue

                logger.info(f"comparing {host.hostname}'s {project.name} ...")
                uri = Path("run") / host.hostname / project.name

                logger.debug(f"remote: ./{uri}")
                logger.debug(f"local: {project_path}")

                self.compare(project_path, uri)
                self.compare(uri, project_path)
                logger.info(f"... done in {time.time() - tic:.3f}s!")

        return found

    def compare(self, path: str, uri: str):
        filecmp.clear_cache()

        base_path = Path(path).resolve()
        if not base_path.exists():
            logger.warning(f"path not found: {base_path}")
            return

        for file in base_path.rglob("*"):
            if file.is_dir():
                continue

            if any(pat.search(part) for part in file.parts for pat in self.patterns):
                # logger.debug(f"skipping {file}")
                continue

            relative_path = file.relative_to(base_path)
            counterpart = Path(uri) / relative_path

            result = counterpart.exists() and filecmp.cmp(
                file, counterpart, shallow=False
            )
            if not result:
                fn = str(file).replace(getcwd(), ".")
                logger.info(f"compared: {result!s:^5}, {fn}")

    def download(self, target: str) -> bool:
        found = False

        for host in self.configs.targets:
            if target and target != host.hostname:
                continue

            found = True
            try:
                with SSHClient() as ssh:
                    ssh.set_missing_host_key_policy(AutoAddPolicy())
                    ssh.connect(
                        host.hostname,
                        port=host.port,
                        username=host.username,
                        password=host.password,
                    )
                    logger.info(
                        f"connected to {host.username}@{host.hostname}:{host.port}!"
                    )

                    with ssh.open_sftp() as sftp:
                        for project in host.projects:
                            tic = time.time()

                            if not any(
                                p.name == project.name for p in self.configs.projects
                            ):
                                continue

                            logger.info(f"copying {project.name} ...")
                            local_path = Path(
                                f"{Path('./run')}/{host.hostname}/{project.name}/"
                            )
                            if local_path.exists():
                                shutil.rmtree(local_path)

                            local_path.mkdir(parents=True, exist_ok=True)

                            counts = self.walk(sftp, local_path, project.path)
                            logger.info(
                                f"... {counts} files copied in {time.time() - tic:.3f}s!"
                            )

            except AuthenticationException:
                logger.error(f"target selected: {target}, authentication failed!")
                return found

            except Exception as err:
                logger.exception(f"unexpected {err=}, {type(err)=}")

        return found

    def generate(self):
        file = Path(self.configs.filename)
        if file.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file.rename(f"./run/filesync_{timestamp}.yml")
            logger.info(f"existing config file renamed to filesync_{timestamp}.yml")

        Path("./run").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.configs.template, self.configs.filename)
        logger.info("skeleton config file generated!")
        return

    def reset(self):
        logger.info("resetting, removing caches and logs ...")
        tic = time.time()

        Path("./run").mkdir(parents=True, exist_ok=True)
        for target in self.configs.targets:
            folder = Path(f"./run/{target.hostname}")
            if folder.exists():
                shutil.rmtree(folder)
                logger.info(f"- deleted: {folder}/*")

        logger.info(f"... done, reset in {time.time() - tic:.3f}s!")

    def run(
        self,
        download: bool,
        check: bool,
        target: str,
        list: bool,
        generate: bool,
        reset: bool,
    ):
        if reset:
            self.reset()
            return

        if generate:
            self.generate()
            return

        if list:
            logger.info("retrieving available targets ...")
            tic = time.time()

            for host in self.configs.targets:
                logger.info(f"- {host.hostname}")

            logger.info(f"... done, retrieved in {time.time() - tic:.3f}s!")
            return

        if target:
            logger.info(f"target selected: {target}.")

        found = False
        action = (download, check)

        if not any(action):
            download = check = True

        if download:
            result = self.download(target)
            found = found or result

        if check:
            result = self.check(target)
            found = found or result

        if not found:
            logger.info("nothing found!")

    def walk(
        self, sftp: SFTPClient, local_path: str, remote_path: str, counts: int = 0
    ):
        try:
            items = sftp.listdir_attr(remote_path)

        except FileNotFoundError:
            logger.error(f"remote path not found: {remote_path}")
            return counts

        local_path = Path(local_path)
        local_path.mkdir(parents=True, exist_ok=True)

        for item in items:
            local_file = local_path / item.filename
            remote_file = f"{remote_path.rstrip('/')}/{item.filename}"

            if any(
                pat.search(part)
                for part in remote_file.split("/")
                for pat in self.patterns
            ):
                logger.debug(f"skipping {item.filename}")
                continue

            if S_ISDIR(item.st_mode):  # directory
                counts = self.walk(sftp, local_file, remote_file, counts=counts)

            else:
                try:
                    sftp.get(remote_file, str(local_file))
                    utime(local_file, (item.st_mtime, item.st_mtime))

                    counts += 1
                    logger.debug(f"copied {remote_file}")

                except (OSError, IOError) as e:
                    logger.error(f"failed to copy {remote_file}: {e}")

        return counts
