import os
import cv2


def extract_mp4_metadata(filename):
    """
    Extract metadata from an MP4 video file using opencv-python.

    Args:
        filename (str): Path to the MP4 file.

    Returns:
        dict: A dictionary containing resolution, duration, frame rate, and file size.
        str: Error message if the file cannot be processed.
    """
    if not os.path.isfile(filename):
        return f"Error: File '{filename}' not found."

    if not filename.lower().endswith('.mp4'):
        return "Error: File is not an MP4 video (based on extension)."

    try:
        cap = cv2.VideoCapture(filename)
        if not cap.isOpened():
            return f"Error: Could not open '{filename}'."

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        if fps <= 0:
            return "Error: Could not determine frame rate."

        duration_ms = (frame_count / fps) * 1000

        return {
            "file_size": os.path.getsize(filename),
            "width": width,
            "height": height,
            "duration_ms": duration_ms,
            "frame_rate": fps,
        }
    except Exception as e:
        return f"Error: {e}"


def extract_mp4_first_frame(filename):
    """
    Extract the first frame of an MP4 file as raw BGR numpy array.

    Args:
        filename (str): Path to the MP4 file.

    Returns:
        numpy.ndarray: BGR frame, or None on failure.
    """
    try:
        cap = cv2.VideoCapture(filename)
        if not cap.isOpened():
            return None
        success, frame = cap.read()
        cap.release()
        return frame if success else None
    except Exception:
        return None
