"""
User Interface module using Rich.
"""
import asyncio
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from .audio import AudioData

class ScannerUI:
    """Rich-based UI for the scanner."""

    def __init__(self):
        self.console = Console()
        self.layout = Layout()

        self.history: list[AudioData] = []
        self.max_history = 10
        self.current_audio: Optional[AudioData] = None
        self.status_message = "Initializing..."

        self._setup_layout()

    def _setup_layout(self):
        """Define the layout structure."""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        self.layout["main"].split_row(
            Layout(name="current", ratio=1),
            Layout(name="history", ratio=1)
        )

    def update_status(self, message: str):
        """Update the status message."""
        self.status_message = message

    def add_transmission(self, audio: AudioData):
        """Add a new transmission to display."""
        self.current_audio = audio
        self.history.insert(0, audio)
        if len(self.history) > self.max_history:
            self.history.pop()

    def _generate_header(self) -> Panel:
        """Generate the header panel."""
        grid = Table.grid(expand=True)
        grid.add_column(justify="center", ratio=1)
        grid.add_column(justify="right")

        title = Text("✈️  Real-Time Aviation Scanner", style="bold blue")
        time_str = datetime.now().strftime("%H:%M:%S")

        grid.add_row(title, Text(f"Time: {time_str}", style="dim"))

        return Panel(grid, style="white on black")

    def _generate_current_panel(self) -> Panel:
        """Generate the current transmission panel."""
        if not self.current_audio:
            return Panel(
                Text("Waiting for transmission...", justify="center", style="dim"),
                title="Live Transmission",
                border_style="blue",
                box=box.ROUNDED
            )

        audio = self.current_audio

        table = Table(show_header=False, expand=True, box=None)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Station", audio.station_name)
        table.add_row("Frequency", audio.frequency)
        table.add_row("Pilot", audio.pilot)
        table.add_row("Airport", audio.airport)
        table.add_row("Location", f"{audio.lat}, {audio.lon}" if audio.lat else "Unknown")
        table.add_row("Flight Rules", audio.flight_rules)

        return Panel(
            table,
            title=f"🔊 Playing: {audio.id}",
            border_style="green",
            box=box.ROUNDED
        )

    def _generate_history_panel(self) -> Panel:
        """Generate the history panel."""
        table = Table(show_header=True, expand=True, box=None)
        table.add_column("Time", style="dim", width=10)
        table.add_column("Station", style="cyan")
        table.add_column("Pilot", style="white")

        for audio in self.history:
             # Assuming stamp is a string, otherwise format it
             # Ideally we'd parse the timestamp
             stamp = audio.stamp if audio.stamp else "-"
             # If stamp is full ISO string, maybe slice it.
             # For now, just use placeholder if needed.

             table.add_row(stamp[-8:] if stamp else "N/A", audio.station_name, audio.pilot)

        return Panel(
            table,
            title="Recent Transmissions",
            border_style="blue",
            box=box.ROUNDED
        )

    def _generate_footer(self) -> Panel:
        """Generate the footer panel."""
        return Panel(
            Text(self.status_message, style="yellow"),
            title="Status",
            border_style="white",
            box=box.ROUNDED
        )

    def render(self) -> Layout:
        """Render the full layout."""
        self.layout["header"].update(self._generate_header())
        self.layout["current"].update(self._generate_current_panel())
        self.layout["history"].update(self._generate_history_panel())
        self.layout["footer"].update(self._generate_footer())
        return self.layout
