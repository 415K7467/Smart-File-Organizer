from pathlib import Path

from file_organizer import FileOrganizer, MoveHistory, MoveLogger


class ConsoleMenu:
    """Console menu that lets the user organize a folder or undo previous moves."""

    def __init__(self):
        self.logger = MoveLogger()
        self.history = MoveHistory(logger=self.logger)

    def run(self):
        actions = {
            "1": self.organize_folder,
            "2": self.undo_last,
            "3": self.undo_all,
            "4": self.exit_app,
        }
        while True:
            self._print_menu()
            action = actions.get(input("Choose an option: ").strip())
            if action is None:
                print("Invalid option, try again.\n")
                continue
            if action() is False:
                break

    def _print_menu(self):
        print("\n=== Smart File Organizer ===")
        print("1. Organize a folder")
        print("2. Undo last move")
        print("3. Undo all moves")
        print("4. Exit")

    def organize_folder(self):
        folder = input("Enter the folder path to organize: ").strip()
        if not Path(folder).is_dir():
            print("That folder does not exist.")
            return
        moved = FileOrganizer(folder, logger=self.logger, history=self.history).organize()
        print(f"Moved {moved} file(s). See organizer_log.csv for details.")

    def undo_last(self):
        print(self.history.undo_last())

    def undo_all(self):
        results = self.history.undo_all()
        print(f"Undone {len(results)} move(s).")

    def exit_app(self):
        print("Goodbye!")
        return False


if __name__ == "__main__":
    ConsoleMenu().run()
