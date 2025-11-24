"""
Core scanner logic using asyncio.
"""
import asyncio
import json
import logging
import time
from typing import List, Optional, Callable
from urllib.parse import urljoin

import aiohttp
import websockets
from rich.console import Console

from .audio import AudioBuffer, EnhancedAudioStreamer, AudioData
from .config import config

logger = logging.getLogger(__name__)

class RealtimeScanner:
    """Enhanced scanner with real-time capabilities using asyncio."""

    def __init__(self,
                 api_base_url: str = None,
                 volume: float = 0.7,
                 fetch_interval: int = 3,
                 use_websocket: bool = True,
                 prefetch_audio: bool = True,
                 vfr_only: bool = False,
                 geo_filter: bool = False,
                 airports: List[str] = None,
                 on_audio_start: Optional[Callable[[AudioData], None]] = None,
                 on_status_update: Optional[Callable[[str], None]] = None):

        self.api_base_url = api_base_url or config.api_url
        self.ws_url = config.ws_url
        self.volume = volume
        self.fetch_interval = fetch_interval
        self.use_websocket = use_websocket
        self.prefetch_audio = prefetch_audio
        self.vfr_only = vfr_only
        self.geo_filter = geo_filter
        self.airports = airports or []

        self.on_audio_start = on_audio_start
        self.on_status_update = on_status_update

        # Audio components
        self.audio_streamer = EnhancedAudioStreamer(volume=volume)
        self.audio_buffer = AudioBuffer() if prefetch_audio else None

        # Async Queue
        self.audio_queue = asyncio.PriorityQueue()

        # State
        self.last_played_id = 0
        self.is_running = False
        self.ws_connected = False
        self.session: Optional[aiohttp.ClientSession] = None

        # Geographic bounds (Albuquerque ARTCC defaults)
        self.zab_bounds = config.get('zab_bounds', {
            'north': 37.0,
            'south': 31.0,
            'east': -103.0,
            'west': -114.0
        })

    async def start(self):
        """Start the scanner."""
        if self.is_running:
            return

        self.is_running = True
        self.session = aiohttp.ClientSession()

        if self.on_status_update:
            self.on_status_update("Starting scanner...")

        # Initial fetch to populate history/context
        initial_audio = await self.fetch_audio_batch()
        for audio in initial_audio:
            await self.audio_queue.put((1, time.time(), audio))
            if self.audio_buffer:
                self.audio_buffer.prefetch(audio)

        # Use TaskGroup for structured concurrency (Python 3.11+)
        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(self.audio_player_worker())
                tg.create_task(self.audio_fetcher_worker())
                if self.use_websocket and self.ws_url:
                     tg.create_task(self.websocket_worker())
        except Exception as e:
            logger.error(f"Scanner crashed: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources."""
        self.is_running = False
        if self.session:
            await self.session.close()
        self.audio_streamer.stop()
        if self.on_status_update:
            self.on_status_update("Scanner stopped.")

    async def _parse_audio_data(self, item: dict) -> Optional[AudioData]:
        """Parse API response to AudioData object."""
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

    async def fetch_audio_batch(self) -> List[AudioData]:
        """Fetch audio via REST API."""
        if not self.session:
            return []

        try:
            url = urljoin(self.api_base_url, f"/scanner/last?last={self.last_played_id}&limit=50")
            async with self.session.get(url, timeout=10) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch audio: Status {response.status}")
                    return []

                data = await response.json()

            audio_list = []
            for item in data:
                audio_obj = await self._parse_audio_data(item)
                if audio_obj:
                    audio_list.append(audio_obj)

            if audio_list:
                self.last_played_id = max(a.id for a in audio_list)
                logger.info(f"Fetched {len(audio_list)} audio files via REST")

            return audio_list

        except Exception as e:
            logger.error(f"Failed to fetch audio: {e}")
            return []

    def should_play_audio(self, audio: AudioData) -> bool:
        """Apply filters to audio."""
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

    async def play_audio(self, audio: AudioData) -> bool:
        """Play audio."""
        if not self.should_play_audio(audio):
            return False

        if self.on_audio_start:
            self.on_audio_start(audio)

        # Try buffer first
        audio_bytes = None
        if self.audio_buffer:
            audio_bytes = self.audio_buffer.get(audio.id)

        # Fetch if not in buffer
        if not audio_bytes and self.session:
            try:
                async with self.session.get(audio.url, timeout=10) as response:
                    if response.status == 200:
                        audio_bytes = await response.read()
            except Exception as e:
                logger.error(f"Failed to download audio: {e}")

        if audio_bytes:
            # Run blocking audio playback in a separate thread
            # loop.run_in_executor is suitable for this
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, self.audio_streamer.stream_audio_instant, audio_bytes)

        return False

    async def audio_player_worker(self):
        """Worker to play audio from the queue."""
        logger.info("Audio player started")
        while self.is_running:
            try:
                priority, timestamp, audio = await self.audio_queue.get()

                await self.play_audio(audio)

                self.audio_queue.task_done()

                # Small delay to prevent overlapping too much if latency is high
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Player error: {e}")

    async def audio_fetcher_worker(self):
        """Worker to fetch audio via REST (fallback/supplement to WebSocket)."""
        logger.info("REST fetcher started")
        while self.is_running:
            try:
                # If WebSocket is connected, we might want to fetch less often or not at all
                # But keeping it as a backup or for missed messages is good practice.
                # For now, we'll fetch if WS is not active or periodically.

                if not self.ws_connected:
                    audio_list = await self.fetch_audio_batch()

                    for audio in audio_list:
                        await self.audio_queue.put((1, time.time(), audio))
                        if self.audio_buffer:
                            self.audio_buffer.prefetch(audio)

                await asyncio.sleep(self.fetch_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Fetcher error: {e}")
                await asyncio.sleep(5)

    async def websocket_worker(self):
        """Worker to handle WebSocket connection."""
        if not self.ws_url:
            logger.warning("No WebSocket URL configured")
            return

        logger.info(f"Connecting to WebSocket: {self.ws_url}")

        while self.is_running:
            try:
                async with websockets.connect(self.ws_url) as ws:
                    self.ws_connected = True
                    if self.on_status_update:
                        self.on_status_update("WebSocket Connected")

                    # Send subscription message
                    await ws.send(json.dumps({
                        'type': 'subscribe',
                        'last_id': self.last_played_id,
                        'filters': {
                            'vfr_only': self.vfr_only,
                            'airports': self.airports
                        }
                    }))

                    async for message in ws:
                        try:
                            data = json.loads(message)
                            if data.get('type') == 'audio':
                                audio_obj = await self._parse_audio_data(data.get('data', {}))
                                if audio_obj:
                                    # Add with high priority (0)
                                    await self.audio_queue.put((0, time.time(), audio_obj))
                                    if self.audio_buffer:
                                        self.audio_buffer.prefetch(audio_obj)
                                    logger.debug(f"Received real-time audio ID {audio_obj.id}")
                        except json.JSONDecodeError:
                            pass

            except Exception as e:
                self.ws_connected = False
                if self.on_status_update:
                    self.on_status_update(f"WebSocket Disconnected: {e}")
                logger.error(f"WebSocket error: {e}")
                await asyncio.sleep(5) # Reconnect delay
            finally:
                self.ws_connected = False
