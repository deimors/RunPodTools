# save as serve.py
import argparse
from flask import Flask, send_from_directory
import os

app = Flask(__name__)

# Use argparse to handle command-line arguments
parser = argparse.ArgumentParser(description="Serve files from a specified directory.")
parser.add_argument('--directory', '-d', default='.', help="Directory to serve files from")
# Add a port argument to argparse
parser.add_argument('--port', '-p', type=int, default=3138, help="Port to run the server on")
args = parser.parse_args()
files_directory = args.directory
port = args.port

@app.route('/<path:path>')
def get_file(path):
    return send_from_directory(files_directory, path)

@app.route('/')
def list_files():
    files = []
    for filename in os.listdir(files_directory):
        filepath = os.path.join(files_directory, filename)
        if os.path.isfile(filepath):
            files.append({'name': filename, 'size': os.path.getsize(filepath)})
    return {'files': files}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
