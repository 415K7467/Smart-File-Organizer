import sys
import threading

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:
    sys.exit(
        "tkinter is required for the GUI but is not installed.\n"
        "Windows/macOS: reinstall Python from python.org (Tcl/Tk is included by default).\n"
        "Linux (Debian/Ubuntu): sudo apt install python3-tk\n"
        "Linux (Fedora/RHEL): sudo dnf install python3-tkinter"
    )

from file_organizer import FileOrganizer, MoveHistory, MoveLogger


class OrganizerGUI:
    """Tkinter GUI: select a folder, watch live progress, start/stop/undo."""

    def __init__(self, root):
        self.root = root
        self.root.title("Smart File Organizer")
        self.root.minsize(440, 360)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        self.folder_path = tk.StringVar()
        self.status_text = tk.StringVar(value="Select a folder to begin.")
        self.logger = MoveLogger()
        self.history = MoveHistory(logger=self.logger)
        self._stop_requested = False

        self._build_widgets()

    def _build_widgets(self):
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(4, weight=1)

        folder_row = ttk.Frame(container)
        folder_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        folder_row.columnconfigure(0, weight=1)
        ttk.Entry(folder_row, textvariable=self.folder_path, state="readonly").grid(row=0, column=0, sticky="ew")
        ttk.Button(folder_row, text="Browse...", command=self.select_folder).grid(row=0, column=1, padx=(8, 0))

        self.progress = ttk.Progressbar(container, mode="determinate")
        self.progress.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(container, textvariable=self.status_text).grid(row=2, column=0, sticky="w", pady=(0, 8))

        button_row = ttk.Frame(container)
        button_row.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        self.start_button = ttk.Button(button_row, text="Start", command=self.start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(button_row, text="Stop", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=8)
        ttk.Button(button_row, text="Undo Last", command=self.undo_last).pack(side="left", padx=(0, 8))
        ttk.Button(button_row, text="Undo All", command=self.undo_all).pack(side="left")

        log_frame = ttk.Frame(container)
        log_frame.grid(row=4, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_box = tk.Listbox(log_frame)
        self.log_box.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_box.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_box.configure(yscrollcommand=scrollbar.set)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_path.set(folder)

    def start(self):
        folder = self.folder_path.get()
        if not folder:
            messagebox.showwarning("No folder selected", "Please select a folder first.")
            return
        self._stop_requested = False
        self.log_box.delete(0, tk.END)
        self.progress.configure(value=0, maximum=1)
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_text.set("Organizing...")
        threading.Thread(target=self._organize, args=(folder,), daemon=True).start()

    def _organize(self, folder):
        try:
            moved = FileOrganizer(folder, logger=self.logger, history=self.history).organize(
                stop_check=lambda: self._stop_requested,
                on_move=self._report_move,
                on_progress=self._report_progress,
            )
            self.root.after(0, self._on_finished, f"Done. Moved {moved} file(s).")
        except OSError as error:
            self.root.after(0, self._on_finished, f"Error: {error}")

    def _report_progress(self, current, total):
        self.root.after(0, self._update_progress, current, total)

    def _update_progress(self, current, total):
        self.progress.configure(value=current, maximum=max(total, 1))
        self.status_text.set(f"Organizing... ({current}/{total})")

    def _report_move(self, source, destination):
        self.root.after(0, self._append_log, f"{source.name} -> {destination.parent.name}/{destination.name}")

    def _append_log(self, message):
        self.log_box.insert(tk.END, message)
        self.log_box.see(tk.END)

    def _on_finished(self, message):
        self.status_text.set(message)
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")

    def stop(self):
        self._stop_requested = True
        self.status_text.set("Stopping...")

    def undo_last(self):
        self.status_text.set(self.history.undo_last())

    def undo_all(self):
        results = self.history.undo_all()
        self.status_text.set(f"Undone {len(results)} move(s).")


if __name__ == "__main__":
    root = tk.Tk()
    OrganizerGUI(root)
    root.mainloop()
