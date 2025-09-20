#!/usr/bin/env python3

"""
Enhanced Real-Time Aviation Scanner with WebSocket support
Provides lower latency audio streaming and optional WebSocket connections
"""

import os
import requests
import time
import threading
import queue
import argparse
from typing import Dict, List, Optional
from dataclasses import dataclass
from urllib.parse import urljoin
import logging
import sounddevice as sd
import numpy as np
import io
import json
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import dependencies.deps as deps 

load_dotenv()
API_URL = os.getenv("API_URL", os.getenv("URL"))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from JSON file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"Config file {config_path} not found, using defaults")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing config file: {e}")
        return {}


CONFIG = load_config()


@dataclass
class AudioData:
    """Represents an audio transmission"""
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
    priority: int = 0  # For priority queue handling


class AudioBuffer:
    """Manages pre-fetched audio data for instant playback"""

    def __init__(self, max_size: int = 10):
        self.buffer = {}
        self.max_size = max_size
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.lock = threading.Lock()

    def prefetch(self, audio_data: AudioData):
        """Prefetch audio data in background"""
        if len(self.buffer) >= self.max_size:
            # Remove oldest entry
            with self.lock:
                if self.buffer:
                    oldest = min(self.buffer.keys())
                    del self.buffer[oldest]

        self.executor.submit(self._fetch_audio, audio_data)

    def _fetch_audio(self, audio_data: AudioData):
        """Fetch and cache audio data"""
        try:
            response = requests.get(audio_data.url, timeout=10)
            response.raise_for_status()
            with self.lock:
                self.buffer[audio_data.id] = response.content
            logger.debug(f"Prefetched audio ID {audio_data.id}")
        except Exception as e:
            logger.warning(f"Failed to prefetch audio {audio_data.id}: {e}")

    def get(self, audio_id: int) -> Optional[bytes]:
        """Get cached audio data"""
        with self.lock:
            return self.buffer.get(audio_id)

    def clear(self):
        """Clear the buffer"""
        with self.lock:
            self.buffer.clear()


class EnhancedAudioStreamer:
    """Enhanced audio streaming with lower latency"""

    def __init__(self, volume: float = 1.0):
        self.volume = volume
        self.is_playing = False
        self.current_stream = None

    def stream_audio_instant(self, audio_data: bytes) -> bool:
        """Stream audio with minimal latency"""
        try:
            # Try miniaudio first (lowest latency)
            if deps.miniaudio:
                return self._play_miniaudio(audio_data)

            # Fallback to pydub/sounddevice
            if deps.pydub:
                return self._play_pydub(audio_data)

            logger.error("No audio backend available")
            return False

        except Exception as e:
            logger.error(f"Error streaming audio: {e}")
            return False

    def _play_miniaudio(self, audio_data: bytes) -> bool:
        """Play using miniaudio (low latency)"""
        try:
            decoder = deps.miniaudio.decode(audio_data)
            samples = decoder.samples

            # Apply volume
            samples = samples * self.volume

            with deps.miniaudio.PlaybackDevice(
                output_format=deps.miniaudio.SampleFormat.FLOAT32,
                nchannels=decoder.nchannels,
                sample_rate=decoder.sample_rate
            ) as device:
                self.is_playing = True
                device.start(samples)
                while device.callback_generator:
                    time.sleep(0.01)

            self.is_playing = False
            return True
        except Exception as e:
            logger.warning(f"Miniaudio playback failed: {e}")
            return False

    def _play_pydub(self, audio_data: bytes) -> bool:
        
        try:
            audio = deps.audios.from_mp3(io.BytesIO(audio_data))

            # Convert to numpy array
            samples = np.array(audio.get_array_of_samples())

            if audio.sample_width == 2:
                samples = samples.astype(np.float32) / 32768.0
            else:
                samples = samples.astype(np.float32) / 128.0

            # Reshape for channels
            if audio.channels == 2:
                samples = samples.reshape((-1, 2))

            # Apply volume
            samples = samples * self.volume

            self.is_playing = True
            sd.play(samples, samplerate=audio.frame_rate, blocking=True)
            self.is_playing = False
            return True

        except Exception as e:
            logger.error(f"Pydub playback failed: {e}")
            return False

    def stop(self):
        """Stop current playback"""
        self.is_playing = False
        try:
            sd.stop()
        except:
            pass


class RealtimeScanner:
    """Enhanced scanner with real-time capabilities"""

    def __init__(self,
                 api_base_url: str = None,
                 volume: float = 0.7,
                 fetch_interval: int = 3,
                 use_websocket: bool = True,
                 prefetch_audio: bool = True,
                 vfr_only: bool = False,
                 geo_filter: bool = False,
                 airports: List[str] = None):

        self.api_base_url = api_base_url or API_URL
        self.volume = volume
        self.fetch_interval = fetch_interval
        self.use_websocket = use_websocket and deps.websocket
        self.prefetch_audio = prefetch_audio
        self.vfr_only = vfr_only
        self.geo_filter = geo_filter
        self.airports = airports or []

        # Audio components
        self.audio_streamer = EnhancedAudioStreamer(volume=volume)
        self.audio_buffer = AudioBuffer() if prefetch_audio else None

        # Queue with priority support
        self.audio_queue = queue.PriorityQueue()

        # State
        self.last_played_id = 0
        self.is_running = False
        self.ws = None

        # Geographic bounds (Albuquerque ARTCC)
        self.zab_bounds = CONFIG.get('zab_bounds', {
            'north': 37.0,
            'south': 31.0,
            'east': -103.0,
            'west': -114.0
        })

        # Threads
        self.fetch_thread = None
        self.play_thread = None

        logger.info(f"Realtime Scanner initialized - WebSocket: {self.use_websocket}, Prefetch: {self.prefetch_audio}")

    # def connect_websocket(self):
    #
    #     if not self.use_websocket:
    #         return

    #     ws_url = WS_URL.replace("https://", "wss://").replace("http://", "ws://")

        # def on_message(message):
        #     try:
        #         data = json.loads(message)
        #         if data.get('type') == 'audio':
        #             audio_obj = self._parse_audio_data(data.get('data', {}))
        #             if audio_obj:
        #                 # Add with high priority for real-time data
        #                 self.audio_queue.put((0, time.time(), audio_obj))
        #                 if self.audio_buffer:
        #                     self.audio_buffer.prefetch(audio_obj)
        #                 logger.debug(f"Received real-time audio ID {audio_obj.id}")
        #     except Exception as e:
        #         logger.error(f"WebSocket message error: {e}")

        # def on_error(ws, error):
        #     logger.error(f"WebSocket error: {error}")

        # def on_close(ws, close_status_code, close_msg):
        #     logger.info("WebSocket closed")
        #     if self.is_running:
        #         time.sleep(5)
        #         self.connect_websocket()  # Reconnect

        # def on_open(ws):
        #     logger.info("WebSocket connected")
        #     # Send subscription message
        #     ws.send(json.dumps({
        #         'type': 'subscribe',
        #         'last_id': self.last_played_id,
        #         'filters': {
        #             'vfr_only': self.vfr_only,
        #             'airports': self.airports
        #         }
        #     }))

        # try:
        #     self.ws = websocket.WebSocketApp(ws_url,
        #                                     on_open=on_open,
        #                                     on_message=on_message,
        #                                     on_error=on_error,
        #                                     on_close=on_close)

            # Run in background thread
        #     ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        #     ws_thread.start()
        # except Exception as e:
        #     logger.error(f"Failed to connect WebSocket: {e}")
        #     self.use_websocket = False

    def _parse_audio_data(self, item: dict) -> Optional[AudioData]:
        try:
            return AudioData(
                id=item.get('id', 0),
                url=item.get('url', ''),
                who_from=item.get('who_from', '-'),
                frequency=item.get('frequency', '-'),
                station_name=item.get('station_name', '-'),
                pilot=f"[{item.get('flight_rules', 'UNK')}] {item.get('pilot', '-')}",
                airport=item.get('airport', '-'),
                position=item.get('position', '-'),
                voice_name=item.get('voice_name', '-'),
                from_userid=item.get('from_userid', '-'),
                flight_rules=item.get('flight_rules', 'UNK'),
                lat=item.get('lat'),
                lon=item.get('lon'),
                stamp=item.get('stamp')
            )
        except Exception as e:
            logger.warning(f"Failed to parse audio item: {e}")
            return None

    def fetch_audio_batch(self) -> List[AudioData]:
        try:
            url = urljoin(self.api_base_url, f"/scanner/last?last={self.last_played_id}&limit=50")
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            audio_list = []
            for item in response.json():
                audio_obj = self._parse_audio_data(item)
                if audio_obj:
                    audio_list.append(audio_obj)

            if audio_list:
                self.last_played_id = max(a.id for a in audio_list)
                logger.info(f"Fetched {len(audio_list)} audio files")

            return audio_list

        except Exception as e:
            logger.error(f"Failed to fetch audio: {e}")
            return []

    def should_play_audio(self, audio: AudioData) -> bool:
        """Apply filters to audio"""
        if self.vfr_only and audio.flight_rules != 'VFR':
            return False

        if not audio.url or not audio.url.startswith('http'):
            return False

        if self.geo_filter:
            if audio.airport in self.airports:
                return True

            if audio.lat and audio.lon:
                in_bounds = (
                    self.zab_bounds['south'] <= audio.lat <= self.zab_bounds['north'] and
                    self.zab_bounds['west'] <= audio.lon <= self.zab_bounds['east']
                )
                if not in_bounds:
                    return False

        return True

    def play_audio(self, audio: AudioData) -> bool:
        """Play audio with minimal latency"""
        try:
            if not self.should_play_audio(audio):
                return False

            # Display transmission info
            print(f"   LIVE TRANSMISSION")
            print(f"   Station: {audio.station_name}")
            print(f"   Frequency: {audio.frequency}")
            print(f"   Pilot: {audio.pilot}")
            print(f"   Airport: {audio.airport}")
            if audio.lat and audio.lon:
                print(f"   Location: {audio.lat:.4f}, {audio.lon:.4f}")

            # Try buffer first
            audio_bytes = None
            if self.audio_buffer:
                audio_bytes = self.audio_buffer.get(audio.id)

            # Fetch if not in buffer
            if not audio_bytes:
                response = requests.get(audio.url, timeout=10)
                response.raise_for_status()
                audio_bytes = response.content

            
            return self.audio_streamer.stream_audio_instant(audio_bytes)

        except Exception as e:
            logger.error(f"Failed to play audio {audio.id}: {e}")
            return False

    def audio_player_worker(self):
        logger.info("Audio player started")

        while self.is_running:
            try:
                # Get from priority queue (timeout for checking is_running)
                try:
                    priority, timestamp, audio = self.audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                # Play the audio
                if self.play_audio(audio):
                    # Small delay between transmissions
                    time.sleep(0.1)

                self.audio_queue.task_done()

            except Exception as e:
                logger.error(f"Player error: {e}")

    def audio_fetcher_worker(self):
        """Worker thread for REST API fetching"""
        logger.info("REST fetcher started")

        while self.is_running:
            try:
                if not self.use_websocket or not self.ws:
                    # Fetch via REST API
                    audio_list = self.fetch_audio_batch()

                    for audio in audio_list:
                        # Add with normal priority
                        self.audio_queue.put((1, time.time(), audio))

                        # Prefetch if enabled
                        if self.audio_buffer:
                            self.audio_buffer.prefetch(audio)

                # Wait before next fetch
                time.sleep(self.fetch_interval)

            except Exception as e:
                logger.error(f"Fetcher error: {e}")
                time.sleep(5)

    def start(self):
        """Start the scanner"""
        if self.is_running:
            return

        logger.info("Starting Realtime Scanner...")
        self.is_running = True

        # Connect WebSocket if enabled
        # if self.use_websocket:
        #     self.connect_websocket()

        # Start worker threads
        self.play_thread = threading.Thread(target=self.audio_player_worker, daemon=True)
        self.fetch_thread = threading.Thread(target=self.audio_fetcher_worker, daemon=True)

        self.play_thread.start()
        self.fetch_thread.start()

        # Initial fetch
        initial_audio = self.fetch_audio_batch()
        for audio in initial_audio:
            self.audio_queue.put((1, time.time(), audio))
            if self.audio_buffer:
                self.audio_buffer.prefetch(audio)

        logger.info("✈️  Scanner is running!")

    def stop(self):
        """Stop the scanner"""
        logger.info("Stopping scanner...")
        self.is_running = False

        if self.ws:
            self.ws.close()

        if self.audio_buffer:
            self.audio_buffer.clear()

        self.audio_streamer.stop()

        if self.play_thread:
            self.play_thread.join(timeout=2)
        if self.fetch_thread:
            self.fetch_thread.join(timeout=2)

        logger.info("Scanner stopped")

    def get_status(self) -> Dict:
        return {
            "running": self.is_running,
            "playing": self.audio_streamer.is_playing,
            "queue_size": self.audio_queue.qsize(),
            "last_played_id": self.last_played_id,
            "websocket": "connected" if self.ws else "disconnected",
            "prefetch": self.prefetch_audio,
            "buffer_size": len(self.audio_buffer.buffer) if self.audio_buffer else 0
        }


def main():
    parser = argparse.ArgumentParser(description="Real-Time Aviation Scanner")
    parser.add_argument("--api", type=str, help="API base URL")
    parser.add_argument("--volume", type=float, default=0.7, help="Volume (0.0-1.0)")
    parser.add_argument("--interval", type=int, default=3, help="Fetch interval (seconds)")
    parser.add_argument("--no-websocket", action="store_true", help="Disable WebSocket")
    parser.add_argument("--no-prefetch", action="store_true", help="Disable audio prefetching")
    parser.add_argument("--vfr-only", action="store_true", help="Only play VFR traffic")
    parser.add_argument("--geo-filter", action="store_true", help="Enable geographic filtering")
    parser.add_argument("--airports", nargs="+", help="Filter by airports (e.g. KTUS KABQ)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create scanner
    scanner = RealtimeScanner(
        api_base_url=args.api,
        volume=args.volume,
        fetch_interval=args.interval,
        use_websocket=not args.no_websocket,
        prefetch_audio=not args.no_prefetch,
        vfr_only=args.vfr_only,
        geo_filter=args.geo_filter,
        airports=args.airports
    )

    try:
        scanner.start()

        print("\n✈️  Real-Time Aviation Scanner")
        print("=" * 40)
        print(f"API: {scanner.api_base_url}")
        print(f"WebSocket: {'Enabled' if scanner.use_websocket else 'Disabled'}")
        print(f"Prefetch: {'Enabled' if scanner.prefetch_audio else 'Disabled'}")
        print(f"Volume: {scanner.volume}")
        print("\nPress Ctrl+C to stop\n")

        # Keep running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nShutting down...")
    finally:
        scanner.stop()
        print("Goodbye!")


if __name__ == "__main__":
    main()