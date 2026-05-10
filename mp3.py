from mutagen.mp3 import MP3


def extract_mp3_metadata(filepath: str) -> dict:
    """Extract metadata from an MP3 file using mutagen."""
    try:
        audio = MP3(filepath)
        return {
            'file_size': audio.info.size if hasattr(audio.info, 'size') else None,
            'duration_seconds': audio.info.length,
        }
    except Exception as e:
        return {'error': str(e)}
