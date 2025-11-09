import os
import time
import requests
import threading
import queue
import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from urllib.parse import urljoin
from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class AudioData:
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

    def to_dict(self):
        return asdict(self)


class ScannerService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'initialized'):
            return

        self.initialized = True
        self.api_base_url = settings.API_URL
        self.is_running = False
        self.last_played_id = 0
        self.audio_queue = queue.Queue()
        self.fetch_thread = None
        self.current_settings = self._load_default_settings()
        self.listeners = []

        with open('config.json', 'r') as f:
            config = json.load(f)
        self.zab_bounds = config.get('zab_bounds', {
            'north': 37.0,
            'south': 31.0,
            'east': -103.0,
            'west': -114.0
        })

    def _load_default_settings(self):
        with open('config.json', 'r') as f:
            config = json.load(f)
        return config.get('default_settings', {})

    def add_listener(self, callback):
        self.listeners.append(callback)

    def remove_listener(self, callback):
        if callback in self.listeners:
            self.listeners.remove(callback)

    def _notify_listeners(self, event_type: str, data: dict):
        for listener in self.listeners:
            try:
                listener(event_type, data)
            except Exception as e:
                logger.error(f"Error notifying listener: {e}")

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
        vfr_only = self.current_settings.get('vfr_only', False)
        geo_filter = self.current_settings.get('geo_filter', False)
        airports = self.current_settings.get('airports', [])

        if vfr_only and audio.flight_rules != 'VFR':
            return False

        if not audio.url or not audio.url.startswith('http'):
            return False

        if geo_filter:
            if audio.airport in airports:
                return True

            if audio.lat and audio.lon:
                in_bounds = (
                    self.zab_bounds['south'] <= audio.lat <= self.zab_bounds['north'] and
                    self.zab_bounds['west'] <= audio.lon <= self.zab_bounds['east']
                )
                if not in_bounds:
                    return False

        return True

    def fetcher_worker(self):
        logger.info("Fetcher started")
        fetch_interval = self.current_settings.get('fetch_interval', 20)

        while self.is_running:
            try:
                audio_list = self.fetch_audio_batch()

                for audio in audio_list:
                    if self.should_play_audio(audio):
                        self.audio_queue.put(audio)
                        self._notify_listeners('new_transmission', audio.to_dict())

                time.sleep(fetch_interval)

            except Exception as e:
                logger.error(f"Fetcher error: {e}")
                time.sleep(5)

    def start(self, settings: dict = None):
        if self.is_running:
            return {"status": "already_running"}

        if settings:
            self.current_settings.update(settings)

        logger.info("Starting Scanner Service...")
        self.is_running = True

        self.fetch_thread = threading.Thread(target=self.fetcher_worker, daemon=True)
        self.fetch_thread.start()

        initial_audio = self.fetch_audio_batch()
        for audio in initial_audio:
            if self.should_play_audio(audio):
                self.audio_queue.put(audio)
                self._notify_listeners('new_transmission', audio.to_dict())

        logger.info("Scanner Service is running!")
        self._notify_listeners('scanner_started', {'settings': self.current_settings})
        return {"status": "started", "settings": self.current_settings}

    def stop(self):
        if not self.is_running:
            return {"status": "not_running"}

        logger.info("Stopping Scanner Service...")
        self.is_running = False

        if self.fetch_thread:
            self.fetch_thread.join(timeout=2)

        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        logger.info("Scanner Service stopped")
        self._notify_listeners('scanner_stopped', {})
        return {"status": "stopped"}

    def get_status(self) -> Dict:
        return {
            "running": self.is_running,
            "queue_size": self.audio_queue.qsize(),
            "last_played_id": self.last_played_id,
            "settings": self.current_settings
        }

    def get_next_audio(self) -> Optional[AudioData]:
        try:
            return self.audio_queue.get_nowait()
        except queue.Empty:
            return None

    def update_settings(self, settings: dict):
        self.current_settings.update(settings)
        self._notify_listeners('settings_updated', {'settings': self.current_settings})
        return {"status": "updated", "settings": self.current_settings}
