import argparse
import requests
import os
from tqdm import tqdm

# Use argparse to handle command-line arguments
parser = argparse.ArgumentParser(description="Download files from a specified server.")
parser.add_argument('--host', '-H', default='http://localhost', help="Host of the server")
parser.add_argument('--port', '-p', type=int, default=3138, help="Port of the server")
parser.add_argument('--directory', '-d', default='.', help="Directory to save downloaded files")
args = parser.parse_args()

server_url = f"{args.host}:{args.port}"
save_directory = args.directory

# Ensure the save directory exists
os.makedirs(save_directory, exist_ok=True)

# Get the list of files from the server
response = requests.get(f"{server_url}/")
response.raise_for_status()
files = response.json().get('files', [])

# List the files to be retrieved
print("Files to be downloaded:")
for file in files:
    print(f" - {file['name']} ({file['size']} bytes)")

# Download each file
for file in files:
    filename = file['name']
    file_size = file['size']
    download_url = f"{server_url}/{filename}"
    save_path = os.path.join(save_directory, filename)

    # Use tqdm to display the starting download message
    with tqdm(
        total=file_size, unit='B', unit_scale=True, unit_divisor=1024, desc=f"Starting download: {filename}"
    ) as progress:
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(save_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    progress.update(len(chunk))
                    f.write(chunk)
                    progress.update(len(chunk))
