# Aviation Scanner - Quick Start Guide

## 5-Minute Setup

### Step 1: Configure Environment (1 min)

```bash
cp .env.example .env
nano .env  # or your preferred editor
```

**Required settings:**
```bash
API_URL=https://your-aviation-api-url.com
SUPABASE_DB_PASSWORD=your-database-password
```

### Step 2: Start the Application (2 min)

```bash
./start.sh
```

This will:
- Create virtual environment
- Install dependencies
- Run database migrations
- Start the server

### Step 3: Access the Interface (1 min)

Open your browser to:
```
http://localhost:8000
```

### Step 4: Start Scanning (1 min)

1. Click the "Start Scanner" button
2. Audio will play automatically
3. Monitor the dashboard

## Common Commands

### Development
```bash
./dev.sh                              # Start dev server
python manage.py createsuperuser      # Create admin user
python manage.py runserver            # Manual dev server
```

### Production
```bash
./start.sh                                              # Production mode
daphne aviation_scanner.asgi:application                # Manual start
docker-compose up                                       # Docker
```

### Database
```bash
python manage.py makemigrations       # Create migrations
python manage.py migrate              # Apply migrations
python manage.py dbshell             # Database shell
```

### Management
```bash
python manage.py run_scanner          # Run scanner CLI
python manage.py collectstatic        # Collect static files
python manage.py test                 # Run tests
```

## Troubleshooting

### "Module not found" error
```bash
pip install -r requirements.txt
```

### Database connection failed
Check your `.env` file for correct Supabase credentials

### Audio not playing
- Check browser permissions
- Verify API_URL is correct
- Look at browser console for errors

### Port already in use
```bash
# Change port in start.sh or use:
daphne -b 0.0.0.0 -p 8001 aviation_scanner.asgi:application
```

## Key URLs

- **Live Scanner**: http://localhost:8000/
- **Dashboard**: http://localhost:8000/dashboard/
- **History**: http://localhost:8000/history/
- **Settings**: http://localhost:8000/settings/
- **Admin**: http://localhost:8000/admin/

## Configuration Files

- `.env` - Environment variables
- `config.json` - Scanner configuration
- `aviation_scanner/settings.py` - Django settings

## Getting Help

1. Check `README.md` for comprehensive documentation
2. See `SETUP.md` for detailed installation
3. Read `PROJECT_OVERVIEW.md` for architecture
4. Review `FEATURES.md` for feature details

## Quick Tips

- Use Chrome or Firefox for best compatibility
- Enable audio autoplay in browser settings
- Check the dashboard for system status
- History page shows all past transmissions
- Settings are saved automatically

## Default Settings

- Volume: 0.7
- Fetch Interval: 20 seconds
- VFR Only: Disabled
- Geo Filter: Disabled
- Prefetch: Enabled

## Next Steps

1. Configure filters in Settings
2. Add airports to monitor
3. Adjust volume and intervals
4. Review transmission history
5. Enable geographic filtering

## Support

For issues:
- Check Django logs in console
- Verify database connectivity
- Test API accessibility
- Review browser console

Enjoy monitoring air traffic!
