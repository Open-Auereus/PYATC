from typing import Optional, Any

class OptionalDependencies:
    """Manages optional dependencies with graceful fallback"""

    websocket: Optional[Any] = None
    websocket_available: bool = False
    AudioSegment: Optional[Any] = None
    pydub_available: bool = False
    miniaudio: Optional[Any] = None
    miniaudio_available: bool = False

    def __init__(self):
        # WebSocket support
        try:
            import websocket
            self.websocket_available = True
            self.websocket = websocket
        except ImportError:
            self.websocket_available = False
            self.websocket = None
            print("WebSocket support not available. Install with: pip install websocket-client")

        # Pydub support
        try:
            from pydub import AudioSegment
            self.pydub_available = True
            self.AudioSegment = AudioSegment
        except ImportError:
            self.pydub_available = False
            self.AudioSegment = None
            print("Pydub not available. Install with: pip install pydub")

        # Miniaudio support
        try:
            import miniaudio
            self.miniaudio_available = True
            self.miniaudio = miniaudio
        except ImportError:
            self.miniaudio_available = False
            self.miniaudio = None
            print("Miniaudio not available. Install with: pip install miniaudio")

# Create singleton instance
deps = OptionalDependencies()

# Export for backward compatibility
WEBSOCKET_AVAILABLE = deps.websocket_available
PYDUB_AVAILABLE = deps.pydub_available
MINIAUDIO_AVAILABLE = deps.miniaudio_available