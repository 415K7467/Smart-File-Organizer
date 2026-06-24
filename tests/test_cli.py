import pytest

from cli import ConsoleMenu


@pytest.fixture
def menu(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return ConsoleMenu()


class TestConsoleMenu:
    def test_organize_folder_rejects_missing_path(self, menu, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda *_: "/no/such/folder")
        menu.organize_folder()
        assert "does not exist" in capsys.readouterr().out

    def test_organize_folder_moves_files(self, menu, monkeypatch, tmp_path, capsys):
        folder = tmp_path / "data"
        folder.mkdir()
        (folder / "a.txt").write_text("a")
        monkeypatch.setattr("builtins.input", lambda *_: str(folder))

        menu.organize_folder()

        out = capsys.readouterr().out
        assert "Moved 1 file(s)" in out
        assert (folder / "Documents" / "a.txt").exists()

    def test_undo_last_with_no_history(self, menu, capsys):
        menu.undo_last()
        assert "Nothing to undo." in capsys.readouterr().out

    def test_undo_all_with_no_history(self, menu, capsys):
        menu.undo_all()
        assert "Undone 0 move(s)." in capsys.readouterr().out

    def test_exit_app_returns_false_and_prints_goodbye(self, menu, capsys):
        assert menu.exit_app() is False
        assert "Goodbye!" in capsys.readouterr().out

    def test_run_handles_invalid_option_then_exits(self, menu, monkeypatch, capsys):
        inputs = iter(["bogus", "4"])
        monkeypatch.setattr("builtins.input", lambda *_: next(inputs))

        menu.run()

        out = capsys.readouterr().out
        assert "Invalid option" in out
        assert "Goodbye!" in out

    def test_run_organizes_then_exits(self, menu, monkeypatch, tmp_path, capsys):
        folder = tmp_path / "data"
        folder.mkdir()
        (folder / "a.jpg").write_text("a")
        inputs = iter(["1", str(folder), "4"])
        monkeypatch.setattr("builtins.input", lambda *_: next(inputs))

        menu.run()

        assert (folder / "Images" / "a.jpg").exists()
        assert "Goodbye!" in capsys.readouterr().out
