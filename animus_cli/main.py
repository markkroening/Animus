#!/usr/bin/env python3
"""
Animus CLI - Main Entry Point
Orchestrates log collection, parsing, and analysis.
"""

import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Import components from other modules
from animus_cli.config import DEFAULT_OUTPUT_PATH, DEFAULT_MODEL_NAME
from animus_cli.cli import AnimusCLI

# Load environment variables from .env file (especially GEMINI_API_KEY)
load_dotenv()

def main():
    """CLI Entry Point."""
    # Parse minimal arguments (for backward compatibility with the batch file)
    parser = argparse.ArgumentParser(description="Animus - Windows Event Log Analysis CLI")
    parser.add_argument("--output", "-o", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--interactive", "-i", action="store_true", default=True)
    args = parser.parse_args()
    
    # Set parameters
    log_file_path = args.output
    model_name = DEFAULT_MODEL_NAME
    verbose = False
    
    # Ensure the log directory exists
    try:
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not ensure output directory exists: {e}", file=sys.stderr)
        # Proceed anyway, collector/parser might handle it or fail

    # Instantiate the CLI controller
    cli = AnimusCLI(
        output_path=log_file_path,
        model_name=model_name,
        verbose=verbose
    )

    # Always collect fresh logs
    print("Collecting fresh logs...")
    logs_collected = cli.collect_and_load_logs(
        hours=48,  # Default value
        max_events=500,  # Default value
        include_security=True,  # Always include security logs
        force=True  # Always force collection
    )

    # Exit if logs could not be collected
    if not logs_collected:
        print("Error: Could not collect logs. Exiting.", file=sys.stderr)
        return 1

    # Always start in interactive mode
    cli.run_interactive_mode()
    return 0

if __name__ == "__main__":
    sys.exit(main())
