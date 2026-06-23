import threading

import pytest

tk = pytest.importorskip("tkinter")

from gui import OrganizerGUI


class ImmediateThread:
    """Stand-in for threading.Thread that runs the target synchronously."""

    def __init__(self, target, args=(), daemon=None):
        self._target = target
        self._args = args

    def start(self):
        self._target(*self._args)


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"no display available for Tk: {error}")
    window.withdraw()
    yield window
    window.destroy()


@pytest.fixture
def gui(root, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(threading, "Thread", ImmediateThread)
    return OrganizerGUI(root)


class TestOrganizerGUI:
    def test_select_folder_sets_path_when_chosen(self, gui, monkeypatch, tmp_path):
        monkeypatch.setattr("gui.filedialog.askdirectory", lambda: str(tmp_path))
        gui.select_folder()
        assert gui.folder_path.get() == str(tmp_path)

    def test_select_folder_noop_when_cancelled(self, gui, monkeypatch):
        monkeypatch.setattr("gui.filedialog.askdirectory", lambda: "")
        gui.start()
        gui.select_folder()
        assert gui.folder_path.get() == ""

    def test_start_warns_when_no_folder(self, gui, monkeypatch):
        warnings = []
        monkeypatch.setattr("gui.messagebox.showwarning", lambda title, message: warnings.append(message))

        gui.start()

        assert warnings
        assert str(gui.start_button["state"]) == "normal"

    def test_start_organizes_folder_and_reports_completion(self, gui, tmp_path):
        folder = tmp_path / "data"
        folder.mkdir()
        (folder / "a.jpg").write_text("a")
        gui.folder_path.set(str(folder))

        gui.start()
        gui.root.update()

        assert (folder / "Images" / "a.jpg").exists()
        assert "Done. Moved 1 file(s)." in gui.status_text.get()
        assert str(gui.start_button["state"]) == "normal"
        assert str(gui.stop_button["state"]) == "disabled"
        assert gui.log_box.get(0, tk.END) == ("a.jpg -> Images/a.jpg",)

    def test_start_reports_error_from_organize(self, gui, monkeypatch, tmp_path):
        folder = tmp_path / "data"
        folder.mkdir()
        gui.folder_path.set(str(folder))
        monkeypatch.setattr(
            "gui.FileOrganizer.organize",
            lambda self, stop_check=None, on_move=None, on_progress=None: (_ for _ in ()).throw(OSError("boom")),
        )

        gui.start()
        gui.root.update()

        assert "Error: boom" in gui.status_text.get()

    def test_stop_sets_flag_and_status(self, gui):
        gui.stop()
        assert gui._stop_requested is True
        assert gui.status_text.get() == "Stopping..."

    def test_undo_last_with_no_history(self, gui):
        gui.undo_last()
        assert gui.status_text.get() == "Nothing to undo."

    def test_undo_all_with_no_history(self, gui):
        gui.undo_all()
        assert gui.status_text.get() == "Undone 0 move(s)."

    def test_undo_last_restores_moved_file(self, gui, tmp_path):
        folder = tmp_path / "data"
        folder.mkdir()
        (folder / "a.jpg").write_text("a")
        gui.folder_path.set(str(folder))

        gui.start()
        gui.root.update()
        gui.undo_last()

        assert (folder / "a.jpg").exists()
        assert "Restored a.jpg" in gui.status_text.get()
