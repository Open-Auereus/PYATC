#!/usr/bin/env python3

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
from pydub import AudioSegment
import io
import json
from pathlib import Path
import subprocess
import shutil
import platform
from dotenv import load_dotenv

load_dotenv()
api_link = os.getenv("api_url")
try:
    import miniaudio  # Lightweight decoder/player, no external ffmpeg needed
    MINIAUDIO_AVAILABLE = True
except Exception:
    MINIAUDIO_AVAILABLE = False

# Load configuration
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

# Configure logging
logging.basicConfig(
    level=getattr(logging, CONFIG.get('logging', {}).get('default_level', 'INFO')),
    format=CONFIG.get('logging', {}).get('format', '%(asctime)s - %(levelname)s - %(message)s')
)
logger = logging.getLogger(__name__)

# Configure FFmpeg  likely deprecated soon with websockets
try:
    ffmpeg_cfg = CONFIG.get('ffmpeg', {}) if isinstance(CONFIG, dict) else {}
    ffmpeg_path = ffmpeg_cfg.get('ffmpeg_path')
    ffprobe_path = ffmpeg_cfg.get('ffprobe_path')
    if ffmpeg_path:
        AudioSegment.converter = ffmpeg_path
    if ffprobe_path:
        AudioSegment.ffprobe = ffprobe_path
except Exception as _e:
    # Non-fatal; pydub will fallback to PATH
    logger.debug(f"FFmpeg config not applied: {_e}")

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

class AudioStreamer:
    """Handles real-time audio streaming from URLs"""
    
    def __init__(self, volume: float = 1.0):
        self.volume = volume
        self.is_playing = False
        self.buffer_size = 1024  # kept for potential future chunking

    def stream_audio(self, audio_data: bytes):
        """Decode MP3 bytes to PCM and play."""
        # Prefer miniaudio if available (no external binaries required)
        if MINIAUDIO_AVAILABLE:
            try:
                decoder = miniaudio.Decoder(memory=audio_data)
                # Start a playback device using decoder's output format
                with miniaudio.PlaybackDevice(
                    output_format=decoder.output_format,
                    nchannels=decoder.nchannels,
                    sample_rate=decoder.sample_rate,
                ) as device:
                    self.is_playing = True
                    device.start(decoder)
                    # Block until playback finishes
                    while device.running and self.is_playing:
                        time.sleep(0.05)
                return
            except Exception as e:
                logger.warning(f"miniaudio playback failed, falling back to pydub: {e}")

        # Fallback: decode via pydub (requires ffmpeg) and play via sounddevice
        try:
            audio = AudioSegment.from_mp3(io.BytesIO(audio_data))
            samples = np.array(audio.get_array_of_samples())
            sample_width_bytes = audio.sample_width
            if samples.dtype.kind != "f":
                max_int = float(1 << (8 * sample_width_bytes - 1))
                samples = samples.astype(np.float32) / max_int
            else:
                samples = samples.astype(np.float32)
            samples = samples.reshape((-1, audio.channels))
            samples = np.clip(samples * self.volume, -1.0, 1.0)
            self.is_playing = True
            sd.play(samples, samplerate=audio.frame_rate)
            sd.wait()
        except (IOError, ValueError) as e:
            logger.error(f"Error streaming audio: {e}")
        finally:
            self.is_playing = False

    def stop(self):
        """Stop audio playback"""
        self.is_playing = False
        try:
            sd.stop()
        except Exception:
            pass

class LiveScanner:
    
    def __init__(self, 
                 api_base_url: str = None,
                 volume: float = None,
                 fetch_interval: int = None,
                 vfr_only: bool = None,
                 playback_delay: float = None,
                 geo_filter: bool = None,
                 airports: List[str] = None):
        """
        Initialize the live scanner
        
        Args:
            api_base_url: Base URL for the API (prod, dev, or local)
            volume: Audio volume (0.0 to 1.0)
            fetch_interval: How often to fetch new audio (seconds)
            vfr_only: Only play VFR traffic
            playback_delay: Delay between audio clips (seconds)
            geo_filter: Enable geographic filtering for Albuquerque ARTCC
            airports: List of specific airports to include (e.g. ['KTUS'])
        """
        defaults = CONFIG.get('default_settings', {})
        
        # Get API URL based on environment or use provided URL
        if api_base_url is None:
            api_env = defaults.get('api' ,'prod', "api_url")
            api_base_url = CONFIG.get('api_environments', {}).get(api_env, api_env)
            
        self.api_base_url = api_base_url
        self.volume = volume if volume is not None else defaults.get('volume', 0.7)
        self.fetch_interval = fetch_interval if fetch_interval is not None else defaults.get('fetch_interval', 20)
        self.vfr_only = vfr_only if vfr_only is not None else defaults.get('vfr_only', False)
        self.playback_delay = playback_delay if playback_delay is not None else defaults.get('playback_delay', 0.5)
        self.geo_filter = geo_filter if geo_filter is not None else defaults.get('geo_filter', False)
        self.airports = airports if airports is not None else defaults.get('airports', [])
        playback_cfg = CONFIG.get('playback', {}) if isinstance(CONFIG, dict) else {}
        # Choose backend: 'system' | 'miniaudio' | 'pydub'
        default_backend = 'system' if platform.system().lower().startswith('win') else ('miniaudio' if MINIAUDIO_AVAILABLE else 'pydub')
        self.playback_backend = playback_cfg.get('backend', default_backend)
        
        # Albuquerque ARTCC (ZAB) approximate bounds
        self.zab_bounds = CONFIG.get('zab_bounds', {
            'north': 37.0,  # Northern New Mexico
            'south': 31.0,  # Southern Arizona/New Mexico border
            'east': -103.0, # Eastern New Mexico
            'west': -114.0  # Western Arizona
        })
        
        # State management
        self.last_played_id = 0
        self.audio_queue = queue.Queue()
        self.is_running = False
        self.is_playing = False
        
        # Initialize audio streamer
        self.audio_streamer = AudioStreamer(volume=volume)
        
        #  pygame.mixer.music.load(temp_file)
        #     pygame.mixer.music.set_volume(self.volume)
        #     pygame.mixer.music.play()
            
        #     # Wait for playback to complete
        #     while pygame.mixer.music.get_busy() and self.is_running:
        #         time.sleep(0.1)

        
        self.fetch_thread = None
        self.play_thread = None
        
        logger.info(f"Scanner initialized with API: {self.api_base_url}")
    
    def fetch_audio_files(self) -> List[AudioData]:
        """Fetch new audio files from the API"""
        try:
            url = urljoin(self.api_base_url, f"/scanner/last?last={self.last_played_id}&limit=100")
            
            logger.debug(f"Fetching audio from: {url}")
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            audio_data_list = response.json()
            
            if not audio_data_list:
                logger.debug("No new audio data received")
                return []
            
            # Convert to AudioData objects
            audio_objects = []
            for item in audio_data_list:
                try:
                    audio_obj = AudioData(
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
                    audio_objects.append(audio_obj)
                except Exception as e:
                    logger.warning(f"Failed to parse audio item: {e}")
                    continue
            
            if audio_objects:
                self.last_played_id = audio_objects[-1].id
                logger.info(f"Fetched {len(audio_objects)} new audio files")
            
            return audio_objects
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch audio files: {e}")
            return []
        except (ValueError, TypeError) as e:
            logger.error(f"Unexpected error fetching audio: {e}")
            return []
    
    def reorder_audio_data(self, audio_list: List[AudioData]) -> List[AudioData]:

        if len(audio_list) <= 1:
            return audio_list
        
        reordered = audio_list.copy()
        
        i = 0
        while i < len(reordered) - 1:
            current_pilot = reordered[i].pilot
            
            # Look ahead for matching pilot (call/response)
            j = i + 1
            while j < len(reordered):
                if reordered[j].pilot == current_pilot:
                    # Move the matched item right after the current one
                    matched_item = reordered.pop(j)
                    reordered.insert(i + 1, matched_item)
                    i += 1  # Skip the newly inserted item
                    break
                j += 1
            i += 1
        
        return reordered
    
    def should_play_audio(self, audio: AudioData) -> bool:
        """Determine if audio should be played based on filters"""
        # VFR-only filter
        if self.vfr_only and audio.flight_rules != 'VFR':
            logger.debug(f"Skipping non-VFR audio: {audio.flight_rules}")
            return False
        
        # URL validation
        if not audio.url or not audio.url.startswith('http'):
            logger.warning(f"Invalid audio URL: {audio.url}")
            return False
            
        # Geographic filtering
        if self.geo_filter:
            # Check if audio is from a specific airport we're interested in
            if audio.airport in self.airports:
                return True
                
            # Check if coordinates are within Albuquerque ARTCC bounds
            if audio.lat is not None and audio.lon is not None:
                in_bounds = (
                    self.zab_bounds['south'] <= audio.lat <= self.zab_bounds['north'] and
                    self.zab_bounds['west'] <= audio.lon <= self.zab_bounds['east']
                )
                if not in_bounds:
                    logger.debug(f"Skipping audio outside ZAB bounds: {audio.lat}, {audio.lon}")
                    return False
            else:
               #Failback to airport ICAO code as a filter, as the map seem
                if audio.airport.startswith('K'):
                    if not any(audio.airport == airport for airport in self.airports):
                        logger.debug(f"Skipping audio from airport outside filter: {audio.airport}")
                        return False
        
        return True
    
    def play_audio_file(self, audio: AudioData) -> bool:
        # Experimental implementation of real time audio from mp3 to raw 
        try:
            if not self.should_play_audio(audio):
                return False
            # Logging output for troubleshooting
            logger.info(f"Playing audio ID {audio.id}: {audio.station_name} - {audio.pilot}")
            logger.debug(f"Audio URL: {audio.url}")

            # Display current transmission params
            print(f" LIVE TRANSMISSION")
            print(f"   Station: {audio.station_name}")
            print(f"   Frequency: {audio.frequency}")
            print(f"   From: {audio.who_from}")
            print(f"   Pilot: {audio.pilot}")
            print(f"   Airport: {audio.airport}")
            print(f"   Position: {audio.position}")
            if audio.lat and audio.lon:
                print(f"   Location: {audio.lat:.4f}, {audio.lon:.4f}")

            # If using system player backend, play the URL directly (no Python decode deps)
            if self.playback_backend == 'system':
                self._play_with_system_player(audio.url)
            else:
                # Download audio bytes and play via selected Python backend
                response = requests.get(audio.url, timeout=30)
                response.raise_for_status()
                audio_bytes = response.content
                self.audio_streamer.stream_audio(audio_bytes)

            return True

        except requests.RequestException as e:
            logger.error(f"Failed to download audio {audio.id}: {e}")
            return False
        except (IOError, ValueError) as e:
            logger.error(f"Failed to play audio {audio.id}: {e}")
            return False

    def _play_with_system_player(self, url: str) -> None:
        """Play an MP3 URL using system tools. Prefers ffplay if available; otherwise uses Windows Media Player via PowerShell on Windows."""
        # Try ffplay first if present
        ffplay_path = shutil.which('ffplay')
        if ffplay_path is not None:
            try:
                subprocess.run([ffplay_path, '-nodisp', '-autoexit', '-loglevel', 'error', url],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                return
            except Exception as e:
                logger.debug(f"ffplay failed, falling back: {e}")

        # Windows-specific fallback using WMP COM via PowerShell
        if platform.system().lower().startswith('win'):
            try:
                # Escape single quotes for PowerShell single-quoted string
                safe_url = url.replace("'", "''")
                ps_script = (
                    f"$wmp=New-Object -ComObject WMPlayer.OCX; "
                    f"$m=$wmp.newMedia('{safe_url}'); "
                    f"$wmp.currentPlaylist.Clear(); $wmp.currentPlaylist.appendItem($m); "
                    f"$wmp.controls.play(); "
                    f"while($wmp.playState -ne 1) {{ Start-Sleep -Milliseconds 100 }}; "
                    f"$wmp.close()"
                )
                subprocess.run(['powershell', '-NoProfile', '-Command', ps_script],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                return
            except Exception as e:
                logger.error(f"Windows Media Player playback failed: {e}")
        else:
            # Non-Windows: Try common CLI players if available
            for player_cmd in [['mpv', '--no-video', '--quiet', url], ['vlc', '--intf', 'dummy', '--play-and-exit', url], ['afplay', url]]:
                if shutil.which(player_cmd[0]):
                    try:
                        subprocess.run(player_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                        return
                    except Exception:
                        continue
        raise IOError('No system audio player available to play MP3 URL')
    
    def audio_player_worker(self):
        """Worker thread for playing audio from the queue"""
        logger.info("Audio player thread started")
        
        while self.is_running:
            try:
                # Get audio from queue (with timeout to allow checking is_running)
                try:
                    audio = self.audio_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                self.is_playing = True
                
                # Play the audio
                if self.play_audio_file(audio):
                    # Add delay between clips
                    if self.playback_delay > 0 and self.is_running:
                        time.sleep(self.playback_delay)
                
                self.is_playing = False
                self.audio_queue.task_done()
                
            except (IOError, ValueError) as e:
                logger.error(f"Error in audio player worker: {e}")
                self.is_playing = False
    
    def audio_fetcher_worker(self):
        logger.info("Audio fetcher thread started")
        
        while self.is_running:
            try:
                # Fetch new audio
                audio_list = self.fetch_audio_files()
                
                if audio_list:
                    # Reorder for better call/response flow
                    audio_list = self.reorder_audio_data(audio_list)
                    
                    for audio in audio_list:
                        if self.is_running:
                            self.audio_queue.put(audio)
                    
                    logger.info(f"Added {len(audio_list)} audio files to queue")
                
                # Wait before next fetch
                for _ in range(self.fetch_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
                    
            except (IOError, ValueError) as e:
                logger.error(f"Error in audio fetcher worker: {e}")
                time.sleep(5)  # Wait a bit before retrying
    
    def start(self):
        if self.is_running:
            logger.warning("Scanner is already running")
            return
        
        logger.info("Starting live scanner...")
        self.is_running = True
        
        self.fetch_thread = threading.Thread(target=self.audio_fetcher_worker, daemon=True)
        self.play_thread = threading.Thread(target=self.audio_player_worker, daemon=True)
        
        self.fetch_thread.start()
        self.play_thread.start()
        
        logger.info(" Live scanner is now running")
        
        try:
            audio_list = self.fetch_audio_files()
            if audio_list:
                audio_list = self.reorder_audio_data(audio_list)
                for audio in audio_list:
                    self.audio_queue.put(audio)
                logger.info(f"Initial load: {len(audio_list)} audio files queued")
        except (IOError, ValueError) as e:
            logger.error(f"Failed initial audio fetch: {e}")
    
    def stop(self):
        if not self.is_running:
            return
        
        logger.info("Stopping live scanner...")
        self.is_running = False
        
        self.audio_streamer.stop()
        
        if self.fetch_thread and self.fetch_thread.is_alive():
            self.fetch_thread.join(timeout=2)
        if self.play_thread and self.play_thread.is_alive():
            self.play_thread.join(timeout=2)
        
        logger.info("Live scanner stopped")
    
    def get_status(self) -> Dict:
        return {
            "running": self.is_running,
            "playing": self.is_playing,
            "queue_size": self.audio_queue.qsize(),
            "last_played_id": self.last_played_id,
            "api_base_url": self.api_base_url,
            "vfr_only": self.vfr_only,
            "volume": self.volume
        }

def main():
    parser = argparse.ArgumentParser(description="Live Aviation Scanner")
    parser.add_argument("--config", type=str, default="config.json",
                       help="Path to configuration file")
    parser.add_argument("--api", choices=["prod", "dev", "local"],
                       help="API environment to use (overrides config)")
    parser.add_argument("--volume", type=float,
                       help="Audio volume (0.0 to 1.0) (overrides config)")
    parser.add_argument("--interval", type=int,
                       help="Fetch interval in seconds (overrides config)")
    parser.add_argument("--vfr-only", action="store_true",
                       help="Only play VFR traffic (overrides config)")
    parser.add_argument("--delay", type=float,
                       help="Delay between audio clips in seconds (overrides config)")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug logging (overrides config)")
    parser.add_argument("--geo-filter", action="store_true",
                       help="Enable geographic filtering for Albuquerque ARTCC zone (overrides config)")
    parser.add_argument("--airports", type=str, nargs="+",
                       help="List of airports to include e.g. KTUS KABQ (overrides config)")
    
    args = parser.parse_args()
    
    # Load config from specified file
    global CONFIG
    CONFIG = load_config(args.config)
    
    # Override config with command line arguments if provided
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get API URL based on environment
    api_url = None
    if args.api:
        api_url = CONFIG.get('api_environments', {}).get(args.api)
    
    # Create scanner with command line arguments overriding config values
    scanner = LiveScanner(
        api_base_url=api_url,
        volume=args.volume,
        fetch_interval=args.interval,
        vfr_only=args.vfr_only if args.vfr_only else None,
        playback_delay=args.delay,
        geo_filter=args.geo_filter if args.geo_filter else None,
        airports=args.airports
    )
    
    try:
        scanner.start()
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\nReceived interrupt signal...")
    except (IOError, ValueError) as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        scanner.stop()
        print("Scanner stopped. Goodbye!")

if __name__ == "__main__":
    main()