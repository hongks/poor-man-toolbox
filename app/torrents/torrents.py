"""torrents.py, mostly routines related to qBittorrent."""

import pathlib
import shutil

from collections import Counter
from send2trash import send2trash


def getlist(source):
    """Get a list of unique files."""

    path = pathlib.Path(source)
    uniques = {}
    duplicates = Counter()

    for file in path.rglob("*.*"):
        if not file.is_file():
            continue
        if file.name in uniques:
            print(" ! Found duplicate file: {}".format(file.name))
            duplicates.update([file.name])
            del uniques[file]
        else:
            uniques[file.name] = file

    return uniques


def orphans():
    """Get qBittorrent's orphan torrents."""

    # rename backup folder to orphan
    shutil.move("/mnt/Seagate/Torrents/Backup/", "/mnt/Seagate/Torrents/Orphan/")

    # get torrents from orphan folder
    path = pathlib.Path("/mnt/Seagate/Torrents/Orphan/")
    torrents = Counter()
    for item in path.glob("*"):
        stem = item.stem
        torrents[stem] = "{}".format(item)

    # get completed folders / files from completed folder
    path = pathlib.Path("/mnt/Seagate/Torrents/Completed/")
    completed = Counter()
    for item in path.glob("*"):
        completed[item.name] = "{}".format(item)

    # move non orphan torrents back to backup folder
    path = pathlib.Path("/mnt/Seagate/Torrents/Backup/")
    if not path.exists():
        path.mkdir()

    for key, value in torrents.items():
        if key in completed.keys():
            shutil.move(value, path)


def rebuild(source, target):
    """Rebuild qBittorrent's downloading location."""

    # build target list first
    target_uniques = getlist(target)

    # build source list
    source_uniques = getlist(source)

    # building in-progress...
    for file, path in source_uniques.items():
        found = False
        if file in target_uniques.keys():
            if target_uniques[file].stat().st_size == 0:
                found = True
                print(" ! Zero size file found: {}".format(file))
            elif (
                target_uniques[file].stat().st_size
                < source_uniques[file].stat().st_size
            ):
                found = True
                print(" ! Smaller file found: {}".format(file))

            if found:
                send2trash(str(target_uniques[file]))
                shutil.move(str(path), str(target_uniques[file]))
                del target_uniques[file]
