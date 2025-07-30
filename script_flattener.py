"""
Utility Python script to copy all .CS files from the source directory
to the destination directory, flattening the directory structure.
"""

import os
import shutil
import argparse


DEFAULT_SRC_DIR = "source"
DEFAULT_DEST_DIR = "flattened"


def flatten_directory(src_dir, dest_dir) -> int:
    """
    Copies all .CS files from src_dir to dest_dir, flattening the directory structure.

    :param src_dir: Source directory containing .CS files.
    :param dest_dir: Destination directory where .CS files will be copied.
    """
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    count = 0

    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".cs"):
                src_file_path = os.path.join(root, file)
                dest_file_path = os.path.join(dest_dir, file)
                shutil.copy2(src_file_path, dest_file_path)
                print(f"Copied: {src_file_path} to {dest_file_path}")
                count += 1

    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flatten directory structure by copying .CS files.")
    parser.add_argument("--src_dir", type=str, default=DEFAULT_SRC_DIR, help="Source directory containing .CS files.")
    parser.add_argument(
        "--dest_dir", type=str, default=DEFAULT_DEST_DIR, help="Destination directory for flattened .CS files."
    )

    args = parser.parse_args()

    count = flatten_directory(args.src_dir, args.dest_dir)
    print(f"\n{count} scripts flattened.\n")
