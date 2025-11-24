"""
Audio handling module for playback and streaming.
"""
import io
import time
import logging
import threading
import asyncio
from dataclasses import dataclass
from typing import Optional, Dict
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import requests

try:
    import miniaudio
    MINIAUDIO_AVAILABLE = True
except ImportError:
    MINIAUDIO_AVAILABLE = False

try:
    import sounddevice as sd
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    PYDUB_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass(slots=True)
class AudioData:
    """Represents an audio transmission."""
    id: int
    url: str
    who_from: str
    frequency: str
    station_name: str
    pilot: str
    airport: str
    position: str
    voice_name: str
    from_userid: str
    flight_rules: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    stamp: Optional[str] = None
    priority: int = 0

class AudioBuffer:
    """Manages pre-fetched audio data for instant playback."""

    def __init__(self, max_size: int = 10):
        self.buffer: Dict[int, bytes] = {}
        self.max_size = max_size
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.lock = threading.Lock()

    def prefetch(self, audio_data: AudioData):
        """Prefetch audio data in background."""
        if len(self.buffer) >= self.max_size:
            with self.lock:
                if self.buffer:
                    oldest = min(self.buffer.keys())
                    del self.buffer[oldest]

        self.executor.submit(self._fetch_audio, audio_data)

    def _fetch_audio(self, audio_data: AudioData):
        """Fetch and cache audio data."""
        if not audio_data.url:
            return

        try:
            response = requests.get(audio_data.url, timeout=10)
            response.raise_for_status()
            with self.lock:
                self.buffer[audio_data.id] = response.content
            logger.debug(f"Prefetched audio ID {audio_data.id}")
        except Exception as e:
            logger.warning(f"Failed to prefetch audio {audio_data.id}: {e}")

    def get(self, audio_id: int) -> Optional[bytes]:
        """Get cached audio data."""
        with self.lock:
            return self.buffer.get(audio_id)

    def clear(self):
        """Clear the buffer."""
        with self.lock:
            self.buffer.clear()

class EnhancedAudioStreamer:
    """Enhanced audio streaming with lower latency."""

    def __init__(self, volume: float = 1.0):
        self.volume = volume
        self.is_playing = False
        self._stop_event = threading.Event()

    def stream_audio_instant(self, audio_data: bytes) -> bool:
        """Stream audio with minimal latency."""
        try:
            self._stop_event.clear()
            # Try miniaudio first (lowest latency)
            if MINIAUDIO_AVAILABLE:
                return self._play_miniaudio(audio_data)

            # Fallback to pydub/sounddevice
            if PYDUB_AVAILABLE:
                return self._play_pydub(audio_data)

            logger.error("No audio backend available")
            return False

        except Exception as e:
            logger.error(f"Error streaming audio: {e}")
            return False

    def _play_miniaudio(self, audio_data: bytes) -> bool:
        """Play using miniaudio (low latency)."""
        try:
            # Decode to FLOAT32 for easier volume processing
            decoder = miniaudio.decode(audio_data, sample_format=miniaudio.SampleFormat.FLOAT32)

            # Convert to numpy array to apply volume
            samples = np.frombuffer(decoder.samples, dtype=np.float32)

            # Apply volume
            if self.volume != 1.0:
                samples = samples * self.volume

            # Convert back to bytes (miniaudio expects bytes or memoryview)
            # Note: samples is now a new array, so we can just pass it if miniaudio accepts array interface
            # or convert tobytes()

            with miniaudio.PlaybackDevice(
                output_format=miniaudio.SampleFormat.FLOAT32,
                nchannels=decoder.nchannels,
                sample_rate=decoder.sample_rate
            ) as device:
                self.is_playing = True
                device.start(samples)
                while device.callback_generator and not self._stop_event.is_set():
                    time.sleep(0.01)

            self.is_playing = False
            return True
        except Exception as e:
            logger.warning(f"Miniaudio playback failed: {e}")
            # Fallback to pydub if miniaudio fails
            if PYDUB_AVAILABLE:
                return self._play_pydub(audio_data)
            return False

    def _play_pydub(self, audio_data: bytes) -> bool:
        """Play using pydub/sounddevice."""
        try:
            audio = AudioSegment.from_mp3(io.BytesIO(audio_data))

            # Convert to numpy array
            samples = np.array(audio.get_array_of_samples())

            if audio.sample_width == 2:
                samples = samples.astype(np.float32) / 32768.0
            elif audio.sample_width == 1:
                samples = samples.astype(np.float32) / 128.0
            else:
                # Fallback for other bit depths
                pass # pydub usually handles 16 bit.

            # Reshape for channels
            if audio.channels == 2:
                samples = samples.reshape((-1, 2))

            # Apply volume
            samples = samples * self.volume

            self.is_playing = True
            # check stop event periodically? sd.play is blocking.
            # We can't easily interrupt sd.play(blocking=True) without a callback or async.
            # But for short audio clips it might be fine.
            sd.play(samples, samplerate=audio.frame_rate, blocking=True)
            self.is_playing = False
            return True

        except Exception as e:
            logger.error(f"Pydub playback failed: {e}")
            return False

    def stop(self):
        """Stop current playback."""
        self.is_playing = False
        self._stop_event.set()
        try:
            sd.stop()
        except:
            pass
