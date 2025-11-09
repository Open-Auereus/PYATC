from django.shortcuts import render, redirect
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import json
import logging
from .scanner_service import ScannerService
from .models import ScannerSettings, AudioTransmission, ScannerSession

logger = logging.getLogger(__name__)

scanner_service = ScannerService()


def index(request):
    context = {
        'status': scanner_service.get_status(),
    }
    return render(request, 'scanner/index.html', context)


def dashboard(request):
    status = scanner_service.get_status()
    recent_transmissions = AudioTransmission.objects.all()[:20]

    context = {
        'status': status,
        'recent_transmissions': recent_transmissions,
    }
    return render(request, 'scanner/dashboard.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def start_scanner(request):
    try:
        data = json.loads(request.body) if request.body else {}
        result = scanner_service.start(data)
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error starting scanner: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def stop_scanner(request):
    try:
        result = scanner_service.stop()
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error stopping scanner: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@require_http_methods(["GET"])
def get_status(request):
    try:
        status = scanner_service.get_status()
        return JsonResponse(status)
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def update_settings(request):
    try:
        data = json.loads(request.body)
        result = scanner_service.update_settings(data)
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@require_http_methods(["GET"])
def get_next_audio(request):
    try:
        audio = scanner_service.get_next_audio()
        if audio:
            return JsonResponse(audio.to_dict())
        else:
            return JsonResponse({"status": "no_audio"}, status=204)
    except Exception as e:
        logger.error(f"Error getting next audio: {e}")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@require_http_methods(["GET"])
def transmissions_list(request):
    limit = int(request.GET.get('limit', 50))
    transmissions = AudioTransmission.objects.all()[:limit]
    data = [{
        'id': t.transmission_id,
        'station_name': t.station_name,
        'frequency': t.frequency,
        'pilot': t.pilot,
        'airport': t.airport,
        'flight_rules': t.flight_rules,
        'timestamp': t.timestamp.isoformat() if t.timestamp else None,
    } for t in transmissions]
    return JsonResponse(data, safe=False)


def settings_page(request):
    status = scanner_service.get_status()
    return render(request, 'scanner/settings.html', {'settings': status['settings']})


def history(request):
    transmissions = AudioTransmission.objects.all()[:100]
    return render(request, 'scanner/history.html', {'transmissions': transmissions})
