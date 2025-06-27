import os
import sys
from pathlib import Path

def delete_empty_dirs(root_dir):
    """Recursively delete all empty directories under root_dir."""
    root = Path(root_dir)
    # Walk bottom-up so we remove children before parents
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        dir_path = Path(dirpath)
        # If directory is empty (no files, no subdirs)
        if not any(dir_path.iterdir()):
            try:
                dir_path.rmdir()
                print(f"Deleted empty directory: {dir_path}")
            except Exception as e:
                print(f"Failed to delete {dir_path}: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python delete_empty_dirs.py /path/to/root_dir")
        sys.exit(1)
    delete_empty_dirs(sys.argv[1])
