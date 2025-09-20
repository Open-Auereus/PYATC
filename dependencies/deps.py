def websocket_available():
    try:
        import websocket
        WEBSOCKET_AVAILABLE = True
    except ImportError:
        WEBSOCKET_AVAILABLE = False
        print("WebSocket support not available. Install with: pip install websocket-client rel")
    try:
        from pydub import AudioSegment
        PYDUB_AVAILABLE = True
    except ImportError:
        PYDUB_AVAILABLE = False
        print("Pydub not available. Install with: pip install pydub")

    try:
        from pydub import miniaudio
        MINIAUDIO_AVAILABLE = True
    except ImportError:
        MINIAUDIO_AVAILABLE = False

    # Create a simple object to hold our values
    class Deps:
        def __init__(self):
            self.websocket = WEBSOCKET_AVAILABLE
            self.pydub = PYDUB_AVAILABLE
            self.miniaudio = MINIAUDIO_AVAILABLE
            self.audios = AudioSegment if PYDUB_AVAILABLE else None
    
    return Deps()

deps = websocket_available()
MINIAUDIO_AVAILABLE = deps.miniaudio
PYDUB_AVAILABLE = deps.pydub
WEBSOCKET_AVAILABLE = deps.websocket