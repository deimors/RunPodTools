from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import ResourceExistsError
import os
import argparse
from tqdm import tqdm
import time
import mimetypes

mimetypes.add_type("image/webp", ".webp")

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Upload files to Azure Blob Storage')
    parser.add_argument('connection_string', help='Azure Storage connection string')
    parser.add_argument('container_name', help='Azure Blob container name')
    parser.add_argument('-d', '--directory', default='.', help='Directory to upload (default: current directory)')
    
    args = parser.parse_args()
    
    # Create blob service client and container client once
    blob_service_client = BlobServiceClient.from_connection_string(args.connection_string)
    
    try:
        blob_service_client.create_container(args.container_name)
    except ResourceExistsError:
        pass
    
    container_client = blob_service_client.get_container_client(args.container_name)
    
    push_all(args.directory, container_client)
