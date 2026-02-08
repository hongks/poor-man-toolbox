from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from click import Context
from pdf2image import convert_from_path

from . import logger
from .config import Config


class Folders:
    def __init__(self, configs: Config, context: Context):
        self.configs = configs
        self.context = context
        self._dir_size_cache: dict[Path, int] = {}

    def pdf2image(
        self, filename: str, fileformat: str = "png", output_dir: Path | None = None
    ):
        """Convert a PDF into images (png/jpeg)."""
        if fileformat not in {"jpeg", "png"}:
            logger.error(f"Unsupported file format: {fileformat}")
            return

        try:
            pages = convert_from_path(filename)
        except Exception as e:
            logger.error(f"Failed to convert {filename} to images: {e}")
            return

        output_dir = Path(output_dir or Path.cwd())
        output_dir.mkdir(parents=True, exist_ok=True)

        for i, page in enumerate(pages, start=1):
            out_file = output_dir / f"{Path(filename).stem}_{i}.{fileformat}"
            page.save(out_file, fileformat)

        logger.info(
            f"Converted {filename} -> {len(pages)} {fileformat} files in {output_dir}"
        )

    def remove_empty_folder(self, root: Path):
        """Remove empty folders recursively."""
        for p in root.rglob("*"):
            if p.is_dir() and not any(p.iterdir()):
                logger.info(f"Removing empty folder: {p}")
                p.rmdir()

    def run(self, target: str | None = None, list_only: bool = False):
        """Entrypoint for CLI integration."""
        root = Path(target or Path.cwd())
        self.tree(root)

    def _get_dir_size(self, path: Path) -> int:
        if path in self._dir_size_cache:
            return self._dir_size_cache[path]

        total = 0
        try:
            for f in path.rglob("*"):
                if f.is_file() and not f.is_symlink():
                    total += f.stat().st_size
        except (PermissionError, FileNotFoundError):
            pass

        self._dir_size_cache[path] = total
        return total

    def _format_size(self, size: int, unit: str = "KB") -> str:
        if unit == "MB":
            return f"{round(size / (1024 * 1024), 1)} MB"
        return f"{round(size / 1024, 1)} KB"

    def tree(self, directory: Path, prefix: str = ""):
        """Print a tree with sizes, like `tree -h`."""
        try:
            entries = sorted(directory.iterdir())
        except PermissionError:
            logger.warning(f"No permission to read {directory}")
            return

        if not prefix:
            size = self._format_size(self._get_dir_size(directory))
            print(f"d   {size:>8}  {directory.name}")

        entries_count = len(entries)

        for idx, path in enumerate(entries):
            connector = "└─ " if idx == entries_count - 1 else "├─ "
            col1 = "d" if path.is_dir() else " "
            col2 = "l" if path.is_symlink() else " "

            try:
                size = (
                    self._format_size(self._get_dir_size(path))
                    if path.is_dir()
                    else self._format_size(path.stat().st_size)
                )
            except (PermissionError, FileNotFoundError):
                size = "N/A"

            print(f"{col1} {col2} {size:>8}  {prefix}{connector}{path.name}")

            if path.is_dir():
                extension = "    " if idx == entries_count - 1 else "│   "
                self.tree(path, prefix + extension)

    def extract(source):
        file = "test.zip"

        # mkdir "temp"

        with ZipFile(file, "r") as zip:
            for info in zip.infolist():
                if ".gba" in info.filename:
                    zip.extract(info.filename)
                    # move "done/"

    def test(file):
        with ZipFile(file, "r") as zip:
            zip.testzip()

    def compress(source):
        file = "test\\test.zip"

        with ZipFile(file, "w", ZIP_DEFLATED, 9) as zip:
            zip.write("test\\test.gba")
