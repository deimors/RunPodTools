from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
import os
import argparse
from tqdm import tqdm
import time

def push_to_blob(filename, connection_string, container_name):
    """
    Upload a file to Azure Blob Storage.
    
    Args:
        filename (str): Path to the file to upload
        connection_string (str): Azure Storage connection string
        container_name (str): Name of the blob container
    """
    blob_name = os.path.basename(filename)
    file_size = os.path.getsize(filename)
    
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    try:
        blob_service_client.create_container(container_name)
    except ResourceExistsError:
        pass
    
    start_time = time.time()
    
    with tqdm(
        total=file_size, unit='B', unit_scale=True, unit_divisor=1024, desc=f"Uploading: {os.path.basename(filename)}"
    ) as progress:
        with open(filename, 'rb') as data:
            blob_client = blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_name
            )
            
            def progress_callback(bytes_transferred, total):
                progress.update(bytes_transferred)
            
            blob_client.upload_blob(data, overwrite=True, progress_hook=progress_callback)
    
    end_time = time.time()
    upload_time = end_time - start_time
    upload_speed = file_size / upload_time if upload_time > 0 else 0
    
    print(f"Uploaded {filename} as {blob_name} | Size: {file_size:,} bytes | Time: {upload_time:.2f}s | Speed: {upload_speed / (1024 * 1024):.2f} MB/s")

def push_all(directory, connection_string, container_name):
    """
    Upload all files in a directory to Azure Blob Storage.
    
    Args:
        directory (str): Path to the directory containing files to upload
        connection_string (str): Azure Storage connection string
        container_name (str): Name of the blob container
    """
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        return
    
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            push_to_blob(filepath, connection_string, container_name)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Upload files to Azure Blob Storage')
    parser.add_argument('connection_string', help='Azure Storage connection string')
    parser.add_argument('container_name', help='Azure Blob container name')
    parser.add_argument('-d', '--directory', default='.', help='Directory to upload (default: current directory)')
    
    args = parser.parse_args()
    
    push_all(args.directory, args.connection_string, args.container_name)
    args = parser.parse_args()
    
    push_all(args.directory, args.connection_string, args.container_name)
