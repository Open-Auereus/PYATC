# Aviation Scanner - Django Frontend

## Project Overview

A comprehensive Django web application that provides a modern interface for the Aviation Scanner Python script. Monitor real-time air traffic control communications through an intuitive web dashboard.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Web Browser                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   Live   │  │Dashboard │  │ History  │  │ Settings │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼─────────────┼─────────────┼─────────────┼──────────┘
        │             │             │             │
        │    HTTP/WebSocket         │             │
        └─────────────┼─────────────┴─────────────┘
                      │
        ┌─────────────▼─────────────────────────────┐
        │         Django Application                 │
        │  ┌────────────────────────────────────┐   │
        │  │       URL Router & Views           │   │
        │  └──────────┬──────────────────┬──────┘   │
        │             │                  │           │
        │  ┌──────────▼─────┐  ┌────────▼────────┐  │
        │  │  Scanner Service│  │  WebSocket      │  │
        │  │  (Background)   │  │  Consumer       │  │
        │  └──────────┬──────┘  └─────────────────┘  │
        │             │                               │
        │  ┌──────────▼──────────────────────────┐   │
        │  │     Django ORM / Models             │   │
        │  └──────────┬──────────────────────────┘   │
        └─────────────┼────────────────────────────────┘
                      │
        ┌─────────────▼─────────────────────────────┐
        │        Supabase PostgreSQL                 │
        │  ┌──────────────────────────────────────┐ │
        │  │  - Scanner Settings                   │ │
        │  │  - Audio Transmissions               │ │
        │  │  - Scanner Sessions                  │ │
        │  └──────────────────────────────────────┘ │
        └────────────────────────────────────────────┘
                      │
        ┌─────────────▼─────────────────────────────┐
        │      External Aviation API                 │
        │  (Provides transmission data & audio)      │
        └────────────────────────────────────────────┘
```

## Key Features

### 1. Live Scanner Page
- Real-time audio playback
- Visual transmission display
- Start/Stop controls
- Queue monitoring
- Current transmission details

### 2. Dashboard
- Scanner status overview
- Queue size and statistics
- Recent transmissions table
- System information

### 3. History
- Complete transmission archive
- Search and filter capabilities
- Detailed transmission view
- Flight rules filtering

### 4. Settings
- Volume control
- Fetch interval configuration
- VFR/IFR filtering
- Geographic bounds
- Airport-specific filtering
- Prefetch settings

## Technology Stack

### Backend
- **Django 4.2+** - Web framework
- **Django Channels** - WebSocket support
- **Daphne** - ASGI server
- **PostgreSQL** - Database (via Supabase)
- **Python 3.10+**

### Frontend
- **Vanilla JavaScript** - No framework bloat
- **WebSocket API** - Real-time updates
- **Web Audio API** - Audio playback
- **CSS3** - Modern styling

### Infrastructure
- **Supabase** - Database hosting
- **Redis** - Channel layers (optional)
- **Docker** - Containerization (optional)

## File Structure

```
aviation_scanner/
├── aviation_scanner/          # Django project
│   ├── __init__.py
│   ├── settings.py           # Project settings
│   ├── urls.py               # Root URL config
│   ├── asgi.py               # ASGI config
│   └── wsgi.py               # WSGI config
│
├── scanner/                   # Main app
│   ├── models.py             # Database models
│   ├── views.py              # View functions
│   ├── urls.py               # App URLs
│   ├── consumers.py          # WebSocket handlers
│   ├── routing.py            # WebSocket routing
│   ├── scanner_service.py    # Core scanner logic
│   ├── admin.py              # Admin interface
│   ├── apps.py               # App configuration
│   │
│   ├── management/           # Custom commands
│   │   └── commands/
│   │       └── run_scanner.py
│   │
│   └── migrations/           # Database migrations
│
├── templates/                # HTML templates
│   ├── base.html            # Base template
│   └── scanner/
│       ├── index.html       # Live scanner
│       ├── dashboard.html   # Dashboard
│       ├── history.html     # History view
│       └── settings.html    # Settings page
│
├── static/                   # Static files
│   └── (CSS, JS, images)
│
├── scanner_live.py           # Original CLI script
├── manage.py                 # Django management
├── requirements.txt          # Python dependencies
├── config.json              # Scanner configuration
│
├── start.sh                 # Production start script
├── dev.sh                   # Development script
├── SETUP.md                 # Setup instructions
└── PROJECT_OVERVIEW.md      # This file
```

## Data Flow

### Scanning Flow
1. User clicks "Start Scanner"
2. Frontend sends POST to `/api/start/`
3. Scanner service starts background thread
4. Service polls external API at configured interval
5. New transmissions added to queue
6. Frontend polls `/api/next-audio/` for playback
7. Audio plays in browser via Web Audio API
8. Transmission saved to database

### WebSocket Flow
1. Browser connects to `ws://host/ws/scanner/`
2. Server sends initial status
3. Scanner service broadcasts events:
   - New transmission available
   - Status changes
   - Settings updates
4. Browser receives real-time updates
5. UI updates automatically

## Database Schema

### scanner_settings
```sql
- id (PK)
- user_id (FK)
- volume (float)
- fetch_interval (int)
- vfr_only (bool)
- geo_filter (bool)
- prefetch_audio (bool)
- use_websocket (bool)
- airports (json)
- created_at (timestamp)
- updated_at (timestamp)
```

### audio_transmissions
```sql
- id (PK)
- transmission_id (int, unique)
- url (text)
- who_from (varchar)
- frequency (varchar)
- station_name (varchar)
- pilot (varchar)
- airport (varchar)
- position (varchar)
- voice_name (varchar)
- from_userid (varchar)
- flight_rules (varchar)
- latitude (float, nullable)
- longitude (float, nullable)
- timestamp (timestamp)
- created_at (timestamp)
```

### scanner_sessions
```sql
- id (PK)
- user_id (FK, nullable)
- started_at (timestamp)
- ended_at (timestamp, nullable)
- is_active (bool)
- transmissions_count (int)
- settings_snapshot (json)
```

## API Endpoints

### REST API
- `GET /` - Live scanner page
- `GET /dashboard/` - Dashboard page
- `GET /history/` - History page
- `GET /settings/` - Settings page
- `POST /api/start/` - Start scanner
- `POST /api/stop/` - Stop scanner
- `GET /api/status/` - Get status
- `POST /api/settings/` - Update settings
- `GET /api/next-audio/` - Get next audio
- `GET /api/transmissions/` - List transmissions

### WebSocket
- `ws://host/ws/scanner/` - Real-time updates

## Configuration

### Environment Variables
```bash
DJANGO_SECRET_KEY          # Django secret
DEBUG                      # Debug mode
API_URL                    # Aviation API URL
SUPABASE_DB_HOST          # Database host
SUPABASE_DB_PORT          # Database port
SUPABASE_DB_NAME          # Database name
SUPABASE_DB_USER          # Database user
SUPABASE_DB_PASSWORD      # Database password
```

### config.json
```json
{
  "api_environments": { ... },
  "default_settings": {
    "volume": 0.7,
    "fetch_interval": 20,
    "vfr_only": false,
    "geo_filter": false,
    ...
  },
  "zab_bounds": {
    "north": 37.0,
    "south": 31.0,
    "east": -103.0,
    "west": -114.0
  }
}
```

## Deployment

### Development
```bash
./dev.sh
# or
python manage.py runserver
```

### Production
```bash
./start.sh
# or
daphne aviation_scanner.asgi:application
```

### Docker (Optional)
```dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "aviation_scanner.asgi:application"]
```

## Testing

```bash
python manage.py test scanner
```

## Monitoring

- Access Django admin at `/admin/`
- View logs in console
- Monitor database queries
- Check WebSocket connections

## Future Enhancements

- [ ] User authentication system
- [ ] Favorite airports/frequencies
- [ ] Audio recording and playback
- [ ] Map visualization of transmissions
- [ ] Advanced filtering and search
- [ ] Mobile app (React Native)
- [ ] Push notifications
- [ ] Analytics dashboard
- [ ] Export capabilities
- [ ] API rate limiting
- [ ] Caching layer (Redis)
- [ ] Load balancing support

## Contributing

See original scanner_live.py for core functionality.
Web interface built as Django wrapper.

## Support

For issues and questions:
1. Check SETUP.md for installation help
2. Review Django logs
3. Check browser console for frontend errors
4. Verify database connectivity
5. Test external API access
