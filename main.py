#!/usr/bin/env python3
"""
Real-Time Aviation Scanner Entry Point
"""
import argparse
import asyncio
import logging
import sys
from typing import NoReturn

from rich.live import Live

from scanner.config import config
from scanner.core import RealtimeScanner
from scanner.ui import ScannerUI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='scanner.log' # Log to file to not mess up UI
)
logger = logging.getLogger(__name__)

async def run_scanner(args):
    """Run the scanner with UI."""

    ui = ScannerUI()

    def on_audio_start(audio):
        ui.add_transmission(audio)

    def on_status_update(msg):
        ui.update_status(msg)

    scanner = RealtimeScanner(
        api_base_url=args.api,
        volume=args.volume,
        fetch_interval=args.interval,
        use_websocket=not args.no_websocket,
        prefetch_audio=not args.no_prefetch,
        vfr_only=args.vfr_only,
        geo_filter=args.geo_filter,
        airports=args.airports,
        on_audio_start=on_audio_start,
        on_status_update=on_status_update
    )

    # Run scanner and UI update loop
    try:
        with Live(ui.render(), refresh_per_second=4, screen=True) as live:

            # Create a background task for the UI updater
            async def ui_updater():
                while True:
                    live.update(ui.render())
                    await asyncio.sleep(0.25)

            async with asyncio.TaskGroup() as tg:
                tg.create_task(scanner.start())
                tg.create_task(ui_updater())

    except KeyboardInterrupt:
        await scanner.cleanup()
        print("Goodbye!")
    except Exception as e:
        logger.exception("Fatal error")
        print(f"Fatal error: {e}")
    finally:
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="Real-Time Aviation Scanner")
    parser.add_argument("--api", type=str, help="API base URL")
    parser.add_argument("--volume", type=float, default=0.7, help="Volume (0.0-1.0)")
    parser.add_argument("--interval", type=int, default=3, help="Fetch interval (seconds)")
    parser.add_argument("--no-websocket", action="store_true", help="Disable WebSocket")
    parser.add_argument("--no-prefetch", action="store_true", help="Disable audio prefetching")
    parser.add_argument("--vfr-only", action="store_true", help="Only play VFR traffic")
    parser.add_argument("--geo-filter", action="store_true", help="Enable geographic filtering")
    parser.add_argument("--airports", nargs="+", help="Filter by airports (e.g. KTUS KABQ)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging (to file)")

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        asyncio.run(run_scanner(args))
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
