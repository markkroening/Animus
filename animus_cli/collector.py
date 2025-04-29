"""
Windows Event Log collector using PowerShell.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

def get_script_path() -> Path:
    """Determine the correct path to collect_logs.ps1 whether running from source or bundled."""
    if getattr(sys, 'frozen', False):
        # Running as a bundled/frozen executable
        if hasattr(sys, '_MEIPASS'):
             # PyInstaller bundle
             base_path = Path(sys._MEIPASS)
        else:
             # Other bundled executable (generic case)
             base_path = Path(sys.executable).parent
             
        # Check relative to executable base path
        script_path = base_path / "scripts" / "collect_logs.ps1"
        if script_path.exists():
            return script_path
            
        # Fallback: check alongside executable
        alt_path = base_path / "collect_logs.ps1"
        if alt_path.exists():
            return alt_path
            
        # If still not found, return the primary expected path for error reporting
        return base_path / "scripts" / "collect_logs.ps1" 
        
    else:
        # Running from source OR as an installed script (not frozen)
        collector_dir = Path(__file__).parent # This is {app}\animus_cli when installed
        install_base_dir = collector_dir.parent # This should be {app} when installed
        
        # Check path relative to install base dir (preferred when installed)
        installed_script_path = install_base_dir / "scripts" / "collect_logs.ps1"
        if installed_script_path.exists():
            return installed_script_path
            
        # Fallback: Check path relative to collector.py (for running from source)
        source_script_path = collector_dir / "scripts" / "collect_logs.ps1"
        if source_script_path.exists():
            return source_script_path
            
        # If neither found, return the path expected for the installed version for error reporting
        return installed_script_path

def collect_logs(
    output_path: Path,
    hours_back: int = 24,
    max_events: int = 1000,
) -> bool:
    """Collect Windows Event Logs using PowerShell.

    Args:
        output_path: Path to save the collected logs.
        hours_back: Number of hours of logs to collect.
        max_events: Maximum number of events to collect per log type.

    Returns:
        True if collection was successful, False otherwise.
    """
    script_path = get_script_path()

    if not script_path.exists():
        # Try to provide more context about where it looked
        search_dir = script_path.parent
        print(f"Error: Log collector script 'collect_logs.ps1' not found in expected location: {search_dir}", file=sys.stderr)
        if getattr(sys, 'frozen', False):
            print("Info: When running as an executable, the script should be bundled within or alongside it (e.g., in a 'scripts' subdirectory).", file=sys.stderr)
        else:
            print(f"Info: When running from source, expected script relative to: {Path(__file__).parent}", file=sys.stderr)
        return False

    # Ensure output directory exists
    output_dir = output_path.parent
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Error creating output directory: {e}", file=sys.stderr)
        return False

    # Construct PowerShell command
    ps_command = [
        "powershell.exe",
        "-ExecutionPolicy", "Bypass",
        "-File", str(script_path),
        "-OutputPath", str(output_path),
        "-HoursBack", str(hours_back),
        "-MaxEvents", str(max_events)
    ]

    try:
        # Run PowerShell script
        result = subprocess.run(
            ps_command,
            capture_output=True,
            text=True,
            check=True # Restore check=True
        )

        # Check if the output file was created and is not empty
        if not output_path.exists():
            print("Error: Log file was not created", file=sys.stderr)
            return False

        if output_path.stat().st_size == 0:
            print("Error: Log file is empty", file=sys.stderr)
            return False

        return True

    except subprocess.CalledProcessError as e:
        print(f"Error running PowerShell script: {e}", file=sys.stderr)
        if e.stderr:
            print(f"PowerShell error: {e.stderr}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error collecting logs: {e}", file=sys.stderr)
        return False 