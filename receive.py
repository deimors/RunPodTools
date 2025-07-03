import argparse
import requests
import os
from tqdm import tqdm
import sys
import urllib.parse

# Use argparse to handle command-line arguments
parser = argparse.ArgumentParser(description="Download files from a specified server.")
parser.add_argument('--host', '-H', default='http://localhost:3138', help="Host of the server")
parser.add_argument('--directory', '-d', action='append', required=True, help="Directories to save downloaded files")
args = parser.parse_args()

server_url = args.host
save_directories = [os.path.abspath(d) for d in args.directory]

# Validate that all specified save directories exist
create_all = None
for save_directory in save_directories:
    if not os.path.isdir(save_directory):
        if create_all is None:
            choice = input(f"Directory '{save_directory}' does not exist. Create it? (y/n/all): ").strip().lower()
            if choice == "all":
                create_all = True
            elif choice == "n":
                print(f"Error: '{save_directory}' is not a valid directory.")
                sys.exit(1)
            elif choice != "y":
                print("Invalid choice. Exiting.")
                sys.exit(1)
        if create_all or choice == "y":
            os.makedirs(save_directory)
            print(f"Created directory: {save_directory}")

# Get the list of files and validate the number of directories
response = requests.get(f"{server_url}/")
response.raise_for_status()
response_data = response.json()
files = response_data.get('files', [])
directories_count = len(response_data.get('directories', []))

if len(save_directories) != directories_count:
    print(f"Error: Number of save directories ({len(save_directories)}) does not match the number of directories ({directories_count}) returned by the server.")
    sys.exit(1)

# List the files to be retrieved
print("Files to be downloaded:")
for file in files:
    print(f" - {file['name']} ({file['size']} bytes)")

# Calculate total size of all files to be downloaded
total_size = sum(file['size'] for file in files)
total_downloaded = 0

# Create an overall progress bar
with tqdm(
    total=total_size, unit='B', unit_scale=True, unit_divisor=1024, desc="Overall Progress"
) as overall_progress:
    # Download each file
    for file in files:
        filename = file['name']  # URL-encoded relative path of the file
        file_size = file['size']
        directory_index = file['directory_index']
        download_url = f"{server_url}/{directory_index}/{filename}"
        decoded_filename = urllib.parse.unquote(filename)  # URL-decode the filename
        save_path = os.path.join(save_directories[directory_index], decoded_filename)

        # Ensure subdirectories exist
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # Check if the file already exists
        if os.path.isfile(save_path):
            existing_size = os.path.getsize(save_path)
            if existing_size == file_size:
                print(f"Skipping: {decoded_filename} (already exists with the same size)")
                continue
            else:
                size_difference = file_size - existing_size
                print(f"Replacing: {decoded_filename} (size difference: {size_difference} bytes)")

        # Use tqdm to display the starting download message
        with tqdm(
            total=file_size, unit='B', unit_scale=True, unit_divisor=1024, desc=f"Downloading: {decoded_filename}"
        ) as file_progress:
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        file_progress.update(len(chunk))
                        overall_progress.update(len(chunk))
