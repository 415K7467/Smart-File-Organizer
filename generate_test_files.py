import shutil
import sys
from pathlib import Path

EXTENSIONS = [
    ".jpg", ".jpeg", ".png", ".gif",          # Images
    ".pdf", ".docx", ".txt", ".xlsx",         # Documents
    ".mp3", ".wav",                           # Audio
    ".mp4", ".avi",                           # Videos
    ".zip", ".tar",                           # Archives
    ".py", ".java", ".js",                    # Code
    ".rs", ".go", ".csv",                     # unhandled -> own extension folder
]

FILES_PER_EXTENSION = 3
NO_EXTENSION_FILES = 3


def delete(folder: Path) -> None:
    shutil.rmtree(folder)


def generate(folder: Path, files_per_extension: int = FILES_PER_EXTENSION) -> int:
    if(folder.exists()):
        delete(folder)

    folder.mkdir(parents=True, exist_ok=True)
    count = 0

    for extension in EXTENSIONS:
        for i in range(1, files_per_extension + 1):
            count += 1
            file = folder / f"file_{count}{extension}"
            file.write_text(f"sample content for {file.name}", encoding="utf-8")
    
    for i in range(1, NO_EXTENSION_FILES + 1):
        count += 1
        file = folder / f"no_extension_{i}"
        file.write_text("sample content with no extension", encoding="utf-8")
    return count

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("to_sort")
    total = generate(target)
    print(f"Created {total} files in '{target}' ready to be organized.")
