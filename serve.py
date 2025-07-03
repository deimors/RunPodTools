# save as serve.py
import argparse
from flask import Flask, send_from_directory
import os

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

@app.route('/<int:directory_index>/<path:filename>')
def get_file(directory_index, filename):
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
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                files.append({'name': filename, 'size': os.path.getsize(filepath), 'directory_index': index})
    return {'files': files, 'total_directories': len(files_directories), 'directories': files_directories}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
