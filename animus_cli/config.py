"""
Animus CLI Configuration and Constants
"""
import os
from pathlib import Path
import sys

# Basic application info
ANIMUS_VERSION = "0.1.0"

# --- Path Setup ---
# Determine if running as a bundled executable (PyInstaller)
IS_BUNDLED = getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS')

# Base directory setup
if IS_BUNDLED:
    # In a bundle, base is the directory containing the executable
    APP_BASE_DIR = Path(sys.executable).parent.resolve()
    # Assume bundled data is relative to the executable or in _MEIPASS
    BUNDLED_DATA_DIR = Path(getattr(sys, '_MEIPASS', APP_BASE_DIR))
else:
    # Running as script, base is the parent of the 'animus_cli' directory
    APP_BASE_DIR = Path(__file__).parent.parent.resolve()
    BUNDLED_DATA_DIR = APP_BASE_DIR # Not bundled, data dir is app base

# Define key directories relative to the determined base
SCRIPT_DIR = BUNDLED_DATA_DIR / "animus_cli"
LOG_COLLECTOR_SCRIPT = SCRIPT_DIR / "scripts" / "collect_logs.ps1"

# Default output path - use LOCALAPPDATA for user-writable logs
DEFAULT_OUTPUT_PATH = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Animus" / "logs" / "animus_logs.json"

# Ensure the default logs directory exists
try:
    DEFAULT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
except OSError:
    print(f"Warning: Could not create default log directory: {DEFAULT_OUTPUT_PATH.parent}", file=sys.stderr)

# Default LLM model
DEFAULT_MODEL_NAME = "gemini-2.5-pro-exp-03-25" 