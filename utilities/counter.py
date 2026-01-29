# This Python script looks through all the .CS files in a directory and counts the number of lines in each file.
# It then outputs the total number of lines across all files.

import argparse
import os


def count_lines_in_cs_files(directory):
    total_lines = 0
    for root, _dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".cs"):
                with open(os.path.join(root, filename), "r", encoding="utf-8") as file:
                    total_lines += sum(1 for line in file)
    return total_lines


if __name__ == "__main__":
    # Optional position-based argument to define target directory to search, defaults to "./flattened"
    parser = argparse.ArgumentParser(description="Count lines in .CS files in a directory.")
    parser.add_argument(
        "directory", type=str, nargs="?", default="./flattened", help="Directory to search for .CS files."
    )
    args = parser.parse_args()

    total_lines = count_lines_in_cs_files(args.directory)
    print(f"\nTotal lines in .CS files: {total_lines}")
