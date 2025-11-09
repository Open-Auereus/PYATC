# Aviation Scanner - Django Frontend Setup

A modern web interface for the Aviation Scanner that provides real-time monitoring of air traffic control communications with filtering capabilities.

## Features

- Real-time audio streaming of ATC transmissions
- Live dashboard with transmission history
- Configurable filters (VFR/IFR, geographic, airports)
- WebSocket support for instant updates
- Volume and playback controls
- Transmission history with search and filtering
- Settings management UI
- Supabase integration for data persistence

## Prerequisites

- Python 3.10+
- PostgreSQL (Supabase)
- Audio playback support

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your settings
```

Required environment variables:
- `DJANGO_SECRET_KEY` - Django secret key
- `API_URL` - Aviation API endpoint
- `SUPABASE_DB_HOST` - Supabase database host
- `SUPABASE_DB_PORT` - Database port (typically 6543)
- `SUPABASE_DB_NAME` - Database name (typically postgres)
- `SUPABASE_DB_USER` - Database user
- `SUPABASE_DB_PASSWORD` - Database password

3. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

4. Create a superuser (optional):
```bash
python manage.py createsuperuser
```

5. Collect static files:
```bash
python manage.py collectstatic --noinput
```

## Running the Application

### Development Server

For HTTP only:
```bash
python manage.py runserver
```

For WebSocket support (recommended):
```bash
daphne -b 0.0.0.0 -p 8000 aviation_scanner.asgi:application
```

The application will be available at `http://localhost:8000`

## Usage

### Web Interface

1. Navigate to `http://localhost:8000`
2. Click "Start Scanner" to begin monitoring
3. Audio transmissions will play automatically as they arrive
4. Use the dashboard to view statistics
5. Configure filters in the Settings page

### Pages

- **Live** (`/`) - Real-time transmission player with controls
- **Dashboard** (`/dashboard/`) - Statistics and recent transmissions
- **History** (`/history/`) - Full transmission history with filtering
- **Settings** (`/settings/`) - Configure scanner parameters

### API Endpoints

- `POST /api/start/` - Start the scanner
- `POST /api/stop/` - Stop the scanner
- `GET /api/status/` - Get scanner status
- `POST /api/settings/` - Update settings
- `GET /api/next-audio/` - Get next audio transmission
- `GET /api/transmissions/` - List transmissions

### WebSocket

Connect to `ws://localhost:8000/ws/scanner/` for real-time updates.

Message types:
- `new_transmission` - New audio available
- `status_update` - Scanner status changed
- `scanner_started` - Scanner started
- `scanner_stopped` - Scanner stopped

## Configuration

Edit `config.json` to configure:
- API environments
- Default settings
- Geographic bounds (ZAB ARTCC)
- Logging levels
- FFmpeg paths
- Playback backend

## Project Structure

```
aviation_scanner/
├── aviation_scanner/        # Django project settings
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── scanner/                 # Main scanner app
│   ├── models.py           # Database models
│   ├── views.py            # View functions
│   ├── urls.py             # URL routing
│   ├── consumers.py        # WebSocket consumers
│   ├── scanner_service.py  # Core scanner logic
│   └── admin.py            # Admin interface
├── templates/              # HTML templates
│   ├── base.html
│   └── scanner/
│       ├── index.html
│       ├── dashboard.html
│       ├── history.html
│       └── settings.html
├── static/                 # Static files
├── scanner_live.py         # Original CLI scanner
└── manage.py              # Django management

## Database Models

### ScannerSettings
User-specific scanner configuration settings.

### AudioTransmission
Stores transmission metadata for history and analysis.

### ScannerSession
Tracks scanner sessions for auditing and statistics.

## Admin Interface

Access the Django admin at `/admin/` to:
- View and manage transmissions
- Configure user settings
- Monitor scanner sessions

## Troubleshooting

### Audio not playing
- Check browser permissions for audio
- Verify the API_URL is correct
- Ensure audio URLs are accessible

### WebSocket not connecting
- Make sure you're using Daphne, not runserver
- Check ALLOWED_HOSTS in settings.py
- Verify WebSocket URL protocol (ws:// or wss://)

### Database connection errors
- Verify Supabase credentials in .env
- Check network connectivity to Supabase
- Ensure migrations are applied

## Production Deployment

1. Set `DEBUG=False` in .env
2. Generate a secure `DJANGO_SECRET_KEY`
3. Configure `ALLOWED_HOSTS`
4. Use a production WSGI server (gunicorn + daphne)
5. Set up Redis for channel layers
6. Configure HTTPS/WSS
7. Set up static file serving (nginx/CDN)

## License

See LICENSE file for details.
