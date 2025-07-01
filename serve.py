# save as serve.py
import argparse
from flask import Flask, send_from_directory

app = Flask(__name__)

# Use argparse to handle command-line arguments
parser = argparse.ArgumentParser(description="Serve files from a specified directory.")
parser.add_argument('--directory', '-d', default='.', help="Directory to serve files from")
# Add a port argument to argparse
parser.add_argument('--port', '-p', type=int, default=3137, help="Port to run the server on")
args = parser.parse_args()
files_directory = args.directory
port = args.port

@app.route('/<path:path>')
def get_file(path):
    return send_from_directory(files_directory, path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port)
