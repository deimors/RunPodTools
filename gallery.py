import os
import sys
from flask import Flask, send_from_directory, jsonify, render_template_string, abort, request
from werkzeug.utils import secure_filename

# Validate input directory
if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} /path/to/webp_folder")
    sys.exit(1)

webp_dir = os.path.abspath(sys.argv[1])
if not os.path.isdir(webp_dir):
    print(f"Error: '{webp_dir}' is not a valid directory.")
    sys.exit(1)

# Constants
FILES_PER_PAGE = 12
ALLOWED_EXTENSIONS = {'webp'}

app = Flask(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Lazy WebP Gallery</title>
    <style>
        body { font-family: sans-serif; margin: 0; padding: 1em; background: #f8f8f8; }
        .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(480px, 1fr)); gap: 1em; }
        .gallery img { width: 100%; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.2); }
        #loading { text-align: center; margin: 2em; font-size: 1.2em; color: #888; }
        #drop-area {
            border: 2px dashed #888;
            border-radius: 8px;
            background: #fff;
            padding: 2em;
            margin-bottom: 2em;
            text-align: center;
            color: #888;
            transition: border-color 0.2s;
        }
        #drop-area.dragover {
            border-color: #0078d7;
            color: #0078d7;
            background: #e6f2ff;
        }
        #upload-status {
            margin-top: 1em;
            color: #007800;
        }
    </style>
</head>
<body>
    <h1>Lazy-Loaded WebP Gallery</h1>
    <div id="drop-area">
        <p>Drag &amp; drop a .webp file here to upload,<br>or click to select a file.</p>
        <input type="file" id="fileElem" accept=".webp" style="display:none" />
        <div id="upload-status"></div>
    </div>
    <div class="gallery" id="gallery"></div>
    <div id="loading">Loading...</div>

    <script>
        let page = 0;
        let loading = false;
        let done = false;

        const gallery = document.getElementById("gallery");
        const loadedImages = new Map();

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const img = entry.target;
                if (entry.isIntersecting) {
                    if (!img.dataset.src) return;
                    img.src = img.dataset.src;
                    loadedImages.set(img, true);
                } else {
                    if (loadedImages.has(img)) {
                        img.removeAttribute("src");  // Unload image
                        loadedImages.delete(img);
                    }
                }
            });
        }, {
            rootMargin: "1000px 0px",  // Start loading before visible
            threshold: 0.01
        });

        async function loadMore() {
            if (loading || done) return;
            loading = true;
            document.getElementById("loading").style.display = "block";

            const response = await fetch(`/files?page=${page}`);
            const data = await response.json();

            if (data.files.length === 0) {
                document.getElementById("loading").innerText = "No more files.";
                done = true;
                return;
            }

            data.files.forEach(file => {
                const img = document.createElement("img");
                img.src = `/webp/${file}`;
                img.alt = file;
                observer.observe(img);
                gallery.appendChild(img);
            });

            page++;
            loading = false;
        }

        // Initial load
         loadMore();

        // Infinite scroll
        window.addEventListener("scroll", () => {
            if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 300) {
                loadMore();
            }
        });

        const dropArea = document.getElementById('drop-area');
        const fileElem = document.getElementById('fileElem');
        const uploadStatus = document.getElementById('upload-status');

        dropArea.addEventListener('click', () => fileElem.click());

        dropArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropArea.classList.add('dragover');
        });
        dropArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropArea.classList.remove('dragover');
        });
        dropArea.addEventListener('drop', async (e) => {
            e.preventDefault();
            dropArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            await uploadFiles(files);
        });
        fileElem.addEventListener('change', async (e) => {
            const files = e.target.files;
            await uploadFiles(files);
        });

        async function uploadFiles(files) {
            const formData = new FormData();
            for (const file of files) {
                formData.append('file', file);
            }
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });
            const result = await response.json();
            uploadStatus.innerText = result.message;
        }
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/files")
def list_files():
    page = int(request.args.get("page", 0))
    all_files = sorted([f for f in os.listdir(webp_dir) if f.lower().endswith('.webp')])
    start = page * FILES_PER_PAGE
    end = start + FILES_PER_PAGE
    return jsonify({"files": all_files[start:end]})

@app.route("/webp/<path:filename>")
def webp_file(filename):
    full_path = os.path.join(webp_dir, filename)
    if not os.path.isfile(full_path):
        abort(404)
    return send_from_directory(webp_dir, filename)

@app.route("/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(webp_dir, filename))
        return jsonify({"message": f"File '{filename}' uploaded successfully"}), 200
    return jsonify({"message": "Invalid file type"}), 400

if __name__ == "__main__":
    print(f"Serving from: {webp_dir}")
    app.run(host="0.0.0.0", port=3137)