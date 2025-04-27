"""
Core Animus CLI interaction class.
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional

from animus_cli.data_models import LogCollection
from animus_cli.parser import LogParser
from animus_cli.collector import collect_logs
from animus_cli.llm_manager import LLMManager, GeminiAPIError
from animus_cli.config import ANIMUS_BANNER, DEFAULT_MODEL_NAME

class AnimusCLI:
    """Handles the main CLI logic for loading, collecting, and querying logs."""

    def __init__(
        self,
        output_path: Path,
        model_name: str = DEFAULT_MODEL_NAME,
        verbose: bool = False,
    ):
        """Initialize the CLI.

        Args:
            output_path: Path to the log JSON file.
            model_name: Name of the Gemini model to use.
            verbose: Enable verbose output (primarily for LLM).
        """
        self.output_path = output_path
        self.model_name = model_name
        self.verbose = verbose
        self.log_collection: Optional[LogCollection] = None
        self.llm: Optional[LLMManager] = None
        self.running = False

    def _ensure_llm(self) -> bool:
        """Initialize the LLMManager if not already done."""
        if self.llm is None:
            try:
                print("Initializing LLM...", file=sys.stderr)
                # Check for API key before initializing
                if not os.getenv("GEMINI_API_KEY"):
                     print("Warning: GEMINI_API_KEY not found in environment.", file=sys.stderr)
                     print("         Please set the environment variable for AI analysis.", file=sys.stderr)
                     return False
                self.llm = LLMManager(model_name=self.model_name, verbose=self.verbose)
                print("LLM initialized.", file=sys.stderr)
                return True
            except GeminiAPIError as e:
                print(f"Error initializing LLM: {e}", file=sys.stderr)
                print("AI analysis features will be unavailable.", file=sys.stderr)
                return False
            except Exception as e:
                print(f"Unexpected error initializing LLM: {e}", file=sys.stderr)
                return False
        return True

    def load_logs(self) -> bool:
        """Load logs from the configured output path.

        Returns:
            True if logs were loaded successfully, False otherwise.
        """
        print(f"Attempting to load logs from {self.output_path}...", file=sys.stderr)
        self.log_collection = LogParser.parse_file(self.output_path)
        if self.log_collection:
            count = self.log_collection.event_count['total']
            print(f"Loaded {count} events.", file=sys.stderr)
            return True
        else:
            # Error message is printed by LogParser.parse_file
            # print("Failed to load logs.", file=sys.stderr)
            return False

    def collect_and_load_logs(
        self, hours: int, max_events: int, force: bool
    ) -> bool:
        """Collect logs using the PowerShell script and then load them.

        Args:
            hours: Hours of logs to collect.
            max_events: Max events per log type.
            force: Force collection even if recent logs exist (ignored here).

        Returns:
            True if collection and loading were successful, False otherwise.
        """
        print(f"Starting log collection...", file=sys.stderr)
        collection_successful = collect_logs(
            output_path=self.output_path,
            hours_back=hours,
            max_events=max_events
        )

        if collection_successful:
            return self.load_logs()
        else:
            print("Log collection failed.", file=sys.stderr)
            return False

    def show_status(self):
        """Display basic status of the loaded logs."""
        if not self.log_collection:
            print("No logs loaded. Use 'load' or 'collect'.")
            return

        summary = self.log_collection.get_summary()
        print("\n--- Log Status ---")
        print(f"Collected: {summary['collection_time']}")
        print(f"Range: {summary['time_range'].get('StartTime', 'N/A')} - {summary['time_range'].get('EndTime', 'N/A')}")
        counts = summary['event_counts']
        print(f"Events: Total={counts['total']}, Errors={counts['errors']}, Warnings={counts['warnings']}")
        sys_summary = summary['system_summary']
        print(f"System: {sys_summary['os']} on {sys_summary['computer']} ({sys_summary['model']}), Uptime: {sys_summary['uptime']}")
        print("------------------\n")


    def process_query(self, query: str):
        """Process a natural language query using the LLM.

        Args:
            query: The user's question.
        """
        if not self.log_collection:
            print("Error: No logs loaded to query. Use 'load' or 'collect'.")
            return

        if not self._ensure_llm() or not self.llm:
            print("Error: LLM is not available. Cannot process query.")
            # Basic fallback can be added here if needed, but kept minimal per request
            print("Basic response: LLM unavailable.")
            return

        print("Sending query to LLM...", file=sys.stderr)
        try:
            # Read the raw log data again for the LLM context
            # This avoids holding the potentially large raw data in memory constantly
            # Assume parser used utf-8-sig successfully if logs were loaded
            with open(self.output_path, 'r', encoding='utf-8-sig') as f:
                raw_log_data = json.load(f)

            response, gen_time = self.llm.query_logs(
                query=query,
                log_data=raw_log_data,
            )
            if self.verbose:
                print(f"LLM generation took {gen_time:.2f}s", file=sys.stderr)

            # Print the LLM response directly
            print(f"\n{response}\n")

        except FileNotFoundError:
             print(f"Error: Log file not found at {self.output_path} during query.")
        except json.JSONDecodeError:
             print(f"Error: Could not decode JSON from {self.output_path} during query.")
        except GeminiAPIError as e:
            print(f"Error querying LLM: {e}")
        except Exception as e:
            print(f"An unexpected error occurred during query processing: {e}")

    def run_interactive_mode(self):
        """Start the interactive Q&A loop."""
        if not self.log_collection:
            print("No logs loaded. Cannot start interactive mode.", file=sys.stderr)
            print("Please load or collect logs first.", file=sys.stderr)
            return # Exit if no logs

        print(ANIMUS_BANNER)
        self.show_status() # Show status once at the start
        print("Entering interactive Q&A mode. Type your questions or 'exit'/'quit'.")
        print(f"Using model: {self.model_name}")

        self.running = True
        while self.running:
            try:
                user_input = input("Animus> ").strip()

                if not user_input:
                    continue

                cmd_lower = user_input.lower()
                if cmd_lower in ["exit", "quit"]:
                    self.running = False
                    break
                elif cmd_lower == "status":
                    self.show_status()
                elif cmd_lower == "help":
                     print("Available commands: status, help, exit/quit, or enter your question.")
                # Add collect/load commands if desired, or handle them before starting interactive mode
                # elif user_input.startswith("collect"):
                #    pass # Add argument parsing for collect
                # elif user_input.startswith("load"):
                #    pass # Add argument parsing for load
                else:
                    # Treat any other input as a query
                    self.process_query(user_input)

            except (KeyboardInterrupt, EOFError):
                print() # Newline for clean exit
                self.running = False
                break
            except Exception as e:
                print(f"An error occurred in the interactive loop: {e}")
                # Decide whether to continue or exit on error
                # self.running = False

        print("Exiting Animus CLI.") 