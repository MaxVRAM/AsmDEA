"""
Utility Python script to copy all .CS files from the source directory
to the destination directory, flattening the directory structure.
"""

import os
import shutil
import argparse


SRC_DIR = "source"
DEST_DIR = "flattened"


def flatten_directory(details, src_dir, dest_dir) -> int:
    """
    Copies all .CS files from src_dir to dest_dir, flattening the directory structure.

    :param details: If True, adds comments with containing asmdef file and source-relative path to top of each .CS file.
    :param src_dir: Source directory containing .CS files.
    :param dest_dir: Destination directory where .CS files will be copied.
    """
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    count = 0
    asmdef_path = None
    detail_comment = ""

    for root, _, files in os.walk(src_dir):
        relative_folder = os.path.relpath(root, src_dir)
        for file in files:
            if details and file.endswith(".asmdef"):
                # Path to the asmdef file relative to the source directory (not including the source directory itself)
                asmdef_path = os.path.join(relative_folder, file)
                # Copy asmdef file as well
                asmdef_dest_path = os.path.join(dest_dir, file)
                shutil.copy2(os.path.join(root, file), asmdef_dest_path)
                print(f"Copied asmdef: {os.path.join(root, file)} to {asmdef_dest_path}")
                break

        for file in files:
            if file.endswith(".cs"):
                relative_file = os.path.join(relative_folder, file)
                detail_comment = f"// Asmdef: {asmdef_path}\n// Script: {relative_file}\n\n"
                src_file_path = os.path.join(root, file)
                dest_file_path = os.path.join(dest_dir, file)
                shutil.copy2(src_file_path, dest_file_path)
                if details:
                    try:
                        # Try UTF-8 encoding first
                        with open(dest_file_path, "r+", encoding="utf-8") as dest_file:
                            content = dest_file.read()
                            dest_file.seek(0, 0)
                            dest_file.write(detail_comment + content)
                    except UnicodeDecodeError:
                        try:
                            # If UTF-8 fails, try UTF-16
                            with open(dest_file_path, "r+", encoding="utf-16") as dest_file:
                                content = dest_file.read()
                                dest_file.seek(0, 0)
                                dest_file.write(detail_comment + content)
                        except UnicodeDecodeError:
                            # If all else fails, use binary mode to avoid encoding issues
                            with open(dest_file_path, "rb") as source:
                                content = source.read()
                            with open(dest_file_path, "wb") as dest:
                                dest.write(detail_comment.encode("utf-8") + content)
                print(f"Copied: {src_file_path} to {dest_file_path}")
                count += 1

    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Flatten directory structure by copying .CS files.")
    parser.add_argument("--details", action="store_true", help="Comment .CS files with asmdef name and path.")
    parser.add_argument("--src_dir", type=str, default=SRC_DIR, help="Source directory containing .CS files.")
    parser.add_argument("--dest_dir", type=str, default=DEST_DIR, help="Destination directory for flattened files.")

    args = parser.parse_args()

    count = flatten_directory(args.details, args.src_dir, args.dest_dir)
    print(f"\n{count} scripts flattened.\n")
