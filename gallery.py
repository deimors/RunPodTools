import os
import sys
from flask import Flask, send_from_directory, jsonify, render_template, abort, request, Response, send_file
from werkzeug.utils import secure_filename
import io
from PIL import Image
import argparse
import zipfile
from datetime import datetime
from typing import Dict
from gallery_source import FilesystemGallerySource

# Parse command-line arguments
parser = argparse.ArgumentParser(description="RunPodTools WebP Gallery")
parser.add_argument("webp_dir", help="Path to the WebP folder")
parser.add_argument("-u", "--upload_dir", help="Path to the alternate upload directory", default=None)
parser.add_argument("-a", "--archive_dir", help="Path to the archive target directory", default=None)
args = parser.parse_args()

webp_dir = os.path.abspath(args.webp_dir)
upload_dir = os.path.abspath(args.upload_dir) if args.upload_dir else webp_dir
archive_dir = os.path.abspath(args.archive_dir) if args.archive_dir else webp_dir

# Initialize gallery source
try:
    gallery_source = FilesystemGallerySource(webp_dir, upload_dir, archive_dir)
except ValueError as e:
    print(f"Error: {e}")
    sys.exit(1)

# Constants
FILES_PER_PAGE = 12
ALLOWED_EXTENSIONS = {'webp', 'jpg', 'jpeg', 'png'}

# Static frame cache
static_frame_cache:Dict[str, bytes] = {}

app = Flask(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/static-frame/<path:filename>")
def static_frame(filename):
    """Serve a specific frame of an animated webp as a static image"""
    frame_type = request.args.get("frame", "first")  # Default to the first frame
    cache_bust = request.args.get("bust", "")  # Cache busting parameter
    
    # Replace .png extension with .webp for existence check
    if filename.endswith('.png'):
        filename = filename.replace('.png', '.webp')
    
    if not gallery_source.file_exists(filename, "webp") or not filename.lower().endswith('.webp'):
        abort(404)
    
    # Create cache key including frame type and cache bust parameter
    cache_key = f"{filename}_{frame_type}_{cache_bust}"
    
    # Check if frame is already cached
    if cache_key in static_frame_cache:
        return Response(static_frame_cache[cache_key], mimetype='image/png')
    
    try:
        full_path = gallery_source.get_file_path(filename, "webp")
        with Image.open(full_path) as img:
            if frame_type == "last":
                img.seek(img.n_frames - 1)  # Get the last frame
            else:
                img.seek(0)  # Default to the first frame
            output = io.BytesIO()
            img.save(output, format='PNG')  # Save as PNG
            output.seek(0)
            
            # Cache the generated frame
            frame_data = output.getvalue()
            static_frame_cache[cache_key] = frame_data
            
            return Response(frame_data, mimetype='image/png')  # Serve as PNG
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
    directory_type = "webp" if dir_name == "webp" else "uploads"
    
    all_files = gallery_source.list_files(directory_type)
    
    # Sorting logic
    def sort_key(file):
        if sort_by == "filename":
            return file.lower()
        elif sort_by == "size":
            return gallery_source.get_file_size(file, directory_type)
        elif sort_by == "date":
            return gallery_source.get_file_mtime(file, directory_type)
        return gallery_source.get_file_mtime(file, directory_type)

    reverse = sort_dir == "desc"
    all_files = sorted(all_files, key=sort_key, reverse=reverse)

    start = page * FILES_PER_PAGE
    end = start + FILES_PER_PAGE
    files_metadata = [gallery_source.get_file_metadata(file, directory_type) for file in all_files[start:end]]

    return jsonify({"files": files_metadata})

@app.route("/webp/<path:filename>")
def webp_file(filename):
    if not gallery_source.file_exists(filename, "webp"):
        abort(404)
    return send_from_directory(webp_dir, filename)

@app.route("/uploads/<path:filename>")
def uploads_file(filename):
    if not gallery_source.file_exists(filename, "uploads"):
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
        if gallery_source.save_file(filename, file, "uploads"):
            return jsonify({"message": f"File '{filename}' uploaded successfully"}), 200
        else:
            return jsonify({"message": "Failed to save file"}), 500
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
    directory = data.get("directory", "webp")

    if not files:
        return jsonify({"success": False, "message": "No files selected"}), 400

    directory_type = "webp" if directory == "webp" else "uploads"
    zip_path = os.path.join(archive_dir, filename)  # Use archive_dir instead of zip_dir

    # Check if the target file already exists
    if os.path.exists(zip_path):
        return jsonify({"success": False, "message": f"File '{filename}' already exists"}), 400

    try:
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for file in files:
                if gallery_source.file_exists(file, directory_type):
                    file_path = gallery_source.get_file_path(file, directory_type)
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
    
    directory_type = "webp" if directory == "webp" else "uploads"
    deleted = []
    errors = []
    
    for file in files:
        if gallery_source.delete_file(file, directory_type):
            deleted.append(file)
            
            # Remove cached static frames for this file
            cache_keys_to_remove = [key for key in static_frame_cache.keys() if key.startswith(f"{file}_")]
            for cache_key in cache_keys_to_remove:
                del static_frame_cache[cache_key]
        else:
            errors.append(f"{file}: Failed to delete")
    
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
                target_path = gallery_source.get_file_path(original_name, "webp")

                if os.path.exists(target_path):
                    base_name, ext = os.path.splitext(original_name)
                    counter = 1
                    while os.path.exists(target_path):
                        target_path = gallery_source.get_file_path(f"{base_name}_{counter}{ext}", "webp")
                        counter += 1

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