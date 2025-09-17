# Testing Branch for PYATC Scanner Live

This document describes the new `testing-scanner-live` branch created for testing the PYATC scanner functionality.

## Branch Information

- **Branch Name**: `testing-scanner-live`
- **Created From**: Main branch (commit `2772f9f`)
- **Purpose**: Testing branch for scanner live functionality
- **Current Status**: Ready for testing

## Branch Creation Process

1. Created new branch from main branch commit `2772f9f`
2. Merged changes from `copilot/fix-e195750d-d5d8-41fb-989f-b1889ac487c1` branch
3. Fast-forward merge was successful with no conflicts

## How to Use This Branch

```bash
# Switch to the testing branch
git checkout testing-scanner-live

# Or clone directly to this branch
git clone -b testing-scanner-live https://github.com/Open-Auereus/PYATC.git

# Install dependencies (example)
pip install sounddevice numpy requests python-dotenv pydub websocket-client

# Run the scanner
python3 scanner_live.py --help
```

## Current Code State

The testing branch contains:
- Enhanced Real-Time Aviation Scanner with WebSocket support
- Lower latency audio streaming capabilities 
- Configurable audio playback backends
- Geographic filtering options
- VFR-only traffic filtering

## Testing Checklist

- [ ] Test basic scanner functionality
- [ ] Test audio playback with different backends
- [ ] Test WebSocket connectivity
- [ ] Test geographic filtering
- [ ] Test VFR-only mode
- [ ] Test configuration file loading
- [ ] Test command-line arguments

## Notes

This branch is specifically created for testing purposes and can be safely used for experimentation without affecting the main branch.