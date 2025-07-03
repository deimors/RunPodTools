# save as serve.py
import argparse
from flask import Flask, send_from_directory
import os
import urllib.parse

app = Flask(__name__)

# Use argparse to handle command-line arguments
parser = argparse.ArgumentParser(description="Serve files from a specified directory.")
# Update argparse to exclude the default directory if directories are explicitly specified
parser.add_argument('--directory', '-d', action='append', help="Directories to serve files from")
# Add a port argument to argparse
parser.add_argument('--port', '-p', type=int, default=3138, help="Port to run the server on")
args = parser.parse_args()
files_directories = [os.path.abspath(d) for d in args.directory] if args.directory else [os.path.abspath('.')]
port = args.port

print(f"Serving files on port {port} from directories:")
for index, directory in enumerate(files_directories):
    print(f"  {index}: {directory}")
print()

# Validate that all specified directories exist
for directory in files_directories:
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a valid directory.")
        exit(1)

@app.route('/<int:directory_index>/<path:filename>')
def get_file(directory_index, filename):
    # URL-decode the filename
    filename = urllib.parse.unquote(filename)
    # Validate the directory index and search for the file
    if 0 <= directory_index < len(files_directories):
        directory_path = files_directories[directory_index]
        filepath = os.path.join(directory_path, filename)
        if os.path.isfile(filepath):
            return send_from_directory(directory_path, filename)
    return {'error': 'File not found'}, 404

@app.route('/')
def list_files():
    files = []
    for index, directory in enumerate(files_directories):
        for root, _, filenames in os.walk(directory):  # Recursively walk through subdirectories
            for filename in filenames:
                filepath = os.path.join(root, filename)
                if os.path.isfile(filepath):
                    relative_path = os.path.relpath(filepath, directory).replace(os.sep, '/')  # Use Linux-style paths
                    files.append({
                        'name': urllib.parse.quote(relative_path),  # URL-encode the path
                        'size': os.path.getsize(filepath),
                        'directory_index': index
                    })
    return {'files': files, 'directories': files_directories}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
