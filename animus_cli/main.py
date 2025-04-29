#!/usr/bin/env python3
"""
Animus CLI - Main Entry Point
Orchestrates log collection, parsing, and analysis.
"""

import sys
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Import components from other modules
from animus_cli.config import DEFAULT_OUTPUT_PATH, DEFAULT_MODEL_NAME
from animus_cli.cli import AnimusCLI

def check_environment() -> tuple[bool, str]:
    """Check if the environment is properly configured.
    
    Returns:
        Tuple of (success, error_message)
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Check for required API key
    if not os.getenv("GEMINI_API_KEY"):
        return False, "GEMINI_API_KEY environment variable is not set. Please set it in your environment or .env file."
    
    return True, ""

def main():
    """CLI Entry Point."""
    # First check the environment
    env_ok, error_msg = check_environment()
    if not env_ok:
        print(f"Error: {error_msg}", file=sys.stderr)
        return 1

    # Parse minimal arguments (for backward compatibility with the batch file)
    parser = argparse.ArgumentParser(description="Animus - Windows Event Log Analysis CLI")
    parser.add_argument("--output", "-o", type=Path, default=DEFAULT_OUTPUT_PATH,
                       help=f"Path to save log data (default: {DEFAULT_OUTPUT_PATH})")
    parser.add_argument("--interactive", "-i", action="store_true", default=True,
                       help="Start in interactive mode (default: True)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    args = parser.parse_args()
    
    # Set parameters
    log_file_path = args.output
    model_name = DEFAULT_MODEL_NAME
    verbose = args.verbose
    
    # Ensure the log directory exists
    try:
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Error: Could not create output directory: {e}", file=sys.stderr)
        return 1

    # Instantiate the CLI controller
    cli = AnimusCLI(
        output_path=log_file_path,
        model_name=model_name,
        verbose=verbose
    )

    # Collect and load logs
    logs_collected = cli.collect_and_load_logs(
        hours=48,  # Default value
        max_events=500,  # Default value
        force=True  # Always force collection
    )

    # Exit if logs could not be collected
    if not logs_collected:
        print("Error: Could not collect or load logs. Please check the error messages above.", file=sys.stderr)
        return 1

    # Start interactive mode if requested
    if args.interactive:
        if not cli.run_interactive_mode():
            print("Error: Could not start interactive mode. Please check the error messages above.", file=sys.stderr)
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
