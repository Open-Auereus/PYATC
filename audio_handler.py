import asyncio
import websockets
import json
import threading
import queue
import numpy as np
import pyaudio
from collections import deque
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AudioBuffer:
    """Enhanced audio buffer with RAM storage and circular buffer implementation"""
    
    def __init__(self, max_size=44100 * 10):  # 10 seconds at 44.1kHz
        self.buffer = deque(maxlen=max_size)
        self.lock = threading.Lock()
        self.sample_rate = 44100
        self.channels = 1
        self.chunk_size = 1024
        
    def add_chunk(self, audio_data):
        """Add audio chunk to buffer"""
        with self.lock:
            # Convert bytes to numpy array if needed
            if isinstance(audio_data, bytes):
                audio_array = np.frombuffer(audio_data, dtype=np.int16)
            else:
                audio_array = audio_data
            
            # Add to circular buffer
            self.buffer.extend(audio_array)
            
    def get_latest_chunk(self, size=None):
        """Get the most recent audio chunk"""
        with self.lock:
            if not self.buffer:
                return None
            
            if size is None:
                size = min(len(self.buffer), self.chunk_size)
            
            # Get latest chunk
            chunk = list(self.buffer)[-size:]
            return np.array(chunk, dtype=np.int16)
    
    def get_buffer_duration(self):
        """Get current buffer duration in seconds"""
        with self.lock:
            return len(self.buffer) / self.sample_rate
    
    def clear_buffer(self):
        """Clear the audio buffer"""
        with self.lock:
            self.buffer.clear()

class AudioStreamHandler:
    """Main audio stream handler with WebSocket support"""
    
    def __init__(self, websocket_port=8765):
        self.audio_buffer = AudioBuffer()
        self.is_recording = False
        self.is_streaming = False
        self.websocket_port = websocket_port
        self.connected_clients = set()
        
        # PyAudio setup
        self.pa = pyaudio.PyAudio()
        self.stream = None
        
        # Threading
        self.record_thread = None
        self.websocket_thread = None
        self.audio_queue = queue.Queue()
        
    def start_recording(self):
        """Start audio recording"""
        if self.is_recording:
            logger.warning("Already recording")
            return
            
        try:
            self.stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=self.audio_buffer.channels,
                rate=self.audio_buffer.sample_rate,
                input=True,
                frames_per_buffer=self.audio_buffer.chunk_size,
                stream_callback=self._audio_callback
            )
            
            self.is_recording = True
            self.stream.start_stream()
            logger.info("Audio recording started")
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            
    def stop_recording(self):
        """Stop audio recording"""
        if not self.is_recording:
            return
            
        self.is_recording = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
        logger.info("Audio recording stopped")
        
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback for handling incoming audio"""
        if status:
            logger.warning(f"Audio callback status: {status}")
            
        # Add to buffer
        self.audio_buffer.add_chunk(in_data)
        
        # Add to queue for WebSocket streaming
        if self.is_streaming and not self.audio_queue.full():
            try:
                self.audio_queue.put_nowait(in_data)
            except queue.Full:
                logger.warning("Audio queue full, dropping frame")
                
        return (None, pyaudio.paContinue)
    
    async def websocket_handler(self, websocket, path):
        """Handle WebSocket connections"""
        self.connected_clients.add(websocket)
        logger.info(f"Client connected. Total clients: {len(self.connected_clients)}")
        
        try:
            await websocket.send(json.dumps({
                "type": "connection",
                "status": "connected",
                "sample_rate": self.audio_buffer.sample_rate,
                "channels": self.audio_buffer.channels
            }))
            
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.handle_websocket_message(websocket, data)
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "message": "Invalid JSON"
                    }))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
        finally:
            self.connected_clients.discard(websocket)
            
    async def handle_websocket_message(self, websocket, data):
        """Handle incoming WebSocket messages"""
        message_type = data.get("type")
        
        if message_type == "start_stream":
            self.is_streaming = True
            await websocket.send(json.dumps({
                "type": "stream_status",
                "streaming": True
            }))
            
        elif message_type == "stop_stream":
            self.is_streaming = False
            await websocket.send(json.dumps({
                "type": "stream_status",
                "streaming": False
            }))
            
        elif message_type == "get_buffer_info":
            await websocket.send(json.dumps({
                "type": "buffer_info",
                "duration": self.audio_buffer.get_buffer_duration(),
                "size": len(self.audio_buffer.buffer)
            }))
            
    async def stream_audio_data(self):
        """Stream audio data to connected WebSocket clients"""
        while True:
            if self.is_streaming and self.connected_clients:
                try:
                    # Get audio data from queue with timeout
                    audio_data = self.audio_queue.get(timeout=0.1)
                    
                    # Convert to base64 for JSON transmission
                    import base64
                    audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                    
                    message = json.dumps({
                        "type": "audio_data",
                        "data": audio_b64,
                        "timestamp": time.time()
                    })
                    
                    # Send to all connected clients
                    disconnected = set()
                    for client in self.connected_clients:
                        try:
                            await client.send(message)
                        except websockets.exceptions.ConnectionClosed:
                            disconnected.add(client)
                    
                    # Remove disconnected clients
                    self.connected_clients -= disconnected
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error streaming audio: {e}")
            else:
                await asyncio.sleep(0.1)
                
    def start_websocket_server(self):
        """Start WebSocket server for audio streaming"""
        async def run_server():
            # Start audio streaming task
            stream_task = asyncio.create_task(self.stream_audio_data())
            
            # Start WebSocket server
            server = await websockets.serve(
                self.websocket_handler,
                "localhost",
                self.websocket_port
            )
            
            logger.info(f"WebSocket server started on port {self.websocket_port}")
            
            # Keep server running
            await server.wait_closed()
            
        # Run in separate thread
        self.websocket_thread = threading.Thread(
            target=lambda: asyncio.run(run_server())
        )
        self.websocket_thread.daemon = True
        self.websocket_thread.start()
        
    def get_audio_data(self, duration=1.0):
        """Get audio data from buffer for specified duration"""
        samples_needed = int(duration * self.audio_buffer.sample_rate)
        return self.audio_buffer.get_latest_chunk(samples_needed)
        
    def save_buffer_to_file(self, filename):
        """Save current buffer to WAV file"""
        import wave
        
        with self.audio_buffer.lock:
            if not self.audio_buffer.buffer:
                logger.warning("No audio data to save")
                return False
                
            try:
                # Convert buffer to numpy array
                audio_data = np.array(list(self.audio_buffer.buffer), dtype=np.int16)
                
                # Save as WAV file
                with wave.open(filename, 'wb') as wav_file:
                    wav_file.setnchannels(self.audio_buffer.channels)
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(self.audio_buffer.sample_rate)
                    wav_file.writeframes(audio_data.tobytes())
                    
                logger.info(f"Audio saved to {filename}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to save audio: {e}")
                return False
                
    def cleanup(self):
        """Clean up resources"""
        self.stop_recording()
        self.is_streaming = False
        
        if self.pa:
            self.pa.terminate()
            
        logger.info("Audio handler cleaned up")

# Example usage and testing
if __name__ == "__main__":
    # Create audio handler instance
    audio_handler = AudioStreamHandler(websocket_port=8765)
    
    try:
        # Start WebSocket server
        audio_handler.start_websocket_server()
        
        # Start recording
        audio_handler.start_recording()
        
        print("Audio handler started. Press Ctrl+C to stop...")
        print(f"WebSocket server running on ws://localhost:8765")
        print("Buffer duration updates every 5 seconds...")
        
        # Keep main thread alive and show buffer status
        while True:
            time.sleep(5)
            duration = audio_handler.audio_buffer.get_buffer_duration()
            print(f"Current buffer duration: {duration:.2f} seconds")
            
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        audio_handler.cleanup()
