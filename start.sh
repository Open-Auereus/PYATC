#!/bin/bash

echo "Aviation Scanner - Quick Start"
echo "==============================="

if [ ! -f ".env" ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and configure it."
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Running migrations..."
python manage.py makemigrations
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "Starting server with WebSocket support..."
echo "Access the application at: http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

daphne -b 0.0.0.0 -p 8000 aviation_scanner.asgi:application
