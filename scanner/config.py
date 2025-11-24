"""
Configuration management for the scanner.
"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class Config:
    """Configuration handler."""

    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.data = self._load_config()

        # Environment variable overrides
        self.api_url = os.getenv("API_URL", os.getenv("URL"))

        # Derived WebSocket URL
        if self.api_url:
            self.ws_url = self.api_url.replace("https://", "wss://").replace("http://", "ws://")
            if self.ws_url.endswith('/'):
                self.ws_url = self.ws_url[:-1]
            self.ws_url = f"{self.ws_url}/live"  # Assuming /live endpoint for WS, need to verify
        else:
            self.ws_url = None

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading config from {self.config_path}: {e}")
        return {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.data.get(key, default)

# Global config instance
config = Config()
