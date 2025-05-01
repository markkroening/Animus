#!/usr/bin/env python3
"""
Animus CLI - Main Entry Point
Orchestrates log collection, processing, and interaction with the LLM.
"""

import sys
import os
import subprocess
import json
from pathlib import Path
import argparse
from typing import Optional, Tuple, NoReturn

# Import components and default config values
from animus_cli.config import DEFAULT_OUTPUT_PATH, DEFAULT_MODEL_NAME, LOG_COLLECTOR_SCRIPT
from animus_cli.cli import AnimusCLI

# --- Configuration ---
SCRIPT_DIR = Path(__file__).parent
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Default Settings ---
DEFAULT_HOURS_BACK = 168
DEFAULT_MAX_EVENTS = 500
DEFAULT_VERBOSE = False
DEFAULT_SKIP_COLLECTION = False

# --- Helper Functions ---

def exit_with_error(message: str, exit_code: int = 1) -> NoReturn:
    """Prints an error message to stderr and exits."""
    print(f"[ERROR] {message}", file=sys.stderr)
    sys.exit(exit_code)

def check_api_key() -> None:
    """Checks if the required API key environment variable is set."""
    if not GEMINI_API_KEY:
        exit_with_error(
            "GEMINI_API_KEY environment variable not set. "
            "Please set this environment variable before running the application."
        )

def run_log_collector(output_path: Path, hours_back: int, max_events: int, verbose: bool) -> bool:
    """Runs the PowerShell script to collect logs."""
    if not LOG_COLLECTOR_SCRIPT.is_file():
        if verbose:
            print(f"[WARN] Log collector script not found at expected location: {LOG_COLLECTOR_SCRIPT}", file=sys.stderr)
            print("[WARN] Skipping log collection. Attempting to use existing log file if available.", file=sys.stderr)
        return True

    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", str(LOG_COLLECTOR_SCRIPT),
        "-OutputPath", str(output_path),
        "-HoursBack", str(hours_back),
        "-MaxEventsPerLog", str(max_events)
    ]

    if verbose:
        print(f"[INFO] Running log collector script: {' '.join(command)}")

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False
        )

        if verbose and result.stdout:
            print("[INFO] Log Collector STDOUT:")
            print(result.stdout)
        if result.stderr:
            print("[ERROR] Log Collector STDERR:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)

        if result.returncode != 0:
            print(f"[ERROR] Log collector script failed with exit code {result.returncode}.", file=sys.stderr)
            return False

        if verbose:
            print(f"[SUCCESS] Log collector script finished successfully. Output at: {output_path}")
        return True

    except FileNotFoundError:
        exit_with_error(f"Powershell execution failed. Is 'powershell.exe' in your system's PATH?")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred running log collection script: {e}", file=sys.stderr)
        return False

# --- Main Application Logic ---

def main() -> int:
    """CLI Entry Point."""
    parser = argparse.ArgumentParser(description="Animus Log Analysis Tool")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    args = parser.parse_args()

    # 1. Check Environment (API Key)
    check_api_key()

    # 2. Set Parameters
    log_file_path = Path(DEFAULT_OUTPUT_PATH)
    verbose = args.verbose
    hours_back = DEFAULT_HOURS_BACK
    max_events = DEFAULT_MAX_EVENTS
    skip_collection = DEFAULT_SKIP_COLLECTION

    if verbose:
        print("[INFO] Using settings:")
        print(f"  Log Path: {log_file_path}")
        print(f"  Hours Back: {hours_back}")
        print(f"  Max Events/Log: {max_events}")
        print(f"  Skip Collection: {skip_collection}")
        print(f"  Verbose: {verbose}")

    # 3. Ensure Output Directory Exists
    try:
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        if verbose:
            print(f"[INFO] Ensured log output directory exists: {log_file_path.parent}")
    except Exception as e:
        exit_with_error(f"Could not create output directory '{log_file_path.parent}': {e}")

    # 4. Collect Logs (unless skipped)
    if not skip_collection:
        if verbose:
            print("[INFO] Starting log collection...")
        if not run_log_collector(log_file_path, hours_back, max_events, verbose):
            return 1
    elif verbose:
        print("[INFO] Skipping log collection (using default setting or config).")

    # 5. Instantiate and Run CLI
    try:
        if verbose:
            print(f"[INFO] Initializing AnimusCLI (Model: {DEFAULT_MODEL_NAME})...")
        cli = AnimusCLI(verbose=verbose)

        if verbose:
            print(f"[INFO] Loading logs from: {log_file_path}")
        cli.load_logs(str(log_file_path))
        if verbose:
            print("[SUCCESS] Logs loaded successfully.")

    except FileNotFoundError:
        exit_with_error(f"Log file not found at '{log_file_path}'. Cannot proceed.")
    except Exception as e:
        print(f"[ERROR] Failed to initialize or load logs: {e}", file=sys.stderr)
        if verbose:
            import traceback
            traceback.print_exc()
        return 1

    # 6. Start Interactive Loop
    print("\nAnimus> ", end="", flush=True)

    while True:
        try:
            query = input()
            if query.lower() in ['exit', 'quit']:
                break
            if not query:
                print("Animus> ", end="", flush=True)
                continue

            cli.process_query(query)
            print("\nAnimus> ", end="", flush=True)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[ERROR] An error occurred during query processing: {e}", file=sys.stderr)
            if verbose:
                import traceback
                traceback.print_exc()
            print("\nAnimus> ", end="", flush=True)

    return 0

# --- Entry Point Check ---
if __name__ == "__main__":
    sys.exit(main())