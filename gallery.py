import os
import sys
from flask import Flask, send_from_directory, jsonify, render_template_string, abort, request, Response, send_file
from werkzeug.utils import secure_filename
import io
from PIL import Image
import argparse
import zipfile
from webp import extract_webp_animation_metadata

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
        <div id="lightbox-info" style="
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            color: #fff;
            font-size: 0.9em;
            text-align: center;
            background: rgba(0, 0, 0, 0.7);
            padding: 5px 10px;
            border-radius: 4px;
        "></div>
    </div>
    <div id="modal" class="modal">
        <div class="modal-content">
            <!-- Delete Confirmation Step -->
            <div id="delete-confirmation" style="display: none;">
                <h2 id="modal-title">Delete Confirmation</h2>
                <button id="delete-btn" style="width: 100%; padding: 0.5em; background: #d9534f; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 1em; margin-bottom: 0.5em;">Delete</button>
            </div>

            <!-- Zip Filename Input Step -->
            <div id="zip-filename-step" style="display: none;">
                <h2 id="modal-title">Enter Filename</h2>
                <input type="text" id="zip-filename" placeholder="Enter zip filename" style="width: 100%; padding: 0.5em; margin-bottom: 1em; border: 1px solid #ddd; border-radius: 4px; font-size: 1em;">
                <button id="zip-btn" style="width: 100%; padding: 0.5em; background: #0078d7; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 1em; margin-bottom: 0.5em;">Zip</button>
            </div>

            <!-- Zip Progress Step -->
            <div id="zip-progress-step" style="display: none;">
                <h2 id="modal-title">Zipping Files...</h2>
                <div id="modal-progress" style="text-align: center; font-size: 1.2em; color: #888;">Please wait...</div>
            </div>

            <!-- Zip Download Step -->
            <div id="zip-download-step" style="display: none;">
                <h2 id="modal-title">Zip Completed</h2>
                <button id="download-btn" style="width: 100%; padding: 0.5em; background: #0078d7; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-size: 1em; margin-bottom: 0.5em;">Download</button>
            </div>
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

        const modalSteps = {
            deleteConfirmation: document.getElementById("delete-confirmation"),
            zipFilenameStep: document.getElementById("zip-filename-step"),
            zipProgressStep: document.getElementById("zip-progress-step"),  
            zipDownloadStep: document.getElementById("zip-download-step")
        };

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

        function showModal(step) {
            modal.style.display = "block";
            Object.values(modalSteps).forEach(s => s.style.display = "none");
            modalSteps[step].style.display = "block";
        }

        function hideModal() {
            modal.style.display = "none";
        }

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

        const fileMetadataCache = {}; // Object to store metadata indexed by directory and filename

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
                const fileName = file.name; // Extract filename from the response structure
                const fileExt = fileName.split('.').pop().toLowerCase();
                const isWebP = fileExt === 'webp';
                const filePath = isWebP ? `/static-frame/${fileName}` : `/${currentDir}/${fileName}`;
                const animatedPath = isWebP ? `/${currentDir}/${fileName}` : null;

                // Store metadata in the cache
                const cacheKey = `${currentDir}_${fileName.replace(/\./g, '_')}`;
                fileMetadataCache[cacheKey] = file;

                const container = createImageElement(fileName, filePath, isWebP, animatedPath);
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
            lightboxInfo.innerText = ""; // Clear info text
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
                showModal("zipFilenameStep"); // Show zip filename input step
            } else if (e.target.closest("#delete-selected-btn")) {
                const selectedFiles = Array.from(document.querySelectorAll(".gallery .image-container.selected img"))
                    .map(img => img.alt);
                if (selectedFiles.length === 0) {
                    alert("No files selected.");
                    return;
                }

                // Show delete confirmation modal
                showModal("deleteConfirmation");

                const deleteBtn = document.getElementById("delete-btn");
                deleteBtn.onclick = async () => {
                    hideModal();
                    await deleteFiles(selectedFiles);
                };
            }
        });

        zipBtn.addEventListener("click", async () => {
            const filename = zipFilenameInput.value.trim(); // Use zipFilenameInput
            if (!filename) {
                alert("Please enter a filename.");
                return;
            }

            // Start zipping process
            showModal("zipProgressStep");

            const selectedFiles = Array.from(document.querySelectorAll(".gallery .image-container.selected img"))
                .map(img => img.alt);

            const response = await fetch("/zip", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ filename, files: selectedFiles, directory: currentDir }) // Include directory in request
            });

            const result = await response.json();
            if (result.success) {
                showModal("zipDownloadStep");

                downloadBtn.onclick = () => {
                    window.location.href = `/download/${result.filename}`;
                    hideModal();
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
                hideModal();
                const deleteBtn = document.getElementById("delete-btn");
                if (deleteBtn) deleteBtn.remove(); // Remove delete button from modal
            }
        });

        const lightboxInfo = document.createElement("div");
        lightboxInfo.id = "lightbox-info";
        lightboxInfo.style.position = "absolute";
        lightboxInfo.style.bottom = "20px";
        lightboxInfo.style.left = "50%";
        lightboxInfo.style.transform = "translateX(-50%)";
        lightboxInfo.style.color = "#fff";
        lightboxInfo.style.fontSize = "0.9em";
        lightboxInfo.style.textAlign = "center";
        lightboxInfo.style.background = "rgba(0, 0, 0, 0.7)";
        lightboxInfo.style.padding = "5px 10px";
        lightboxInfo.style.borderRadius = "4px";
        lightbox.appendChild(lightboxInfo);

        lightboxImg.addEventListener("load", () => {
            const filename = lightboxImg.src.split("/").pop();
            const cacheKey = `${currentDir}_${filename.replace(/\./g, '_')}`;
            const fileMetadata = fileMetadataCache[cacheKey];

            if (fileMetadata) {
                const resolution = fileMetadata.resolution || "Unknown resolution";
                const frames = fileMetadata.frames || "Unknown frames";
                const duration = fileMetadata.duration_seconds ? `${fileMetadata.duration_seconds.toFixed(2)}s` : "Unknown duration";
                const frameRate = fileMetadata.frame_rate ? `${fileMetadata.frame_rate.toFixed(2)} fps` : "Unknown frame rate";

                lightboxInfo.innerText = `${filename} (${resolution}) | Frames: ${frames} | Duration: ${duration} | Frame Rate: ${frameRate}`;
            } else {
                lightboxInfo.innerText = `${filename} | Metadata not available`;
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
    files_metadata = []

    for file in all_files[start:end]:
        file_path = os.path.join(target_dir, file)
        if file.lower().endswith(".webp"):
            metadata = extract_webp_animation_metadata(file_path)
            if isinstance(metadata, dict):  # Only include valid metadata
                files_metadata.append({
                    "name": file,
                    "size_bytes": metadata["file_size"],
                    "resolution": f"{metadata['width']}x{metadata['height']}",
                    "frames": metadata["frame_count"],
                    "duration_seconds": metadata["total_duration_ms"] / 1000,
                    "frame_rate": metadata["frame_rate"]
                })
            else:
                files_metadata.append({"name": file, "error": metadata})
        else:
            files_metadata.append({"name": file})

    return jsonify({"files": files_metadata})

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