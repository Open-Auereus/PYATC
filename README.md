# PYATC - Real-Time Aviation Scanner

A Python-based real-time aviation scanner that streams ATC (Air Traffic Control) audio transmissions.

## Features

- Real-time audio streaming via REST API polling
- Audio prefetching for smooth playback
- Geographic filtering by ARTCC bounds
- Airport-based filtering
- VFR/IFR traffic filtering
- Configurable volume and fetch intervals

## Requirements

- Python 3.8+
- FFmpeg (required for audio processing)
- PortAudio (required for audio playback)

## Installation

### 1. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg portaudio19-dev
```

**macOS:**
```bash
brew install ffmpeg portaudio
```

**Windows:**
- Download FFmpeg from https://ffmpeg.org/download.html
- PortAudio should be installed automatically with Python dependencies

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Copy the example environment file and configure your API URL:
```bash
cp .env.example .env
```

Edit `.env` and set your API URL:
```
api_url=https://your-api-url.com
```

## Usage

### Basic Usage

```bash
python scanner_live.py --api https://your-api-url.com
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--api` | API base URL | Environment variable `API_URL` |
| `--volume` | Volume level (0.0-1.0) | 0.7 |
| `--interval` | Fetch interval in seconds | 3 |
| `--no-prefetch` | Disable audio prefetching | Enabled |
| `--vfr-only` | Only play VFR traffic | All traffic |
| `--geo-filter` | Enable geographic filtering | Disabled |
| `--airports` | Filter by airports (e.g., KTUS KABQ) | All airports |
| `--debug` | Enable debug logging | Disabled |

### Examples

```bash
# Basic usage with custom API
python scanner_live.py --api https://api.example.com

# Lower volume and longer fetch interval
python scanner_live.py --volume 0.5 --interval 5

# VFR traffic only at specific airports
python scanner_live.py --vfr-only --airports KTUS KABQ KPHX

# Debug mode
python scanner_live.py --debug
```

## Configuration

The `config.json` file allows customization of various settings:

```json
{
    "default_settings": {
        "volume": 0.7,
        "fetch_interval": 20,
        "vfr_only": false
    },
    "zab_bounds": {
        "north": 37.0,
        "south": 31.0,
        "east": -103.0,
        "west": -114.0
    }
}
```

## Troubleshooting

### "PortAudio library not found"
Install PortAudio:
- Ubuntu/Debian: `sudo apt-get install portaudio19-dev`
- macOS: `brew install portaudio`

### "Pydub not available"
Install pydub: `pip install pydub`

### Audio playback issues
Ensure FFmpeg is installed and available in your PATH.

## License

MIT License
