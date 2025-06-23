import os
import sys
from flask import Flask, send_from_directory, jsonify, render_template_string, abort, request, Response, send_file
from werkzeug.utils import secure_filename
import io
from PIL import Image
import argparse
import zipfile

# Parse command-line arguments
parser = argparse.ArgumentParser(description="RunPodTools WebP Gallery")
parser.add_argument("webp_dir", help="Path to the WebP folder")
parser.add_argument("-u", "--upload_dir", help="Path to the alternate upload directory", default=None)
args = parser.parse_args()

webp_dir = os.path.abspath(args.webp_dir)
if not os.path.isdir(webp_dir):
    print(f"Error: '{webp_dir}' is not a valid directory.")
    sys.exit(1)

upload_dir = os.path.abspath(args.upload_dir) if args.upload_dir else webp_dir
if not os.path.isdir(upload_dir):
    print(f"Error: '{upload_dir}' is not a valid directory.")
    sys.exit(1)

# Constants
FILES_PER_PAGE = 12
ALLOWED_EXTENSIONS = {'webp', 'jpg', 'jpeg', 'png'}

app = Flask(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/static-frame/<path:filename>")
def static_frame(filename):
    """Serve the first frame of an animated webp as a static image"""
    full_path = os.path.join(webp_dir, filename)
    if not os.path.isfile(full_path) or not filename.lower().endswith('.webp'):
        abort(404)
    
    try:
        with Image.open(full_path) as img:
            # Get the first frame only
            img.seek(0)
            output = io.BytesIO()
            img.save(output, format='WEBP')
            output.seek(0)
            return Response(output.getvalue(), mimetype='image/webp')
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return send_from_directory(webp_dir, filename)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Lazy WebP Gallery</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        body { font-family: sans-serif; margin: 0; padding: 1em; background: #f8f8f8; }
        #main-content {
            margin-left: 300px; /* Add margin to avoid toolbar overlap */
        }
        .gallery { 
            display: grid; 
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); 
            gap: 1em; 
        }
        .gallery .image-container {
            position: relative;
            width: 100%;
            border: 2px solid transparent; /* Default border */
            border-radius: 8px;
            transition: border-color 0.2s;
        }
        .gallery .image-container.selected {
            border-color: #0078d7; /* Light blue border for selected images */
        }
        .gallery img {
            display: block;
            width: 100%;
            border-radius: 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
        }
        .gallery .checkbox {
            position: absolute;
            top: 8px;
            left: 8px;
            display: none; /* Hidden by default */
        }
        .gallery .image-container:hover .checkbox,
        .gallery .image-container.selected .checkbox {
            display: block; /* Show checkbox on hover or if selected */
        }
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
        #toolbar {
            position: fixed;
            top: 1em;
            left: 1em;
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.2);
            padding: 1em;
            z-index: 1000;
            width: 200px;
        }
        #toolbar button {
            display: flex;
            align-items: center;
            justify-content: flex-start;
            width: 100%;
            margin-bottom: 0.5em;
            padding: 0.5em 1em;
            background: #0078d7;
            color: #fff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
        }
        #toolbar button:hover {
            background: #005fa3;
        }
        #toolbar button.active {
            background: #005fa3; /* Highlight active button */
        }
        #toolbar button i {
            margin-right: 0.5em;
        }
        #drop-area {
            display: none; /* Hide upload control by default */
        }
        #drop-area.visible {
            display: block; /* Show upload control when active */
        }
        #lightbox {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 2000;
        }
        #lightbox img {
            max-width: 90%;
            max-height: 90%;
            border-radius: 8px;
        }
        /* Modal styles */
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: none;
            z-index: 3000;
        }
        .modal-content {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #fff;
            padding: 2em;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            width: 300px;
            text-align: center;
        }
        .modal-content h2 {
            margin: 0 0 1em 0;
            font-size: 1.5em;
            color: #333;
        }
        .modal-content input {
            width: 100%;
            padding: 0.5em;
            margin-bottom: 1em;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1em;
        }
        .modal-content button {
            width: 100%;
            padding: 0.5em;
            background: #0078d7;
            color: #fff;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 1em;
            margin-bottom: 0.5em;
        }
        .modal-content button:hover {
            background: #005fa3;
        }
    </style>
</head>
<body>
    <div id="toolbar">
        <button id="gallery-btn" class="active"><i class="fas fa-images"></i>Gallery</button>
        <button id="uploads-btn"><i class="fas fa-upload"></i>Uploads</button>
        <button><i class="fas fa-file-archive"></i>Zips</button>
        <button id="select-all-btn"><i class="fas fa-check-square"></i>Select All</button>
        <button id="clear-selection-btn"><i class="fas fa-times-circle"></i>Clear Selection</button>
        <button id="zip-selected-btn"><i class="fas fa-file-zipper"></i>Zip Selected</button>
        <button id="delete-selected-btn"><i class="fas fa-trash"></i>Delete Selected</button>
    </div>
    <div id="main-content">
        <h1 id="main-heading">Gallery</h1>
        <div id="drop-area">
            <p>Drag &amp; drop a .webp, .jpg, .jpeg, or .png file here to upload,<br>or click to select a file.</p>
            <input type="file" id="fileElem" accept=".webp,.jpg,.jpeg,.png" style="display:none" />
            <div id="upload-status"></div>
        </div>
        <div class="gallery" id="gallery"></div>
        <div id="loading">Loading...</div>
    </div>
    <div id="lightbox">
        <img id="lightbox-img" src="" alt="Lightbox Image">
    </div>
    <div id="modal" class="modal">
        <div class="modal-content">
            <h2 id="modal-title">Enter Filename</h2>
            <input type="text" id="zip-filename" placeholder="Enter zip filename">
            <button id="zip-btn">Zip</button>
            <div id="modal-progress" style="display: none;">Zipping files...</div>
            <button id="download-btn" style="display: none;">Download</button>
        </div>
    </div>
    <script>
        let page = 0;
        let loading = false;
        let done = false;
        let currentDir = "webp"; // Default to WebP directory

        const gallery = document.getElementById("gallery");
        const loadedImages = new Map();
        const mainHeading = document.getElementById("main-heading");
        const galleryBtn = document.getElementById("gallery-btn");
        const uploadsBtn = document.getElementById("uploads-btn");
        const dropArea = document.getElementById("drop-area");
        const lightbox = document.getElementById("lightbox");
        const lightboxImg = document.getElementById("lightbox-img");
        const modal = document.getElementById("modal");
        const modalTitle = document.getElementById("modal-title"); // Define modalTitle
        const zipFilenameInput = document.getElementById("zip-filename"); // Define zipFilenameInput
        const zipBtn = document.getElementById("zip-btn"); // Ensure consistent usage of "zip-btn"
        const modalProgress = document.getElementById("modal-progress");
        const downloadBtn = document.getElementById("download-btn");

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const imgContainer = entry.target;
                const img = imgContainer.querySelector('img');
                if (entry.isIntersecting) {
                    if (!img.dataset.src) return;
                    img.src = img.dataset.static || img.dataset.src;
                    loadedImages.set(imgContainer, true);
                } else {
                    if (loadedImages.has(imgContainer)) {
                        img.removeAttribute("src");  // Unload image
                        loadedImages.delete(imgContainer);
                    }
                }
            });
        }, {
            rootMargin: "1000px 0px",  // Start loading before visible
            threshold: 0.01
        });

        function createImageElement(fileName, filePath, isWebP = false, animatedPath = null) {
            const container = document.createElement("div");
            container.className = "image-container";

            const img = document.createElement("img");
            img.alt = fileName;

            const checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.className = "checkbox";
            checkbox.addEventListener("change", () => {
                container.classList.toggle("selected", checkbox.checked);
            });

            img.src = filePath;

            if (isWebP && animatedPath) {
                img.dataset.static = filePath;
                img.dataset.animated = animatedPath;

                container.addEventListener("mouseenter", () => {
                    img.src = img.dataset.animated; // Play animation on hover
                });

                container.addEventListener("mouseleave", () => {
                    img.src = img.dataset.static; // Return to static frame when not hovering
                });
            }

            img.addEventListener("click", (e) => {
                if (e.target.className === "checkbox") return;
                lightboxImg.src = isWebP && animatedPath ? img.dataset.animated : img.src;
                lightbox.style.display = "flex";
            });

            container.appendChild(img);
            container.appendChild(checkbox);
            return container;
        }

        async function loadMore() {
            if (loading || done) return;
            loading = true;
            document.getElementById("loading").style.display = "block";

            const response = await fetch(`/files?dir=${currentDir}&page=${page}`);
            const data = await response.json();

            if (data.files.length === 0) {
                document.getElementById("loading").innerText = "No more files.";
                done = true;
                loading = false;
                return;
            }

            data.files.forEach(file => {
                const fileExt = file.split('.').pop().toLowerCase();
                const isWebP = fileExt === 'webp';
                const filePath = isWebP ? `/static-frame/${file}` : `/${currentDir}/${file}`;
                const animatedPath = isWebP ? `/${currentDir}/${file}` : null;
                const container = createImageElement(file, filePath, isWebP, animatedPath);
                gallery.appendChild(container);
            });

            page++;
            loading = false;

            // Check if enough images are loaded to create a scrollbar
            const viewportHeight = window.innerHeight;
            const contentHeight = document.body.scrollHeight;
            if (contentHeight <= viewportHeight && !done) {
                loadMore(); // Continue loading more images if no scrollbar yet
            }
        }

        function switchDirectory(dir) {
            currentDir = dir;
            page = 0;
            done = false;
            gallery.innerHTML = ""; // Clear current gallery
            loadMore(); // Load new directory contents

            // Update heading and button states
            mainHeading.innerText = dir === "webp" ? "Gallery" : "Uploads Directory";
            galleryBtn.classList.toggle("active", dir === "webp");
            uploadsBtn.classList.toggle("active", dir === "uploads");

            // Show or hide upload control
            dropArea.classList.toggle("visible", dir === "uploads");
        }

        galleryBtn.addEventListener("click", () => switchDirectory("webp"));
        uploadsBtn.addEventListener("click", () => switchDirectory("uploads"));

        // Close lightbox on click
        lightbox.addEventListener("click", () => {
            lightbox.style.display = "none";
            lightboxImg.src = "";
        });

        // Initial load
        loadMore();

        // Infinite scroll
        window.addEventListener("scroll", () => {
            if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 300) {
                loadMore();
            }
        });

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

            if (response.ok) {
                for (const file of files) {
                    const fileExt = file.name.split('.').pop().toLowerCase();
                    const isWebP = fileExt === 'webp';
                    const filePath = `/uploads/${file.name}`;
                    const animatedPath = isWebP ? `/uploads/${file.name}` : null;
                    const container = createImageElement(file.name, filePath, isWebP, animatedPath);
                    gallery.appendChild(container);
                }
            }
        }

        document.getElementById("toolbar").addEventListener("click", (e) => {
            if (e.target.closest("#select-all-btn")) {
                // Select all images
                document.querySelectorAll(".gallery .image-container").forEach(container => {
                    const checkbox = container.querySelector(".checkbox");
                    checkbox.checked = true;
                    container.classList.add("selected");
                });
            } else if (e.target.closest("#clear-selection-btn")) {
                // Clear selection
                document.querySelectorAll(".gallery .image-container").forEach(container => {
                    const checkbox = container.querySelector(".checkbox");
                    checkbox.checked = false;
                    container.classList.remove("selected");
                });
            } else if (e.target.closest("#zip-selected-btn")) {
                // Show modal popup
                modal.style.display = "block";
                modalTitle.innerText = "Enter Filename"; // Use modalTitle
                zipFilenameInput.style.display = "block"; // Use zipFilenameInput
                zipBtn.style.display = "block"; // Use consistent ID
                modalProgress.style.display = "none";
                downloadBtn.style.display = "none";
            } else if (e.target.closest("#delete-selected-btn")) {
                const selectedFiles = Array.from(document.querySelectorAll(".gallery .image-container.selected img"))
                    .map(img => img.alt);
                if (selectedFiles.length === 0) {
                    alert("No files selected.");
                    return;
                }

                // Show delete confirmation modal
                modal.style.display = "block";
                modalTitle.innerText = `Delete ${selectedFiles.length} file(s)?`;
                zipFilenameInput.style.display = "none"; // Hide filename input
                zipBtn.style.display = "none"; // Hide zip button
                modalProgress.style.display = "none"; // Hide progress
                downloadBtn.style.display = "none"; // Hide download button

                const deleteBtn = document.createElement("button");
                deleteBtn.id = "delete-btn";
                deleteBtn.innerText = "Delete";
                deleteBtn.style.width = "100%";
                deleteBtn.style.padding = "0.5em";
                deleteBtn.style.background = "#d9534f"; // Red color for delete
                deleteBtn.style.color = "#fff";
                deleteBtn.style.border = "none";
                deleteBtn.style.borderRadius = "4px";
                deleteBtn.style.cursor = "pointer";
                deleteBtn.style.fontSize = "1em";
                deleteBtn.style.marginBottom = "0.5em";

                deleteBtn.addEventListener("click", async () => {
                    modal.style.display = "none";
                    await deleteFiles(selectedFiles);
                });

                modal.querySelector(".modal-content").appendChild(deleteBtn);
            }
        });

        zipBtn.addEventListener("click", async () => {
            const filename = zipFilenameInput.value.trim(); // Use zipFilenameInput
            if (!filename) {
                alert("Please enter a filename.");
                return;
            }

            // Start zipping process
            modalTitle.innerText = "Zipping Files..."; // Use modalTitle
            zipFilenameInput.style.display = "none"; // Use zipFilenameInput
            zipBtn.style.display = "none"; // Use consistent ID
            modalProgress.style.display = "block";

            const selectedFiles = Array.from(document.querySelectorAll(".gallery .image-container.selected img"))
                .map(img => img.alt);

            const response = await fetch("/zip", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filename, files: selectedFiles, directory: currentDir }) // Include directory in request
            });

            const result = await response.json();
            if (result.success) {
                modalTitle.innerText = "Zip Completed"; // Use modalTitle
                modalProgress.style.display = "none";
                downloadBtn.style.display = "block";
                downloadBtn.onclick = () => {
                    window.location.href = `/download/${result.filename}`;
                    modal.style.display = "none";
                };
            } else {
                modalTitle.innerText = "Error Zipping Files"; // Use modalTitle
                modalProgress.style.display = "none";
            }
        });

        async function deleteFiles(files) {
            const response = await fetch("/delete", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ files, directory: currentDir })
            });
            const result = await response.json();
            if (result.success) {
                // Remove deleted files from gallery
                result.deleted.forEach(filename => {
                    const imgContainer = Array.from(gallery.children).find(container => {
                        const img = container.querySelector("img");
                        return img && img.alt === filename;
                    });
                    if (imgContainer) {
                        gallery.removeChild(imgContainer);
                    }
                });
                alert(result.message);
            } else {
                alert("Error deleting files: " + result.message);
            }
        }

        // Close modal when clicking outside
        modal.addEventListener("click", (e) => {
            if (e.target === modal) {
                modal.style.display = "none";
                const deleteBtn = document.getElementById("delete-btn");
                if (deleteBtn) deleteBtn.remove(); // Remove delete button from modal
            }
        });
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/files")
def list_files():
    dir_name = request.args.get("dir", "webp")
    page = int(request.args.get("page", 0))
    target_dir = webp_dir if dir_name == "webp" else upload_dir
    
    # Include all allowed extensions in the file list
    all_files = sorted([f for f in os.listdir(target_dir) 
                      if any(f.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)])
    
    start = page * FILES_PER_PAGE
    end = start + FILES_PER_PAGE
    return jsonify({"files": all_files[start:end]})

@app.route("/webp/<path:filename>")
def webp_file(filename):
    full_path = os.path.join(webp_dir, filename)
    if not os.path.isfile(full_path):
        abort(404)
    return send_from_directory(webp_dir, filename)

@app.route("/uploads/<path:filename>")
def uploads_file(filename):
    full_path = os.path.join(upload_dir, filename)
    if not os.path.isfile(full_path):
        abort(404)
    return send_from_directory(upload_dir, filename)

@app.route("/upload", methods=["POST"])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(upload_dir, filename))
        return jsonify({"message": f"File '{filename}' uploaded successfully"}), 200
    return jsonify({"message": "Invalid file type"}), 400

@app.route("/zip", methods=["POST"])
def zip_files():
    """Compress selected files into a zip archive."""
    data = request.json
    filename = secure_filename(data.get("filename", "archive.zip"))
    files = data.get("files", [])
    directory = data.get("directory", "webp")  # Get directory from POST request payload

    if not files:
        return jsonify({"success": False, "message": "No files selected"}), 400

    target_dir = webp_dir if directory == "webp" else upload_dir
    zip_path = os.path.join(upload_dir, filename)
    try:
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for file in files:
                file_path = os.path.join(target_dir, file)
                if os.path.isfile(file_path):
                    zipf.write(file_path, arcname=file)
        return jsonify({"success": True, "filename": filename}), 200
    except Exception as e:
        print(f"Error creating zip: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/download/<path:filename>")
def download_file(filename):
    """Serve the zip file for download."""
    zip_path = os.path.join(upload_dir, filename)
    if not os.path.isfile(zip_path):
        abort(404)
    return send_file(zip_path, as_attachment=True)

@app.route("/delete", methods=["POST"])
def delete_files():
    """Delete selected files from disk."""
    data = request.json
    files = data.get("files", [])
    directory = data.get("directory", "webp")
    
    if not files:
        return jsonify({"success": False, "message": "No files selected"}), 400
    
    target_dir = webp_dir if directory == "webp" else upload_dir
    deleted = []
    errors = []
    
    for file in files:
        file_path = os.path.join(target_dir, file)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
                deleted.append(file)
        except Exception as e:
            errors.append(f"{file}: {str(e)}")
    
    success = len(deleted) > 0 and len(errors) == 0
    message = f"Deleted {len(deleted)} files" if success else f"Errors: {', '.join(errors)}"
    
    return jsonify({
        "success": success, 
        "message": message,
        "deleted": deleted,
        "errors": errors
    }), 200 if success else 500

if __name__ == "__main__":
    print(f"Serving from: {webp_dir}")
    print(f"Uploads will be saved to: {upload_dir}")
    app.run(host="0.0.0.0", port=3137)