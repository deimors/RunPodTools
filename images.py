import os
import struct
import sys

def get_image_metadata(filename):
    """
    Retrieve resolution and file size in bytes from a .jpeg, .jpg, or .png file.
    
    Args:
        filename (str): Path to the image file.
    
    Returns:
        dict: A dictionary containing resolution and file size.
        str: Error message if the file cannot be processed.
    """
    # Check if file exists
    if not os.path.isfile(filename):
        return f"Error: File '{filename}' not found."
    
    # Check file extension
    ext = filename.lower().rsplit('.', 1)[-1]
    if ext not in {'jpeg', 'jpg', 'png'}:
        return "Error: File is not a supported image type (.jpeg, .jpg, .png)."
    
    try:
        # Read file
        with open(filename, 'rb') as f:
            data = f.read()
        
        file_size = len(data)
        
        if ext in {'jpeg', 'jpg'}:
            # Parse JPEG file
            if data[:2] != b'\xff\xd8':  # Check JPEG SOI marker
                return "Error: Not a valid JPEG file."
            
            pointer = 2
            while pointer < file_size:
                if data[pointer] != 0xFF:  # Marker start
                    return "Error: Invalid JPEG structure."
                
                marker = data[pointer + 1]
                if marker == 0xC0 or marker == 0xC2:  # SOF0 or SOF2 (baseline or progressive)
                    height = struct.unpack('>H', data[pointer + 5:pointer + 7])[0]
                    width = struct.unpack('>H', data[pointer + 7:pointer + 9])[0]
                    return {"width": width, "height": height, "file_size": file_size}
                
                # Skip to next marker
                segment_length = struct.unpack('>H', data[pointer + 2:pointer + 4])[0]
                pointer += 2 + segment_length
            
            return "Error: Could not find resolution in JPEG file."
        
        elif ext == 'png':
            # Parse PNG file
            if data[:8] != b'\x89PNG\r\n\x1a\n':  # Check PNG signature
                return "Error: Not a valid PNG file."
            
            pointer = 8
            while pointer + 8 <= file_size:
                chunk_length = struct.unpack('>I', data[pointer:pointer + 4])[0]
                chunk_type = data[pointer + 4:pointer + 8]
                
                if chunk_type == b'IHDR':  # IHDR chunk contains width and height
                    width = struct.unpack('>I', data[pointer + 8:pointer + 12])[0]
                    height = struct.unpack('>I', data[pointer + 12:pointer + 16])[0]
                    return {"width": width, "height": height, "file_size": file_size}
                
                # Skip to next chunk (length + type + data + CRC)
                pointer += 8 + chunk_length + 4
            
            return "Error: Could not find resolution in PNG file."
    
    except IOError as e:
        return f"Error: I/O error occurred: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error: {str(e)}"

if __name__ == "__main__":
    """Command-line interface for the image metadata extractor."""
    if len(sys.argv) != 2:
        print("Usage: python images.py <filename>")
        sys.exit(1)
    
    filename = sys.argv[1]
    result = get_image_metadata(filename)
    
    if isinstance(result, str):
        # Error occurred
        print(result)
        sys.exit(1)
    else:
        # Success, print metadata
        print(f"File: {filename}")
        print(f"Width: {result['width']} pixels")
        print(f"Height: {result['height']} pixels")
        print(f"File Size: {result['file_size']} bytes")

