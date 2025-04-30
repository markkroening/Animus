"""
Windows Event Log collector using PowerShell (Refactored).
Handles finding the PowerShell script in different execution contexts
and runs it to collect logs.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, NoReturn # Added NoReturn for exit helper

# --- Helper Function (Optional but good practice) ---
def _exit_with_error(message: str, exit_code: int = 1) -> NoReturn:
    """Prints an error message to stderr and exits."""
    print(f"[ERROR] Collector: {message}", file=sys.stderr)
    sys.exit(exit_code)

# --- Path Finding ---
def get_script_path() -> Path:
    """
    Determine the correct path to collect_logs.ps1, handling both
    running from source and as a bundled/frozen executable.
    """
    script_name = "collect_logs.ps1"
    sub_dir = "scripts" # Expected subdirectory name

    if getattr(sys, 'frozen', False):
        # --- Running as a bundled executable ---
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller bundle: _MEIPASS is the temporary directory
            base_path = Path(sys._MEIPASS)
        else:
            # General bundled executable: assume relative to executable
            base_path = Path(sys.executable).parent

        # Check 1: In 'scripts' subdirectory relative to base path
        frozen_path1 = base_path / sub_dir / script_name
        if frozen_path1.is_file():
            return frozen_path1

        # Check 2: Directly alongside the executable/base path
        frozen_path2 = base_path / script_name
        if frozen_path2.is_file():
            return frozen_path2

        # If not found, return the primary expected path for accurate error reporting below
        return frozen_path1

    else:
        # --- Running from source or installed ---
        # First check if we're running from an installed location
        installed_path = Path(r"C:\Program Files (x86)\Animus CLI") / sub_dir / script_name
        if installed_path.is_file():
            return installed_path

        # If not installed, check source paths
        # Assume this structure:
        # {project_root}/
        #   animus_cli/
        #     collector.py  <-- __file__ is here
        #   scripts/
        #     collect_logs.ps1 <-- Target
        source_path = Path(__file__).parent.parent / sub_dir / script_name
        if source_path.is_file():
            return source_path

        # Fallback: Check path relative to this file's directory (less likely structure)
        alt_source_path = Path(__file__).parent / sub_dir / script_name
        if alt_source_path.is_file():
             return alt_source_path

        # If not found, return the installed path for accurate error reporting
        return installed_path

# --- Main Collection Function ---
def collect_logs(
    output_path: Path,
    hours_back: int = 48, # Default defined here, but main.py value takes precedence
    max_events: int = 500, # Default defined here, but main.py value takes precedence
    verbose: bool = False # Added verbose flag
) -> bool:
    """Collect Windows Event Logs using the PowerShell script.

    Args:
        output_path: Path to save the collected logs JSON file.
        hours_back: Number of hours of logs to collect.
        max_events: Maximum number of events to collect per log type.
        verbose: Whether to print verbose output.

    Returns:
        True if collection was successful, False otherwise.
    """
    script_path = get_script_path()

    if not script_path.is_file(): # Use is_file() for more specific check
        # Error message now uses the calculated expected path
        print(f"[ERROR] Log collector script '{script_name}' not found.", file=sys.stderr)
        print(f"        Expected location based on execution context: {script_path}", file=sys.stderr)
        if getattr(sys, 'frozen', False):
            print("        Info: When running as executable, script should be in a '{sub_dir}' subdir or alongside.", file=sys.stderr)
        else:
            print(f"        Info: When running from source, expected script relative to project root.", file=sys.stderr)
        return False

    # Ensure output directory exists before running script
    output_dir = output_path.parent
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        if verbose:
             print(f"[INFO] Collector: Ensured output directory exists: {output_dir}")
    except Exception as e:
        print(f"[ERROR] Collector: Error creating output directory '{output_dir}': {e}", file=sys.stderr)
        return False

    # Construct PowerShell command - USE CORRECT PARAM NAME and add -NoProfile
    ps_command = [
        "powershell.exe",
        "-NoProfile",                 # Add for cleaner/faster execution
        "-ExecutionPolicy", "Bypass",
        "-File", str(script_path),
        "-OutputPath", str(output_path),
        "-HoursBack", str(hours_back),
        "-MaxEventsPerLog", str(max_events) # Corrected parameter name
    ]

    if verbose:
        print(f"[INFO] Collector: Running command: {' '.join(ps_command)}")

    try:
        # Run PowerShell script
        result = subprocess.run(
            ps_command,
            capture_output=True,    # Capture streams
            text=True,              # Decode as text
            check=True,             # Raise CalledProcessError on non-zero exit code
            encoding='utf-8'        # Explicitly decode using utf-8
        )
        if verbose:
             print(f"[INFO] Collector: PowerShell script completed successfully.")
             if result.stdout: # Print stdout only if verbose and non-empty
                  print("[INFO] Collector PS STDOUT:", result.stdout)

        # Check if the output file was created and is not empty *after* success
        if not output_path.is_file(): # is_file() is better than exists() here
            print(f"Error: Log file was not created by the script at '{output_path}'", file=sys.stderr)
            return False
        # Check size AFTER confirming existence
        if output_path.stat().st_size == 0:
            print(f"Warning: Log file '{output_path}' was created but is empty.", file=sys.stderr)
            # Decide if empty file is an error or just means no events found
            # return False # Uncomment if an empty file should be treated as an error
            return True # Assume empty file is okay (maybe no events in timeframe)

        if verbose:
            print(f"[SUCCESS] Collector: Logs collected to '{output_path}'.")
        return True

    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Collector: PowerShell script failed (Exit Code {e.returncode}): {e}", file=sys.stderr)
        # stderr and stdout are already included in the exception object's string representation
        # but printing them explicitly can be helpful
        if e.stdout:
            print("--- PowerShell STDOUT ---", file=sys.stderr)
            print(e.stdout, file=sys.stderr)
            print("-------------------------", file=sys.stderr)
        if e.stderr:
            print("--- PowerShell STDERR ---", file=sys.stderr)
            print(e.stderr, file=sys.stderr)
            print("-------------------------", file=sys.stderr)
        return False
    except FileNotFoundError:
         # This catches if 'powershell.exe' itself isn't found
         _exit_with_error(f"Powershell execution failed. Is 'powershell.exe' in your system's PATH?")
    except Exception as e:
        # Catch other potential errors like permission issues during run
        print(f"[ERROR] Collector: An unexpected error occurred running PowerShell script: {e}", file=sys.stderr)
        return False

# Example Usage (if run directly, though usually called from main.py)
if __name__ == "__main__":
    print("Running collector directly for testing...")
    # Create a dummy output path relative to this script
    test_output_dir = Path(__file__).parent.parent / "output_test"
    test_output_file = test_output_dir / "test_animus_logs.json"
    print(f"Test output will be saved to: {test_output_file}")

    # Use default hours/max_events for test
    success = collect_logs(test_output_file, verbose=True)

    if success:
        print("\nCollector test finished successfully.")
        # Check if file exists and has content
        if test_output_file.is_file() and test_output_file.stat().st_size > 0:
             print(f"Output file '{test_output_file}' created and contains data.")
        elif test_output_file.is_file():
             print(f"Output file '{test_output_file}' created but is empty (possibly no events found).")
        else:
             print(f"Output file '{test_output_file}' was NOT created.")

        # Optionally try reading the first few lines
        try:
            with open(test_output_file, 'r', encoding='utf-8') as f:
                print("\nFirst 5 lines of output file:")
                for i, line in enumerate(f):
                    if i >= 5: break
                    print(line.strip())
        except Exception as e:
            print(f"Could not read test output file: {e}")

    else:
        print("\nCollector test failed.")
        sys.exit(1)

    sys.exit(0)