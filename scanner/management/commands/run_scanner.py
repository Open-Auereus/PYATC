from django.core.management.base import BaseCommand
from scanner.scanner_service import ScannerService
import time


class Command(BaseCommand):
    help = 'Run the aviation scanner service'

    def add_arguments(self, parser):
        parser.add_argument('--volume', type=float, default=0.7, help='Volume level (0.0-1.0)')
        parser.add_argument('--interval', type=int, default=20, help='Fetch interval in seconds')
        parser.add_argument('--vfr-only', action='store_true', help='Only VFR transmissions')
        parser.add_argument('--geo-filter', action='store_true', help='Enable geographic filtering')
        parser.add_argument('--airports', nargs='+', help='Filter by airports')

    def handle(self, *args, **options):
        scanner = ScannerService()

        settings = {
            'volume': options['volume'],
            'fetch_interval': options['interval'],
            'vfr_only': options['vfr_only'],
            'geo_filter': options['geo_filter'],
            'airports': options.get('airports', []),
        }

        self.stdout.write(self.style.SUCCESS('Starting Aviation Scanner...'))
        scanner.start(settings)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nStopping scanner...'))
            scanner.stop()
            self.stdout.write(self.style.SUCCESS('Scanner stopped'))
