#!/bin/bash

echo "Aviation Scanner - Development Mode"
echo "===================================="

if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Using defaults."
fi

source venv/bin/activate 2>/dev/null || true

echo "Starting Django development server..."
echo "Access the application at: http://localhost:8000"
echo ""
echo "Note: For WebSocket support, use ./start.sh instead"
echo ""

python manage.py runserver 0.0.0.0:8000
