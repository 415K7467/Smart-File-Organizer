import csv
import json
import shutil
from datetime import datetime
from pathlib import Path


def unique_path(path: Path) -> Path:
    """Returns `path`, or a variant with a `(n)` suffix if `path` already exists."""
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    counter = 1
    candidate = parent / f"{stem} ({counter}){suffix}"
    while candidate.exists():
        counter += 1
        candidate = parent / f"{stem} ({counter}){suffix}"
    return candidate


class FileScanner:
    """Scans a folder and returns the files it contains."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)

    def scan(self) -> list[Path]:
        return [entry for entry in self.folder.iterdir() if entry.is_file()]


class FileClassifier:
    """Maps a file's extension to a category name."""

    CATEGORIES = {
        ".jpg": "Images", ".jpeg": "Images", ".png": "Images", ".gif": "Images", ".bmp": "Images",
        ".pdf": "Documents", ".doc": "Documents", ".docx": "Documents", ".txt": "Documents", ".xlsx": "Documents",
        ".mp3": "Audio", ".wav": "Audio", ".flac": "Audio",
        ".mp4": "Videos", ".mkv": "Videos", ".avi": "Videos", ".mov": "Videos",
        ".zip": "Archives", ".rar": "Archives", ".7z": "Archives", ".tar": "Archives",
        ".py": "Code", ".js": "Code", ".java": "Code", ".cpp": "Code", ".c": "Code",
    }

    def classify(self, file: Path) -> str:
        """Returns the known category for the file's extension, or the extension
        itself (e.g. ".rs" -> "rs") when it isn't one of the known categories."""
        extension = file.suffix.lower()
        if not extension:
            return "Others"
        return self.CATEGORIES.get(extension, extension.lstrip("."))


class MoveLogger:
    """Logs every moved file (source, destination, time) to a CSV file."""

    def __init__(self, log_file="organizer_log.csv"):
        self.log_file = Path(log_file)
        if not self.log_file.exists():
            with self.log_file.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(["timestamp", "source", "destination", "status"])

    def log(self, source, destination, status="moved"):
        with self.log_file.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([datetime.now().isoformat(timespec="seconds"), source, destination, status])


class MoveHistory:
    """Keeps a persistent record of moved files so they can be undone later."""

    def __init__(self, history_file="move_history.json", logger: MoveLogger = None):
        self.history_file = Path(history_file)
        self.logger = logger
        self.records = self._load()

    def _load(self):
        if self.history_file.exists():
            with self.history_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save(self):
        with self.history_file.open("w", encoding="utf-8") as f:
            json.dump(self.records, f, indent=2)

    def add(self, source: Path, destination: Path):
        self.records.append({"source": str(source), "destination": str(destination)})
        self._save()

    def undo_last(self) -> str:
        if not self.records:
            return "Nothing to undo."
        record = self.records.pop()
        moved_file = Path(record["destination"])
        restore_to = unique_path(Path(record["source"]))
        try:
            if not moved_file.exists():
                return f"Cannot undo: {moved_file} no longer exists."
            restore_to.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(moved_file), str(restore_to))
        except (PermissionError, OSError) as error:
            self.records.append(record)
            return f"Could not undo {moved_file.name}: {error}"
        finally:
            self._save()
        if self.logger:
            self.logger.log(moved_file, restore_to, status="undone")
        return f"Restored {moved_file.name} -> {restore_to}"

    def undo_all(self) -> list[str]:
        results = []
        while self.records:
            results.append(self.undo_last())
        return results


class FileOrganizer:
    """Organizes the files of a folder into category subfolders."""

    def __init__(self, folder: Path, logger: MoveLogger = None, history: MoveHistory = None):
        self.folder = Path(folder)
        self.scanner = FileScanner(self.folder)
        self.classifier = FileClassifier()
        self.logger = logger or MoveLogger()
        self.history = history or MoveHistory(logger=self.logger)

    def _create_destination_folder(self, category: str) -> Path:
        """Creates (if needed) and returns the category subfolder files of that category move into."""
        destination_folder = self.folder / category
        destination_folder.mkdir(exist_ok=True)
        return destination_folder

    def _move_file(self, file: Path, destination_folder: Path) -> Path:
        """Moves `file` into `destination_folder` using shutil.move() and returns its new path."""
        # unique_path() already avoids known conflicts, but another process could still create
        # a same-named file between this check and the move, so shutil.move() can still raise
        # FileExistsError (Windows) - organize() catches it as a name conflict.
        destination = unique_path(destination_folder / file.name)
        shutil.move(str(file), str(destination))
        return destination

    def organize(self, stop_check=None, on_move=None, on_progress=None) -> int:
        moved = 0
        files = self.scanner.scan()
        total = len(files)
        for index, file in enumerate(files, start=1):
            if stop_check and stop_check():
                break
            category = self.classifier.classify(file)
            try:
                destination_folder = self._create_destination_folder(category)
                destination = self._move_file(file, destination_folder)
            except (FileExistsError, PermissionError, OSError) as error:
                if isinstance(error, FileExistsError):
                    status = f"error: name conflict - {error}"
                elif isinstance(error, PermissionError):
                    status = f"error: permission denied - {error}"
                else:
                    status = f"error: {error}"
                self.logger.log(file, self.folder / category, status=status)
                if on_progress:
                    on_progress(index, total)
                continue
            self.logger.log(file, destination, status="moved")
            self.history.add(file, destination)
            moved += 1
            if on_move:
                on_move(file, destination)
            if on_progress:
                on_progress(index, total)
        return moved


if __name__ == "__main__":
    print("Run 'python cli.py' for the console menu or 'python gui.py' for the graphical interface.")
