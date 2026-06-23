import csv
import json
from pathlib import Path

import pytest

from file_organizer import (
    FileClassifier,
    FileOrganizer,
    FileScanner,
    MoveHistory,
    MoveLogger,
    unique_path,
)


class TestUniquePath:
    def test_returns_same_path_when_not_exists(self, tmp_path):
        target = tmp_path / "file.txt"
        assert unique_path(target) == target

    def test_appends_counter_when_path_exists(self, tmp_path):
        target = tmp_path / "file.txt"
        target.write_text("a")
        assert unique_path(target) == tmp_path / "file (1).txt"

    def test_increments_counter_until_free(self, tmp_path):
        (tmp_path / "file.txt").write_text("a")
        (tmp_path / "file (1).txt").write_text("a")
        (tmp_path / "file (2).txt").write_text("a")
        assert unique_path(tmp_path / "file.txt") == tmp_path / "file (3).txt"


class TestFileScanner:
    def test_scan_returns_only_files(self, tmp_path):
        (tmp_path / "a.txt").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        (tmp_path / "subdir").mkdir()
        names = {entry.name for entry in FileScanner(tmp_path).scan()}
        assert names == {"a.txt", "b.txt"}

    def test_scan_empty_folder_returns_empty_list(self, tmp_path):
        assert FileScanner(tmp_path).scan() == []


class TestFileClassifier:
    @pytest.mark.parametrize(
        "filename,expected",
        [
            ("photo.jpg", "Images"),
            ("photo.JPEG", "Images"),
            ("doc.pdf", "Documents"),
            ("sheet.xlsx", "Documents"),
            ("song.mp3", "Audio"),
            ("movie.mp4", "Videos"),
            ("archive.zip", "Archives"),
            ("script.py", "Code"),
        ],
    )
    def test_classify_known_extensions(self, filename, expected):
        assert FileClassifier().classify(Path(filename)) == expected

    def test_classify_unknown_extension_uses_extension_name(self):
        assert FileClassifier().classify(Path("file.rs")) == "rs"

    def test_classify_no_extension_returns_others(self):
        assert FileClassifier().classify(Path("README")) == "Others"


class TestMoveLogger:
    def test_creates_log_file_with_header(self, tmp_path):
        log_file = tmp_path / "log.csv"
        MoveLogger(log_file)
        with log_file.open(newline="") as f:
            rows = list(csv.reader(f))
        assert rows == [["timestamp", "source", "destination", "status"]]

    def test_does_not_overwrite_existing_log(self, tmp_path):
        log_file = tmp_path / "log.csv"
        log_file.write_text("existing content")
        MoveLogger(log_file)
        assert log_file.read_text() == "existing content"

    def test_log_appends_row(self, tmp_path):
        log_file = tmp_path / "log.csv"
        logger = MoveLogger(log_file)
        logger.log("src.txt", "dst.txt", status="moved")
        with log_file.open(newline="") as f:
            rows = list(csv.reader(f))
        assert rows[1][1:] == ["src.txt", "dst.txt", "moved"]

    def test_log_default_status_is_moved(self, tmp_path):
        log_file = tmp_path / "log.csv"
        logger = MoveLogger(log_file)
        logger.log("src.txt", "dst.txt")
        with log_file.open(newline="") as f:
            rows = list(csv.reader(f))
        assert rows[1][-1] == "moved"


class TestMoveHistory:
    def test_loads_empty_when_no_file(self, tmp_path):
        assert MoveHistory(tmp_path / "history.json").records == []

    def test_loads_existing_records(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"source": "a", "destination": "b"}]))
        assert MoveHistory(history_file).records == [{"source": "a", "destination": "b"}]

    def test_add_persists_record(self, tmp_path):
        history_file = tmp_path / "history.json"
        history = MoveHistory(history_file)
        history.add(Path("a.txt"), Path("b.txt"))
        assert json.loads(history_file.read_text()) == [{"source": "a.txt", "destination": "b.txt"}]

    def test_undo_last_with_no_records(self, tmp_path):
        assert MoveHistory(tmp_path / "history.json").undo_last() == "Nothing to undo."

    def test_undo_last_restores_file(self, tmp_path):
        source_dir = tmp_path / "src"
        dest_dir = tmp_path / "dst"
        source_dir.mkdir()
        dest_dir.mkdir()
        moved_file = dest_dir / "a.txt"
        moved_file.write_text("content")

        history = MoveHistory(tmp_path / "history.json")
        history.add(source_dir / "a.txt", moved_file)
        result = history.undo_last()

        assert (source_dir / "a.txt").exists()
        assert not moved_file.exists()
        assert "Restored" in result
        assert history.records == []

    def test_undo_last_renames_on_conflict(self, tmp_path):
        source_dir = tmp_path / "src"
        dest_dir = tmp_path / "dst"
        source_dir.mkdir()
        dest_dir.mkdir()
        (source_dir / "a.txt").write_text("already here")
        moved_file = dest_dir / "a.txt"
        moved_file.write_text("moved content")

        history = MoveHistory(tmp_path / "history.json")
        history.add(source_dir / "a.txt", moved_file)
        history.undo_last()

        assert (source_dir / "a.txt").read_text() == "already here"
        assert (source_dir / "a (1).txt").read_text() == "moved content"

    def test_undo_last_when_moved_file_missing(self, tmp_path):
        history = MoveHistory(tmp_path / "history.json")
        history.add(tmp_path / "a.txt", tmp_path / "gone.txt")
        result = history.undo_last()
        assert "no longer exists" in result
        assert history.records == []

    def test_undo_all_restores_every_record(self, tmp_path):
        dest_dir = tmp_path / "dst"
        dest_dir.mkdir()
        (dest_dir / "a.txt").write_text("a")
        (dest_dir / "b.txt").write_text("b")

        history = MoveHistory(tmp_path / "history.json")
        history.add(tmp_path / "a.txt", dest_dir / "a.txt")
        history.add(tmp_path / "b.txt", dest_dir / "b.txt")
        results = history.undo_all()

        assert len(results) == 2
        assert history.records == []
        assert (tmp_path / "a.txt").exists()
        assert (tmp_path / "b.txt").exists()

    def test_undo_all_with_no_records_returns_empty_list(self, tmp_path):
        assert MoveHistory(tmp_path / "history.json").undo_all() == []

    def test_undo_last_keeps_record_when_move_fails(self, tmp_path, monkeypatch):
        dest_dir = tmp_path / "dst"
        dest_dir.mkdir()
        moved_file = dest_dir / "a.txt"
        moved_file.write_text("a")

        history = MoveHistory(tmp_path / "history.json")
        history.add(tmp_path / "a.txt", moved_file)

        def raise_permission_error(*args, **kwargs):
            raise PermissionError("denied")

        monkeypatch.setattr("file_organizer.shutil.move", raise_permission_error)
        result = history.undo_last()

        assert "Could not undo" in result
        assert history.records == [{"source": str(tmp_path / "a.txt"), "destination": str(moved_file)}]

    def test_undo_logs_when_logger_provided(self, tmp_path):
        dest_dir = tmp_path / "dst"
        dest_dir.mkdir()
        moved = dest_dir / "a.txt"
        moved.write_text("a")

        logger = MoveLogger(tmp_path / "log.csv")
        history = MoveHistory(tmp_path / "history.json", logger=logger)
        history.add(tmp_path / "a.txt", moved)
        history.undo_last()

        with (tmp_path / "log.csv").open(newline="") as f:
            rows = list(csv.reader(f))
        assert rows[-1][-1] == "undone"


class TestFileOrganizer:
    @staticmethod
    def _make_organizer(work_dir, state_dir):
        logger = MoveLogger(state_dir / "log.csv")
        history = MoveHistory(state_dir / "history.json", logger=logger)
        return FileOrganizer(work_dir, logger=logger, history=history)

    @pytest.fixture
    def workspace(self, tmp_path):
        work_dir = tmp_path / "work"
        state_dir = tmp_path / "state"
        work_dir.mkdir()
        state_dir.mkdir()
        return work_dir, state_dir

    def test_organize_moves_files_into_categories(self, workspace):
        work_dir, state_dir = workspace
        (work_dir / "a.jpg").write_text("a")
        (work_dir / "b.pdf").write_text("b")

        moved = self._make_organizer(work_dir, state_dir).organize()

        assert moved == 2
        assert (work_dir / "Images" / "a.jpg").exists()
        assert (work_dir / "Documents" / "b.pdf").exists()

    def test_organize_unknown_extension_gets_own_folder(self, workspace):
        work_dir, state_dir = workspace
        (work_dir / "file.rs").write_text("a")

        self._make_organizer(work_dir, state_dir).organize()

        assert (work_dir / "rs" / "file.rs").exists()

    def test_organize_returns_zero_on_empty_folder(self, workspace):
        work_dir, state_dir = workspace
        assert self._make_organizer(work_dir, state_dir).organize() == 0

    def test_organize_resolves_name_conflicts(self, workspace):
        work_dir, state_dir = workspace
        (work_dir / "Images").mkdir()
        (work_dir / "Images" / "a.jpg").write_text("existing")
        (work_dir / "a.jpg").write_text("new")

        self._make_organizer(work_dir, state_dir).organize()

        assert (work_dir / "Images" / "a.jpg").read_text() == "existing"
        assert (work_dir / "Images" / "a (1).jpg").read_text() == "new"

    def test_organize_calls_on_move_and_on_progress(self, workspace):
        work_dir, state_dir = workspace
        (work_dir / "a.jpg").write_text("a")
        moves, progresses = [], []

        self._make_organizer(work_dir, state_dir).organize(
            on_move=lambda s, d: moves.append((s, d)),
            on_progress=lambda c, t: progresses.append((c, t)),
        )

        assert len(moves) == 1
        assert progresses == [(1, 1)]

    def test_organize_stop_check_halts_before_any_move(self, workspace):
        work_dir, state_dir = workspace
        (work_dir / "a.jpg").write_text("a")
        (work_dir / "b.pdf").write_text("b")

        moved = self._make_organizer(work_dir, state_dir).organize(stop_check=lambda: True)

        assert moved == 0
        assert (work_dir / "a.jpg").exists()
        assert (work_dir / "b.pdf").exists()

    def test_organize_records_history_for_each_move(self, workspace):
        work_dir, state_dir = workspace
        (work_dir / "a.jpg").write_text("a")

        organizer = self._make_organizer(work_dir, state_dir)
        organizer.organize()

        assert len(organizer.history.records) == 1

    def test_organize_running_twice_does_not_remove_files(self, workspace):
        work_dir, state_dir = workspace
        (work_dir / "a.jpg").write_text("a")
        organizer = self._make_organizer(work_dir, state_dir)

        organizer.organize()
        moved_again = organizer.organize()

        assert moved_again == 0
        assert (work_dir / "Images" / "a.jpg").exists()

    def test_organize_handles_permission_error(self, workspace, monkeypatch):
        work_dir, state_dir = workspace
        (work_dir / "a.jpg").write_text("a")

        def raise_permission_error(*args, **kwargs):
            raise PermissionError("denied")

        monkeypatch.setattr("file_organizer.shutil.move", raise_permission_error)
        moved = self._make_organizer(work_dir, state_dir).organize()

        assert moved == 0
        with (state_dir / "log.csv").open(newline="") as f:
            rows = list(csv.reader(f))
        assert "permission denied" in rows[-1][-1]
        assert (work_dir / "a.jpg").exists()

    def test_organize_handles_name_conflict_error(self, workspace, monkeypatch):
        work_dir, state_dir = workspace
        (work_dir / "a.jpg").write_text("a")

        def raise_file_exists_error(*args, **kwargs):
            raise FileExistsError("already there")

        monkeypatch.setattr("file_organizer.shutil.move", raise_file_exists_error)
        moved = self._make_organizer(work_dir, state_dir).organize()

        assert moved == 0
        with (state_dir / "log.csv").open(newline="") as f:
            rows = list(csv.reader(f))
        assert "name conflict" in rows[-1][-1]

    def test_organize_continues_after_a_failed_file(self, workspace, monkeypatch):
        work_dir, state_dir = workspace
        (work_dir / "a.jpg").write_text("a")
        (work_dir / "b.pdf").write_text("b")

        real_move = __import__("shutil").move
        calls = []

        def flaky_move(src, dst):
            calls.append(src)
            if str(src).endswith("a.jpg"):
                raise OSError("disk full")
            return real_move(src, dst)

        monkeypatch.setattr("file_organizer.shutil.move", flaky_move)
        moved = self._make_organizer(work_dir, state_dir).organize()

        assert moved == 1
        assert (work_dir / "Documents" / "b.pdf").exists()
