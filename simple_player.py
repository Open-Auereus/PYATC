#!/usr/bin/env python3
"""
simple_player.py

Minimal helper to download an MP3 URL and play it with pydub+sounddevice.
If those packages are not available or playback fails, it falls back to saving
the MP3 to a temporary file and opening it with the OS default application.

Usage:
    py simple_player.py --url <MP3_URL>

Requirements (recommended): `pydub`, `sounddevice`, `requests`, `numpy`.
"""
from __future__ import annotations

import argparse
import io
import logging
import os
import subprocess
import sys
import tempfile

import requests

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except Exception:
    PYDUB_AVAILABLE = False

try:
    import sounddevice as sd
    SD_AVAILABLE = True
except Exception:
    SD_AVAILABLE = False

import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def play_bytes_with_pydub_sounddevice(mp3_bytes: bytes, volume: float = 1.0) -> None:
    """Decode MP3 bytes with pydub and play with sounddevice (blocking).

    This is intentionally small and robust: it converts samples to float32
    and applies volume before calling `sd.play(..., blocking=True)`.
    """
    audio = AudioSegment.from_file(io.BytesIO(mp3_bytes), format='mp3')

    samples = np.array(audio.get_array_of_samples())

    # Convert integer PCM to float32 in range -1.0..1.0
    if audio.sample_width == 2:
        samples = samples.astype(np.float32) / 32768.0
    elif audio.sample_width == 4:
        samples = samples.astype(np.float32) / 2147483648.0
    else:
        # fallback normalization for other widths
        samples = samples.astype(np.float32)

    # Reshape for multiple channels
    if audio.channels > 1:
        try:
            samples = samples.reshape((-1, audio.channels))
        except Exception:
            logger.debug("Could not reshape samples for channels; proceeding with raw array")

    # Apply volume safely
    samples = samples * float(volume)

    # Play blocking
    sd.play(samples, samplerate=audio.frame_rate, blocking=True)


def fallback_open(mp3_bytes: bytes) -> None:
    """Save bytes to a temp file and open with the OS default application."""
    fd, path = tempfile.mkstemp(suffix='.mp3')
    os.close(fd)
    with open(path, 'wb') as f:
        f.write(mp3_bytes)

    logger.info("Saved temporary MP3 to: %s", path)

    try:
        if sys.platform.startswith('win'):
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == 'darwin':
            subprocess.run(['open', path], check=False)
        else:
            subprocess.run(['xdg-open', path], check=False)
    except Exception as e:
        logger.error("Failed to open file with default application: %s", e)


def play_url(url: str, volume: float = 1.0, no_fallback: bool = False) -> None:
    """Download URL and attempt playback with best available method."""
    logger.info("Downloading: %s", url)
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.content

    # Try pydub + sounddevice first
    if PYDUB_AVAILABLE and SD_AVAILABLE:
        try:
            play_bytes_with_pydub_sounddevice(data, volume=volume)
            return
        except Exception as e:
            logger.warning("pydub+sounddevice playback failed: %s", e)

    # If pydub is available but sounddevice is not, we still fallback to OS player
    if not no_fallback:
        logger.info("Falling back to opening the MP3 in the default application")
        fallback_open(data)
    else:
        logger.error("No available playback method and fallback disabled")


def main() -> None:
    parser = argparse.ArgumentParser(description='Simple MP3 URL player')
    parser.add_argument('--url', '-u', required=True, help='MP3 file URL')
    parser.add_argument('--volume', '-v', type=float, default=1.0, help='Playback volume (0.0-2.0)')
    parser.add_argument('--no-fallback', action='store_true', help='Do not open file with OS fallback')
    args = parser.parse_args()

    try:
        play_url(args.url, volume=args.volume, no_fallback=args.no_fallback)
    except Exception as e:
        logger.exception('Playback failed: %s', e)


if __name__ == '__main__':
    main()
