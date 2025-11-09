# Aviation Scanner - Django Web Frontend

A modern Django web application that provides a real-time interface for monitoring air traffic control communications. Built on top of the existing `scanner_live.py` Python script with a beautiful, responsive web UI.

## Features

- **Live Audio Streaming** - Real-time ATC transmission playback in your browser
- **Interactive Dashboard** - View statistics, queue size, and system status
- **Transmission History** - Browse and search past transmissions
- **Configurable Filters** - Filter by VFR/IFR, airports, and geographic bounds
- **WebSocket Support** - Real-time updates without polling
- **Settings Management** - Easy-to-use configuration interface
- **Database Integration** - Persistent storage with Supabase PostgreSQL
- **Admin Interface** - Django admin for advanced management

## Quick Start

### Prerequisites

- Python 3.10 or higher
- PostgreSQL (Supabase account recommended)
- Audio playback capability

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd aviation_scanner
```

2. Set up environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run the quick start script:
```bash
./start.sh
```

The application will be available at `http://localhost:8000`

### Manual Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
daphne -b 0.0.0.0 -p 8000 aviation_scanner.asgi:application
```

## Configuration

### Environment Variables

Create a `.env` file with:

```bash
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True
API_URL=https://your-aviation-api-url.com

SUPABASE_DB_HOST=your-host.supabase.com
SUPABASE_DB_PORT=6543
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres.your-ref
SUPABASE_DB_PASSWORD=your-password
```

### Scanner Settings

Edit `config.json` to configure:
- API endpoints
- Default volume and intervals
- Geographic bounds (Albuquerque ARTCC)
- FFmpeg paths

## Usage

### Web Interface

1. **Live Scanner** (`/`)
   - Start/stop scanner
   - View current transmission
   - Monitor queue and status
   - Real-time audio playback

2. **Dashboard** (`/dashboard/`)
   - System statistics
   - Recent transmissions
   - Scanner status overview

3. **History** (`/history/`)
   - Browse all transmissions
   - Search and filter
   - View detailed information

4. **Settings** (`/settings/`)
   - Adjust volume
   - Configure fetch interval
   - Set VFR/IFR filters
   - Manage airport list
   - Enable geographic filtering

### API Usage

```bash
# Start scanner
curl -X POST http://localhost:8000/api/start/

# Stop scanner
curl -X POST http://localhost:8000/api/stop/

# Get status
curl http://localhost:8000/api/status/

# Get next audio
curl http://localhost:8000/api/next-audio/

# Update settings
curl -X POST http://localhost:8000/api/settings/ \
  -H "Content-Type: application/json" \
  -d '{"volume": 0.8, "fetch_interval": 15}'
```

### WebSocket Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/scanner/');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'new_transmission') {
    console.log('New audio:', data.data);
  }

  if (data.type === 'status_update') {
    console.log('Status:', data.data);
  }
};

// Start scanner via WebSocket
ws.send(JSON.stringify({
  type: 'start_scanner',
  settings: { volume: 0.7 }
}));
```

## Docker Deployment

### Using Docker Compose

```bash
docker-compose up -d
```

### Manual Docker Build

```bash
docker build -t aviation-scanner .
docker run -p 8000:8000 --env-file .env aviation-scanner
```

## Development

### Running Tests

```bash
python manage.py test scanner
```

### Development Server

```bash
./dev.sh
# or
python manage.py runserver
```

### Creating Admin User

```bash
python manage.py createsuperuser
```

Access admin at: `http://localhost:8000/admin/`

## Project Structure

```
aviation_scanner/
├── aviation_scanner/      # Django project
├── scanner/              # Main app
│   ├── models.py        # Database models
│   ├── views.py         # View functions
│   ├── consumers.py     # WebSocket handlers
│   └── scanner_service.py  # Core logic
├── templates/           # HTML templates
├── static/             # Static files
├── scanner_live.py     # Original CLI script
└── manage.py          # Django management
```

## Database Models

- **ScannerSettings** - User configuration
- **AudioTransmission** - Transmission records
- **ScannerSession** - Session tracking

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Live scanner page |
| GET | `/dashboard/` | Dashboard |
| GET | `/history/` | History view |
| GET | `/settings/` | Settings page |
| POST | `/api/start/` | Start scanner |
| POST | `/api/stop/` | Stop scanner |
| GET | `/api/status/` | Get status |
| POST | `/api/settings/` | Update settings |
| GET | `/api/next-audio/` | Get next audio |
| GET | `/api/transmissions/` | List transmissions |

## Troubleshooting

### Audio Not Playing
- Check browser audio permissions
- Verify API_URL is correct
- Ensure audio URLs are accessible
- Check browser console for errors

### WebSocket Issues
- Use Daphne instead of runserver
- Verify ALLOWED_HOSTS setting
- Check WebSocket URL protocol (ws:// or wss://)

### Database Errors
- Verify Supabase credentials
- Check network connectivity
- Run migrations: `python manage.py migrate`

## Production Deployment

1. Set `DEBUG=False`
2. Generate secure `DJANGO_SECRET_KEY`
3. Configure `ALLOWED_HOSTS`
4. Use production WSGI server (gunicorn + daphne)
5. Set up Redis for channel layers
6. Configure HTTPS/WSS
7. Set up static file serving

Example production setup:

```bash
# Install production dependencies
pip install gunicorn redis

# Collect static files
python manage.py collectstatic --noinput

# Run with Daphne
daphne -b 0.0.0.0 -p 8000 aviation_scanner.asgi:application
```

## Technologies

- **Backend**: Django 4.2+, Django Channels, Daphne
- **Database**: PostgreSQL (Supabase)
- **Frontend**: Vanilla JavaScript, CSS3, WebSocket API
- **Audio**: Web Audio API, Pydub, miniaudio
- **Server**: ASGI (Daphne)

## Documentation

- [SETUP.md](SETUP.md) - Detailed setup instructions
- [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) - Architecture and design

## Contributing

Feel free to submit issues and pull requests.

## License

See LICENSE file for details.

## Acknowledgments

Built on top of the original `scanner_live.py` aviation scanner script.
