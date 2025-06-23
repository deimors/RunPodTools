# save as serve.py
from flask import Flask, send_from_directory

app = Flask(__name__)

@app.route('/<path:path>')

def get_file(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3137)
