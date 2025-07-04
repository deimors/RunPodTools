import os
import sys
from flask import Flask, send_from_directory, jsonify, render_template, abort, request, Response, send_file
from werkzeug.utils import secure_filename
import io
from PIL import Image
import argparse
import zipfile
from webp import extract_webp_animation_metadata
from images import get_image_metadata
from datetime import datetime

# Parse command-line arguments
parser = argparse.ArgumentParser(description="RunPodTools WebP Gallery")
parser.add_argument("webp_dir", help="Path to the WebP folder")
parser.add_argument("-u", "--upload_dir", help="Path to the alternate upload directory", default=None)
parser.add_argument("-a", "--archive_dir", help="Path to the archive target directory", default=None)
args = parser.parse_args()

webp_dir = os.path.abspath(args.webp_dir)
if not os.path.isdir(webp_dir):
    print(f"Error: '{webp_dir}' is not a valid directory.")
    sys.exit(1)

upload_dir = os.path.abspath(args.upload_dir) if args.upload_dir else webp_dir
if not os.path.isdir(upload_dir):
    print(f"Error: '{upload_dir}' is not a valid directory.")
    sys.exit(1)

archive_dir = os.path.abspath(args.archive_dir) if args.archive_dir else webp_dir
if not os.path.isdir(archive_dir):
    print(f"Error: '{archive_dir}' is not a valid directory.")
    sys.exit(1)

# Validate that all specified directories exist
for directory in [webp_dir, upload_dir, archive_dir]:
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a valid directory.")
        sys.exit(1)

# Constants
FILES_PER_PAGE = 12
ALLOWED_EXTENSIONS = {'webp', 'jpg', 'jpeg', 'png'}

app = Flask(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/static-frame/<path:filename>")
def static_frame(filename):
    """Serve a specific frame of an animated webp as a static image"""
    frame_type = request.args.get("frame", "first")  # Default to the first frame
    # Replace .png extension with .webp for existence check
    if filename.endswith('.png'):
        filename = filename.replace('.png', '.webp')
    full_path = os.path.join(webp_dir, filename)
    if not os.path.isfile(full_path) or not filename.lower().endswith('.webp'):
        abort(404)
    
    try:
        with Image.open(full_path) as img:
            if frame_type == "last":
                img.seek(img.n_frames - 1)  # Get the last frame
            else:
                img.seek(0)  # Default to the first frame
            output = io.BytesIO()
            img.save(output, format='PNG')  # Save as PNG
            output.seek(0)
            return Response(output.getvalue(), mimetype='image/png')  # Serve as PNG
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return send_from_directory(webp_dir, filename)

@app.route("/")
def index():
    return render_template("gallery.html")

@app.route("/images")
def list_images():
    dir_name = request.args.get("dir", "webp")
    page = int(request.args.get("page", 0))
    sort_by = request.args.get("sort_by", "date")  # Options: "filename", "date", "size"
    sort_dir = request.args.get("sort_dir", "asc")  # Options: "asc", "desc"
    target_dir = webp_dir if dir_name == "webp" else upload_dir
    
    # Include all allowed extensions in the file list
    all_files = [f for f in os.listdir(target_dir) 
                 if any(f.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)]
    
    # Sorting logic
    def sort_key(file):
        file_path = os.path.join(target_dir, file)
        if sort_by == "filename":
            return file.lower()
        elif sort_by == "size":
            return os.path.getsize(file_path)
        elif sort_by == "date":
            return os.path.getmtime(file_path)
        return os.path.getmtime(file_path)  # Default to date

    reverse = sort_dir == "desc"
    all_files = sorted(all_files, key=sort_key, reverse=reverse)

    start = page * FILES_PER_PAGE
    end = start + FILES_PER_PAGE
    files_metadata = []

    for file in all_files[start:end]:
        file_path = os.path.join(target_dir, file)
        last_modified = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
        if file.lower().endswith(".webp"):
            metadata = extract_webp_animation_metadata(file_path)
            if isinstance(metadata, dict):  # Only include valid metadata
                files_metadata.append({
                    "name": file,
                    "size_bytes": metadata["file_size"],
                    "resolution": f"{metadata['width']}x{metadata['height']}",
                    "frames": metadata["frame_count"],
                    "duration_seconds": metadata["total_duration_ms"] / 1000,
                    "frame_rate": metadata["frame_rate"],
                    "last_modified": last_modified
                })
            else:
                files_metadata.append({"name": file, "error": metadata, "last_modified": last_modified})
        elif file.lower().endswith((".png", ".jpg", ".jpeg")):
            metadata = get_image_metadata(file_path)
            if isinstance(metadata, dict):  # Only include valid metadata
                files_metadata.append({
                    "name": file,
                    "size_bytes": metadata["file_size"],
                    "resolution": f"{metadata['width']}x{metadata['height']}",
                    "last_modified": last_modified
                })
            else:
                files_metadata.append({"name": file, "error": metadata, "last_modified": last_modified})
        else:
            files_metadata.append({"name": file, "last_modified": last_modified})

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

@app.route("/archives")
def list_archives():
    """List all .zip files in the archive directory, including their contents."""
    sort_by = request.args.get("sort_by", "date")  # Options: "filename", "date", "size"
    sort_dir = request.args.get("sort_dir", "asc")  # Options: "asc", "desc"
    
    archive_files = [f for f in os.listdir(archive_dir) if f.lower().endswith(".zip")]
    
    # Sorting logic
    def sort_key(file):
        file_path = os.path.join(archive_dir, file)
        if sort_by == "filename":
            return file.lower()
        elif sort_by == "size":
            return os.path.getsize(file_path)
        elif sort_by == "date":
            return os.path.getmtime(file_path)
        return os.path.getmtime(file_path)  # Default to date

    reverse = sort_dir == "desc"
    archive_files = sorted(archive_files, key=sort_key, reverse=reverse)

    files_metadata = []

    for file in archive_files:
        file_path = os.path.join(archive_dir, file)
        last_modified = datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
        zip_contents = []

        try:
            with zipfile.ZipFile(file_path, "r") as zipf:
                for zip_info in zipf.infolist():
                    zip_contents.append({
                        "path": zip_info.filename,
                        "size_bytes": zip_info.file_size
                    })
        except Exception as e:
            print(f"Error reading zip file {file}: {e}")

        files_metadata.append({
            "name": file,
            "size_bytes": os.path.getsize(file_path),
            "last_modified": last_modified,
            "contents": zip_contents
        })

    return jsonify({"files": files_metadata})

@app.route("/archive", methods=["POST"])
def archive_files():
    """Compress selected files into a zip archive."""
    data = request.json
    filename = secure_filename(data.get("filename", "archive.zip"))
    files = data.get("files", [])
    directory = data.get("directory", "webp")  # Get directory from POST request payload

    if not files:
        return jsonify({"success": False, "message": "No files selected"}), 400

    target_dir = webp_dir if directory == "webp" else upload_dir
    zip_path = os.path.join(archive_dir, filename)  # Use archive_dir instead of zip_dir

    # Check if the target file already exists
    if os.path.exists(zip_path):
        return jsonify({"success": False, "message": f"File '{filename}' already exists"}), 400

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
    zip_path = os.path.join(archive_dir, filename)  # Use archive_dir instead of zip_dir
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

@app.route("/archive/extract", methods=["POST"])
def extract_archive():
    """Extract a .zip file into the webp directory."""
    data = request.json
    archive_name = data.get("filename")

    if not archive_name:
        return jsonify({"success": False, "message": "No archive filename provided"}), 400

    archive_path = os.path.join(archive_dir, archive_name)
    if not os.path.isfile(archive_path) or not archive_name.lower().endswith(".zip"):
        return jsonify({"success": False, "message": "Invalid archive file"}), 400

    try:
        with zipfile.ZipFile(archive_path, "r") as zipf:
            for zip_info in zipf.infolist():
                original_name = zip_info.filename
                target_path = os.path.join(webp_dir, original_name)

                # Ensure unique filename by appending an integer if a conflict occurs
                if os.path.exists(target_path):
                    base_name, ext = os.path.splitext(original_name)
                    counter = 1
                    while os.path.exists(target_path):
                        target_path = os.path.join(webp_dir, f"{base_name}_{counter}{ext}")
                        counter += 1

                # Extract the file
                with zipf.open(zip_info) as source, open(target_path, "wb") as target:
                    target.write(source.read())

        return jsonify({"success": True, "message": f"Archive '{archive_name}' extracted successfully"}), 200
    except Exception as e:
        print(f"Error extracting archive {archive_name}: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == "__main__":
    print(f"Serving from: {webp_dir}")
    print(f"Uploads will be saved to: {upload_dir}")
    app.run(host="0.0.0.0", port=3137)