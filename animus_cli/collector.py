"""
Handles the collection of Windows Event Logs via PowerShell.
"""

import subprocess
import sys
import os
import time
from pathlib import Path

from animus_cli.config import LOG_COLLECTOR_SCRIPT


def collect_logs(
    output_path: Path,
    hours_back: int = 48,
    max_events: int = 500
) -> bool:
    """Call the PowerShell script to collect Windows Event Logs (system and application only).

    Args:
        output_path: The Path object where the JSON log file will be saved.
        hours_back: How many hours of logs to retrieve.
        max_events: Maximum number of events per log type.

    Returns:
        True if the log collection script appears to have run successfully
        and created a non-empty output file, False otherwise.
    """
    script_path_str = str(LOG_COLLECTOR_SCRIPT.resolve())
    output_path_str = str(output_path.resolve())

    # Basic check if the script exists
    if not LOG_COLLECTOR_SCRIPT.exists():
        print(f"Error: Log collector script not found at {script_path_str}", file=sys.stderr)
        return False

    # Ensure output directory exists
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error: Could not create output directory {output_path.parent}: {e}", file=sys.stderr)
        return False

    # Construct the PowerShell command
    powershell_cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", script_path_str,
        "-OutputFile", output_path_str,
        "-HoursBack", str(hours_back),
        "-MaxEvents", str(max_events)
    ]

    try:
        # Run the PowerShell script
        result = subprocess.run(
            powershell_cmd,
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode != 0:
            print(f"Error running log collector script (Exit Code: {result.returncode}).", file=sys.stderr)
            if result.stderr:
                print(f"PowerShell Error Output:\n{result.stderr.strip()}", file=sys.stderr)
            if result.stdout:
                 print(f"PowerShell Standard Output:\n{result.stdout.strip()}", file=sys.stderr)
            return False

        # Brief pause to allow file system operations to complete
        time.sleep(0.5)

        # Basic check: Did the file get created and is it non-empty?
        if not output_path.exists() or output_path.stat().st_size == 0:
            print(f"Error: Log file was not created or is empty at {output_path_str}", file=sys.stderr)
            # Provide stdout/stderr again in case it has clues
            if result.stdout:
                 print(f"PowerShell Standard Output:\n{result.stdout.strip()}", file=sys.stderr)
            if result.stderr:
                print(f"PowerShell Error Output:\n{result.stderr.strip()}", file=sys.stderr)
            return False

        print(f"Log collection script finished. Output saved to: {output_path_str}")
        return True

    except FileNotFoundError:
        print("Error: 'powershell' command not found. Is PowerShell installed and in PATH?", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error occurred during log collection: {e}", file=sys.stderr)
        return False 