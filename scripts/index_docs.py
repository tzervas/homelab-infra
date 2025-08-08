import sys
import os

# Basic script to index markdown files by extracting their titles

def extract_title(file_path):
    with open(file_path, 'r') as file:
        for line in file:
            if line.strip():
                return line.strip().replace('#', '').strip()
    return None

def main(file_path):
    title = extract_title(file_path)
    if title:
        print(f"Indexed {file_path}: {title}")
    else:
        print(f"No title found in {file_path}")

if __name__ == "__main__":
    for file in sys.argv[1:]:
        main(file)

