import os
import sys
import re
from flask import Flask, send_from_directory, jsonify, render_template, abort, request, Response, send_file
from werkzeug.utils import secure_filename
import io
from PIL import Image
import cv2
import numpy as np
import argparse
import zipfile
from datetime import datetime
from typing import Dict
from gallery_source import FilesystemGallerySource, GallerySource
from mp4 import extract_mp4_first_frame

# Parse command-line arguments
parser = argparse.ArgumentParser(description="RunPodTools Media Gallery")
parser.add_argument("gallery_dir", help="Path to the gallery folder")
parser.add_argument("-u", "--upload_dir", help="Path to the alternate upload directory", default=None)
parser.add_argument("-a", "--archive_dir", help="Path to the archive target directory", default=None)
args = parser.parse_args()

gallery_dir = os.path.abspath(args.gallery_dir)
upload_dir = os.path.abspath(args.upload_dir) if args.upload_dir else gallery_dir
archive_dir = os.path.abspath(args.archive_dir) if args.archive_dir else gallery_dir

# Initialize gallery sources - one for each directory
try:
    gallery_source = FilesystemGallerySource(gallery_dir)
    uploads_source = FilesystemGallerySource(upload_dir)
    archive_source = FilesystemGallerySource(archive_dir, allowed_extensions={'zip'})
except ValueError as e:
    print(f"Error: {e}")
    sys.exit(1)

# Constants
FILES_PER_PAGE = 12
ALLOWED_EXTENSIONS = {'webp', 'jpg', 'jpeg', 'png', 'mp4'}

# Static frame cache
static_frame_cache:Dict[str, bytes] = {}
video_thumbnail_cache:Dict[str, bytes] = {}

app = Flask(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/static-frame/<string:dir_name>/<path:filename>")
def static_frame(dir_name, filename):
    """Serve a specific frame of an animated webp as a static image"""
    frame_type = request.args.get("frame", "first")
    cache_bust = request.args.get("bust", "")
    
    if filename.endswith('.png'):
        filename = filename.replace('.png', '.webp')
    
    if not filename.lower().endswith('.webp'):
        abort(404)

    source = get_source_for_directory(dir_name)
    if not source.file_exists(filename):
        abort(404)

    cache_key = f"{filename}_{frame_type}_{cache_bust}"
    
    if cache_key in static_frame_cache:
        return Response(static_frame_cache[cache_key], mimetype='image/png')
    
    try:
        full_path = source.get_file_path(filename)
        with Image.open(full_path) as img:
            if frame_type == "last":
                img.seek(img.n_frames - 1)
            else:
                img.seek(0)
            output = io.BytesIO()
            img.save(output, format='PNG')
            output.seek(0)
            
            frame_data = output.getvalue()
            static_frame_cache[cache_key] = frame_data
            
            return Response(frame_data, mimetype='image/png')
    except Exception as e:
        print(f"Error processing {filename}: {e}")
        return send_from_directory(source.directory, filename)

@app.route("/video-thumbnail/<dir>/<path:filename>")
def video_thumbnail(dir, filename):
    """Serve the first frame of an MP4 as a PNG thumbnail"""
    if dir == 'gallery':
        source = gallery_source
    elif dir == 'uploads':
        source = uploads_source
    else:
        abort(400)

    if not source.file_exists(filename) or not filename.lower().endswith('.mp4'):
        abort(404)

    cache_key = f"{dir}/{filename}"
    if cache_key in video_thumbnail_cache:
        return Response(video_thumbnail_cache[cache_key], mimetype='image/png')

    full_path = source.get_file_path(filename)
    frame = extract_mp4_first_frame(full_path)
    if frame is None:
        abort(500)

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb_frame)
    output = io.BytesIO()
    pil_img.save(output, format='PNG')
    output.seek(0)
    frame_data = output.getvalue()
    video_thumbnail_cache[cache_key] = frame_data
    return Response(frame_data, mimetype='image/png')


@app.route("/")
def index():
    return render_template("gallery.html")

def get_source_for_directory(dir_name: str) -> GallerySource:
    """Get the appropriate gallery source based on directory name."""
    if dir_name == "gallery":
        return gallery_source
    elif dir_name == "uploads":
        return uploads_source
    elif dir_name == "archive":
        return archive_source
    else:
        return gallery_source  # default

@app.route("/dirs")
def list_dirs():
    dir_name = request.args.get("dir", "gallery")
    source = get_source_for_directory(dir_name)
    tree = source.list_dir_tree()
    return jsonify({"tree": tree})

_INVALID_DIR_CHARS = re.compile(r'[/\\:*?"<>|]')

@app.route("/mkdir", methods=["POST"])
def make_dir():
    data = request.get_json(force=True, silent=True) or {}
    dir_name = data.get("dir", "")
    subdir = data.get("subdir", "")
    name = (data.get("name", "") or "").strip()

    if dir_name not in ("gallery", "uploads"):
        return jsonify({"message": "Invalid directory"}), 400
    if not name or name in (".", "..") or _INVALID_DIR_CHARS.search(name):
        return jsonify({"message": "Invalid directory name"}), 400

    source = get_source_for_directory(dir_name)
    if not source.create_subdir(subdir, name):
        return jsonify({"message": "Failed to create directory"}), 500

    return jsonify({"message": "Directory created"}), 200

@app.route("/images")
def list_images():
    dir_name = request.args.get("dir", "gallery")
    page = int(request.args.get("page", 0))
    sort_by = request.args.get("sort_by", "date")
    sort_dir = request.args.get("sort_dir", "asc")
    subpath = request.args.get("subpath", "")
    rating_filter = request.args.get("rating_filter", "all")
    
    source = get_source_for_directory(dir_name)
    all_files = source.list_files_in_dir(subpath)
    
    # Filter by rating if specified
    if rating_filter != "all":
        try:
            target_rating = int(rating_filter)
            if source.ratings_manager:
                all_files = [f for f in all_files 
                           if source.ratings_manager.get_rating(f) == target_rating]
        except (ValueError, TypeError):
            pass  # Invalid rating filter, ignore
    
    # Sorting logic
    def sort_key(file):
        if sort_by == "filename":
            return file.lower()
        elif sort_by == "size":
            return source.get_file_size(file)
        elif sort_by == "date":
            return source.get_file_mtime(file)
        return source.get_file_mtime(file)

    reverse = sort_dir == "desc"
    all_files = sorted(all_files, key=sort_key, reverse=reverse)

    start = page * FILES_PER_PAGE
    end = start + FILES_PER_PAGE
    files_metadata = [source.get_file_metadata(file) for file in all_files[start:end]]

    return jsonify({"files": files_metadata})

@app.route("/gallery/<path:filename>")
def gallery_file(filename):
    if not gallery_source.file_exists(filename):
        abort(404)
    return send_from_directory(gallery_dir, filename)

@app.route("/uploads/<path:filename>")
def uploads_file(filename):
    if not uploads_source.file_exists(filename):
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
        subdir = request.form.get("subdir", "")
        if uploads_source.save_file(filename, file, subdir):
            return jsonify({"message": f"File '{filename}' uploaded successfully"}), 200
        else:
            return jsonify({"message": "Invalid upload directory"}), 400
    return jsonify({"message": "Invalid file type"}), 400

@app.route("/rate", methods=["POST"])
def rate_file():
    """Set the rating for a file."""
    data = request.json
    dir_name = data.get("dir", "gallery")
    filename = data.get("filename", "")
    rating = data.get("rating", 0)
    
    if not filename:
        return jsonify({"success": False, "message": "No filename provided"}), 400
    
    # Validate rating value
    if not isinstance(rating, int) or not (0 <= rating <= 3):
        return jsonify({"success": False, "message": "Rating must be an integer between 0 and 3"}), 400
    
    source = get_source_for_directory(dir_name)
    
    # Check if source has ratings manager
    if not hasattr(source, 'ratings_manager') or source.ratings_manager is None:
        return jsonify({"success": False, "message": "Ratings not supported for this directory"}), 400
    
    # Verify file exists
    if not source.file_exists(filename):
        return jsonify({"success": False, "message": "File not found"}), 404
    
    # Set the rating
    if source.ratings_manager.set_rating(filename, rating):
        return jsonify({"success": True, "rating": rating}), 200
    else:
        return jsonify({"success": False, "message": "Failed to save rating"}), 500

@app.route("/metadata/<dir_name>/<path:filename>")
def get_metadata(dir_name, filename):
    """Extract and return metadata for a file, including workflow JSON."""
    import json
    
    source = get_source_for_directory(dir_name)
    
    if not source.file_exists(filename):
        return jsonify({"success": False, "message": "File not found"}), 404
    
    file_path = source.get_file_path(filename)
    file_ext = os.path.splitext(filename)[1].lower()
    metadata = {}
    
    def try_parse_json(value):
        """Try to parse a string as JSON, return original if it fails."""
        if isinstance(value, str):
            try:
                return json.loads(value)
            except:
                return value
        return value
    
    def decode_value(value):
        """Decode bytes to string if needed."""
        if isinstance(value, bytes):
            try:
                return value.decode('utf-8', errors='ignore')
            except:
                return str(value)
        return value
    
    try:
        # Extract metadata based on file type
        if file_ext in ['.webp', '.png', '.jpg', '.jpeg']:
            with Image.open(file_path) as img:
                # Basic image info
                metadata["_basic"] = {
                    "Format": img.format,
                    "Mode": img.mode,
                    "Size": f"{img.width} × {img.height}"
                }
                
                # Extract PNG info (this is where ComfyUI/InvokeAI store workflow data)
                if hasattr(img, 'info') and img.info:
                    # Look for known workflow/generation keys
                    workflow_keys = ['workflow', 'prompt', 'Workflow', 'Prompt']
                    parameter_keys = ['parameters', 'Parameters', 'Dream', 'invokeai_metadata', 'sd-metadata']
                    
                    for key, value in img.info.items():
                        decoded_value = decode_value(value)
                        parsed_value = try_parse_json(decoded_value)
                        
                        # Prioritize workflow/generation data
                        if key in workflow_keys:
                            metadata[f"🔧 {key}"] = parsed_value
                        elif key in parameter_keys:
                            metadata[f"⚙️ {key}"] = parsed_value
                        else:
                            # Store other metadata
                            if "_other" not in metadata:
                                metadata["_other"] = {}
                            metadata["_other"][key] = parsed_value
                
                # Try to get EXIF data (some tools store data here too)
                exif = img.getexif()
                if exif:
                    from PIL.ExifTags import TAGS
                    exif_data = {}
                    for tag_id, value in exif.items():
                        tag = TAGS.get(tag_id, tag_id)
                        decoded_value = decode_value(value)
                        # Try to parse as JSON for UserComment and other fields
                        if tag in ['UserComment', 'ImageDescription', 'XPComment']:
                            decoded_value = try_parse_json(decoded_value)
                        exif_data[str(tag)] = decoded_value
                    
                    if exif_data:
                        metadata["_exif"] = exif_data
        
        elif file_ext == '.mp4':
            # Extract video metadata using OpenCV
            cap = cv2.VideoCapture(file_path)
            if cap.isOpened():
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps if fps > 0 else 0
                
                metadata["_basic"] = {
                    "Format": "MP4",
                    "Size": f"{width} × {height}",
                    "FPS": f"{fps:.2f}",
                    "Frame Count": str(frame_count),
                    "Duration": f"{duration:.2f}s"
                }
                
                cap.release()
            
            # Extract MP4 metadata tags using mutagen
            try:
                from mutagen.mp4 import MP4
                video = MP4(file_path)
                
                # Look for workflow data in various MP4 tags
                workflow_keys = ['workflow', 'prompt', 'Workflow', 'Prompt', '©cmt', 'desc']
                parameter_keys = ['parameters', 'Parameters']
                
                for key in video.keys():
                    value = video[key]
                    # MP4 tags are usually lists
                    if isinstance(value, list) and len(value) > 0:
                        value = value[0]
                    
                    # Decode if bytes
                    if isinstance(value, bytes):
                        value = value.decode('utf-8', errors='ignore')
                    
                    value_str = str(value)
                    parsed_value = try_parse_json(value_str)
                    
                    # Check if this is workflow/generation data
                    if any(wk.lower() in key.lower() for wk in workflow_keys):
                        metadata[f"🔧 {key}"] = parsed_value
                    elif any(pk.lower() in key.lower() for pk in parameter_keys):
                        metadata[f"⚙️ {key}"] = parsed_value
                    else:
                        # Store in other metadata
                        if "_mp4_tags" not in metadata:
                            metadata["_mp4_tags"] = {}
                        metadata["_mp4_tags"][key] = parsed_value
            except Exception as e:
                print(f"Error extracting MP4 tags with mutagen: {e}")
            
            # Try using ffprobe for more comprehensive metadata extraction
            try:
                import subprocess
                result = subprocess.run(
                    ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', file_path],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    ffprobe_data = json.loads(result.stdout)
                    if 'format' in ffprobe_data and 'tags' in ffprobe_data['format']:
                        tags = ffprobe_data['format']['tags']
                        
                        for key, value in tags.items():
                            parsed_value = try_parse_json(value)
                            
                            # Look for workflow keywords in key names
                            key_lower = key.lower()
                            if any(wk in key_lower for wk in ['workflow', 'prompt', 'comfy']):
                                metadata[f"🔧 {key}"] = parsed_value
                            elif any(pk in key_lower for pk in ['parameter', 'setting']):
                                metadata[f"⚙️ {key}"] = parsed_value
                            elif "_ffprobe_tags" not in metadata:
                                metadata["_ffprobe_tags"] = {}
                                metadata["_ffprobe_tags"][key] = parsed_value
                            else:
                                metadata["_ffprobe_tags"][key] = parsed_value
            except FileNotFoundError:
                # ffprobe not available
                pass
            except Exception as e:
                print(f"Error extracting metadata with ffprobe: {e}")
                pass
        
        # Add file system metadata to _basic section
        file_stat = os.stat(file_path)
        if "_basic" not in metadata:
            metadata["_basic"] = {}
        metadata["_basic"]["File Size"] = f"{file_stat.st_size:,} bytes"
        metadata["_basic"]["Modified"] = datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        
        return jsonify({"success": True, "metadata": metadata})
    
    except Exception as e:
        print(f"Error extracting metadata from {filename}: {e}")
        return jsonify({"success": False, "message": f"Error extracting metadata: {str(e)}"}), 500

@app.route("/archives")
def list_archives():
    """List all .zip files in the archive directory, including their contents."""
    sort_by = request.args.get("sort_by", "date")
    sort_dir = request.args.get("sort_dir", "asc")
    
    archive_files = archive_source.list_files()
    
    # Sorting logic
    def sort_key(file):
        if sort_by == "filename":
            return file.lower()
        elif sort_by == "size":
            return archive_source.get_file_size(file)
        elif sort_by == "date":
            return archive_source.get_file_mtime(file)
        return archive_source.get_file_mtime(file)

    reverse = sort_dir == "desc"
    archive_files = sorted(archive_files, key=sort_key, reverse=reverse)

    files_metadata = []

    for file in archive_files:
        file_path = archive_source.get_file_path(file)
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
            "size_bytes": archive_source.get_file_size(file),
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
    directory = data.get("directory", "gallery")

    if not files:
        return jsonify({"success": False, "message": "No files selected"}), 400

    source = get_source_for_directory(directory)
    zip_path = archive_source.get_file_path(filename)

    if os.path.exists(zip_path):
        return jsonify({"success": False, "message": f"File '{filename}' already exists"}), 400

    try:
        with zipfile.ZipFile(zip_path, "w") as zipf:
            for file in files:
                if source.file_exists(file):
                    file_path = source.get_file_path(file)
                    zipf.write(file_path, arcname=file)
        return jsonify({"success": True, "filename": filename}), 200
    except Exception as e:
        print(f"Error creating zip: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route("/download/<path:filename>")
def download_file(filename):
    """Serve the zip file for download."""
    if not archive_source.file_exists(filename):
        abort(404)
    zip_path = archive_source.get_file_path(filename)
    return send_file(zip_path, as_attachment=True)

@app.route("/delete", methods=["POST"])
def delete_files():
    """Delete selected files from disk."""
    data = request.json
    files = data.get("files", [])
    directory = data.get("directory", "gallery")
    
    if not files:
        return jsonify({"success": False, "message": "No files selected"}), 400
    
    source = get_source_for_directory(directory)
    deleted = []
    errors = []
    
    for file in files:
        if source.delete_file(file):
            deleted.append(file)
            
            # Remove cached static frames for this file
            cache_keys_to_remove = [key for key in static_frame_cache.keys() if key.startswith(f"{file}_")]
            for cache_key in cache_keys_to_remove:
                del static_frame_cache[cache_key]
            # Remove cached video thumbnails for this file
            if file in video_thumbnail_cache:
                del video_thumbnail_cache[file]
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
    """Extract a .zip file into the gallery directory."""
    data = request.json
    archive_name = data.get("filename")

    if not archive_name:
        return jsonify({"success": False, "message": "No archive filename provided"}), 400

    if not archive_source.file_exists(archive_name) or not archive_name.lower().endswith(".zip"):
        return jsonify({"success": False, "message": "Invalid archive file"}), 400

    archive_path = archive_source.get_file_path(archive_name)

    try:
        with zipfile.ZipFile(archive_path, "r") as zipf:
            for zip_info in zipf.infolist():
                original_name = zip_info.filename
                target_path = gallery_source.get_file_path(original_name)

                if os.path.exists(target_path):
                    base_name, ext = os.path.splitext(original_name)
                    counter = 1
                    while os.path.exists(target_path):
                        target_path = gallery_source.get_file_path(f"{base_name}_{counter}{ext}")
                        counter += 1

                with zipf.open(zip_info) as source, open(target_path, "wb") as target:
                    target.write(source.read())

        return jsonify({"success": True, "message": f"Archive '{archive_name}' extracted successfully"}), 200
    except Exception as e:
        print(f"Error extracting archive {archive_name}: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == "__main__":
    print(f"Serving from: {gallery_dir}")
    print(f"Uploads will be saved to: {upload_dir}")
    app.run(host="0.0.0.0", port=3137)