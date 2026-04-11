from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import ResourceExistsError
import os
import argparse
from tqdm import tqdm
import time
import mimetypes
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading

mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("video/mp4", ".mp4")

def push_to_blob(filename, container_client):
    """
    Upload a file to Azure Blob Storage.
    
    Args:
        filename (str): Path to the file to upload
        container_client: Azure Blob Container client
    """
    blob_name = os.path.basename(filename)
    file_size = os.path.getsize(filename)
    content_type, _ = mimetypes.guess_type(filename)
    content_settings = ContentSettings(content_type=content_type or 'application/octet-stream')
    
    start_time = time.time()
    
    with tqdm(
        total=file_size, unit='B', unit_scale=True, unit_divisor=1024, desc=f"Uploading: {os.path.basename(filename)}"
    ) as progress:
        with open(filename, 'rb') as data:
            blob_client = container_client.get_blob_client(blob_name)
            
            def progress_callback(bytes_transferred, total):
                progress.update(bytes_transferred)

            blob_client.upload_blob(data, overwrite=True, content_settings=content_settings, progress_hook=progress_callback)

    end_time = time.time()
    upload_time = end_time - start_time
    upload_speed = file_size / upload_time if upload_time > 0 else 0
    
    print(f"Uploaded {filename} as {blob_name} | Size: {file_size:,} bytes | Content Type: {content_type} | Time: {upload_time:.2f}s | Speed: {upload_speed / (1024 * 1024):.2f} MB/s")

def push_all(directory, container_client):
    """
    Upload all files in a directory to Azure Blob Storage.
    
    Args:
        directory (str): Path to the directory containing files to upload
        container_client: Azure Blob Container client
    """
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        return
    
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            blob_name = os.path.basename(filepath)
            
            try:
                container_client.get_blob_client(blob_name).get_blob_properties()
                print(f"Skipping: {filename} (blob exists)")
                continue
            except Exception:
                pass
            
            push_to_blob(filepath, container_client)

class FileUploadHandler(FileSystemEventHandler):
    def __init__(self, container_client):
        self.container_client = container_client
        self.pending_files = {}
        self.lock = threading.Lock()
    
    def on_created(self, event):
        if event.is_directory:
            return
        
        filepath = event.src_path
        # Track file creation time
        with self.lock:
            self.pending_files[filepath] = time.time()
        
        # Schedule check to verify file is complete
        threading.Timer(2.0, self.check_and_upload, args=[filepath]).start()
    
    def check_and_upload(self, filepath):
        if not os.path.exists(filepath):
            return
        
        try:
            initial_size = os.path.getsize(filepath)
            time.sleep(1)
            final_size = os.path.getsize(filepath)
            
            if initial_size != final_size:
                threading.Timer(2.0, self.check_and_upload, args=[filepath]).start()
                return
            
            blob_name = os.path.basename(filepath)
            try:
                self.container_client.get_blob_client(blob_name).get_blob_properties()
                print(f"Skipping: {blob_name} (blob exists)")
                return
            except Exception:
                pass
            
            push_to_blob(filepath, self.container_client)
            
            with self.lock:
                self.pending_files.pop(filepath, None)
                
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

def watch_and_push(directory, container_client):
    """
    Watch a directory for new files and upload them to Azure Blob Storage.
    
    Args:
        directory (str): Path to the directory to watch
        container_client: Azure Blob Container client
    """
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        return
    
    event_handler = FileUploadHandler(container_client)
    observer = Observer()
    observer.schedule(event_handler, directory, recursive=False)
    observer.start()
    
    print(f"Watching directory: {directory}")
    print("Press Ctrl+C to stop...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped watching directory")
    
    observer.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Upload files to Azure Blob Storage')
    parser.add_argument('connection_string', help='Azure Storage connection string')
    parser.add_argument('container_name', help='Azure Blob container name')
    parser.add_argument('-d', '--directory', default='.', help='Directory to upload (default: current directory)')
    parser.add_argument('-w', '--watch', action='store_true', help='Watch directory for new files after initial upload')
    
    args = parser.parse_args()
    
    blob_service_client = BlobServiceClient.from_connection_string(args.connection_string)
    
    try:
        blob_service_client.create_container(args.container_name)
    except ResourceExistsError:
        pass
    
    container_client = blob_service_client.get_container_client(args.container_name)
    
    push_all(args.directory, container_client)
    
    if args.watch:
        watch_and_push(args.directory, container_client)
