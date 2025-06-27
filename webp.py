import os
import sys
import struct

def extract_webp_animation_metadata(filename):
    """
    Extract metadata from a WebP animation file without using external libraries.
    
    Args:
        filename (str): Path to the WebP file.
    
    Returns:
        dict: A dictionary containing frame rate, frame count, time length, resolution, and file size.
        str: Error message if the file cannot be processed.
    """
    
    # Check if file exists
    if not os.path.isfile(filename):
        return f"Error: File '{filename}' not found."
    
    # Check file extension
    if not filename.lower().endswith('.webp'):
        return "Error: File is not a WebP image (based on extension)."
    
    try:
        # Read file
        with open(filename, 'rb') as f:
            data = f.read()
        
        # Check file size
        file_size = len(data)
        if file_size < 12:
            return "Error: File is too small to be a valid WebP."
        
        # Check WebP header
        if data[:4] != b'RIFF' or data[8:12] != b'WEBP':
            return "Error: Not a valid WebP file (incorrect header)."
        
        # Initialize metadata
        metadata = {
            "file_size": file_size,
            "width": None,
            "height": None,
            "is_animated": False,
            "frame_count": 0,
            "frame_durations": [],
            "total_duration_ms": 0,
            "frame_rate": 0.0
        }
        
        # Parse chunks
        pointer = 12  # Skip RIFF header and WEBP signature
        
        while pointer + 8 <= file_size:
            chunk_type = data[pointer:pointer+4]
            chunk_size = struct.unpack('<I', data[pointer+4:pointer+8])[0]
            
            # Make sure chunk_size is valid
            if pointer + 8 + chunk_size > file_size:
                return "Error: Invalid chunk size, file may be corrupted."
            
            # Extended WebP format chunk (contains animation flag)
            if chunk_type == b'VP8X':
                if chunk_size >= 10:
                    flags = data[pointer+8]
                    metadata["is_animated"] = (flags & 0x2) != 0
                    
                    # Extract width and height (24-bit integers, stored as little-endian)
                    width_minus_one = (data[pointer+12] | (data[pointer+13] << 8) | (data[pointer+14] << 16))
                    height_minus_one = (data[pointer+15] | (data[pointer+16] << 8) | (data[pointer+17] << 16))
                    metadata["width"] = width_minus_one + 1
                    metadata["height"] = height_minus_one + 1
            
            # Animation chunk
            elif chunk_type == b'ANIM':
                # Number of frames is not stored in the ANIM chunk, need to count ANMF chunks
                pass
            
            # Animation frame chunk
            elif chunk_type == b'ANMF':
                metadata["frame_count"] += 1
                # Frame duration (in milliseconds) is stored at offset 12 from chunk data
                # It's a 24-bit little-endian integer
                if chunk_size >= 16:
                    duration = (data[pointer+20] | (data[pointer+21] << 8) | (data[pointer+22] << 16))
                    metadata["frame_durations"].append(duration)
            
            # Move to next chunk (8 bytes for header + chunk data size, padded to even)
            pointer += 8 + chunk_size + (chunk_size & 1)
        
        # Calculate total duration and frame rate
        if metadata["frame_durations"]:
            metadata["total_duration_ms"] = sum(metadata["frame_durations"])
            avg_duration = metadata["total_duration_ms"] / metadata["frame_count"]
            metadata["frame_rate"] = 1000 / avg_duration if avg_duration > 0 else 0
        
        return metadata
        
    except IOError as e:
        return f"Error: I/O error occurred: {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error: {str(e)}"

def main():
    """Command-line interface for the WebP animation metadata extractor."""
    
    if len(sys.argv) != 2:
        print("Usage: python webp.py <filename>")
        sys.exit(1)
    
    filename = sys.argv[1]
    result = extract_webp_animation_metadata(filename)
    
    if isinstance(result, str):
        # Error occurred
        print(result)
        sys.exit(1)
    else:
        # Success, print metadata
        print(f"File: {filename}")
        print(f"Size: {result['file_size']} bytes")
        print(f"Resolution: {result['width']}x{result['height']} pixels")
        print(f"Frames: {result['frame_count']}")
        print(f"Total Duration: {result['total_duration_ms']/1000:.2f} seconds")
        print(f"Frame Rate: {result['frame_rate']:.2f} fps")
        
        # Print frame durations if not too many
        if len(result['frame_durations']) <= 10:
            print(f"Frame Durations (ms): {result['frame_durations']}")
        else:
            print(f"Frame Durations (ms): {result['frame_durations'][:5]} ... {result['frame_durations'][-5:]}")

if __name__ == "__main__":
    main()
