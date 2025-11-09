import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .scanner_service import ScannerService

logger = logging.getLogger(__name__)


class ScannerConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'scanner_updates'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        scanner_service = ScannerService()
        status = await sync_to_async(scanner_service.get_status)()

        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'data': status
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            scanner_service = ScannerService()

            if message_type == 'get_status':
                status = await sync_to_async(scanner_service.get_status)()
                await self.send(text_data=json.dumps({
                    'type': 'status_update',
                    'data': status
                }))

            elif message_type == 'start_scanner':
                settings = data.get('settings', {})
                result = await sync_to_async(scanner_service.start)(settings)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'scanner_started',
                        'data': result
                    }
                )

            elif message_type == 'stop_scanner':
                result = await sync_to_async(scanner_service.stop)()
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'scanner_stopped',
                        'data': result
                    }
                )

        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def new_transmission(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_transmission',
            'data': event['data']
        }))

    async def status_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'data': event['data']
        }))

    async def scanner_started(self, event):
        await self.send(text_data=json.dumps({
            'type': 'scanner_started',
            'data': event['data']
        }))

    async def scanner_stopped(self, event):
        await self.send(text_data=json.dumps({
            'type': 'scanner_stopped',
            'data': event['data']
        }))
