"""Dependency availability checks for PYATC scanner."""


def check_dependencies():
    """Check which optional dependencies are available."""
    try:
        from pydub import AudioSegment
        pydub_available = True
        audio_segment = AudioSegment
    except ImportError:
        pydub_available = False
        audio_segment = None
        print("Pydub not available. Install with: pip install pydub")

    try:
        import miniaudio
        miniaudio_available = True
    except ImportError:
        miniaudio_available = False

    class Deps:
        def __init__(self):
            self.pydub = pydub_available
            self.miniaudio = miniaudio_available
            self.audios = audio_segment

    return Deps()


deps = check_dependencies()
MINIAUDIO_AVAILABLE = deps.miniaudio
PYDUB_AVAILABLE = deps.pydub
