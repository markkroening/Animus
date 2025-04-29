"""
Core Animus CLI interaction class.
"""

import json
import sys
import os
from pathlib import Path
from typing import Optional, Tuple

from animus_cli.data_models import LogCollection
from animus_cli.parser import LogParser
from animus_cli.collector import collect_logs
from animus_cli.llm_manager import LLMManager, GeminiAPIError
from animus_cli.config import DEFAULT_MODEL_NAME

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

    def _ensure_llm(self) -> Tuple[bool, Optional[str]]:
        """Initialize the LLMManager if not already done.
        
        Returns:
            Tuple of (success, error_message)
        """
        if self.llm is None:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return False, "GEMINI_API_KEY environment variable is not set"
            
            try:
                self.llm = LLMManager(model_name=self.model_name, verbose=self.verbose)
                return True, None
            except GeminiAPIError as e:
                return False, f"Failed to initialize Gemini API: {e}"
            except Exception as e:
                return False, f"Unexpected error initializing LLM: {e}"
        return True, None

    def load_logs(self) -> bool:
        """Load logs from the configured output path.

        Returns:
            True if logs were loaded successfully, False otherwise.
        """
        try:
            self.log_collection = LogParser.parse_file(self.output_path)
            if not self.log_collection:
                print("Error: No logs found in the log file.", file=sys.stderr)
                return False
            return True
        except FileNotFoundError:
            print(f"Error: Log file not found at {self.output_path}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"Error: Failed to load logs: {e}", file=sys.stderr)
            return False

    def collect_and_load_logs(
        self, hours: int, max_events: int, force: bool
    ) -> bool:
        """Collect logs using the PowerShell script and then load them.

        Args:
            hours: Hours of logs to collect.
            max_events: Max events per log type.
            force: Force collection even if recent logs exist.

        Returns:
            True if collection and loading were successful, False otherwise.
        """
        collection_successful = collect_logs(
            output_path=self.output_path,
            hours_back=hours,
            max_events=max_events
        )

        if not collection_successful:
            print("Error: Failed to collect logs.", file=sys.stderr)
            return False
            
        return self.load_logs()

    def process_query(self, query: str) -> bool:
        """Process a natural language query using the LLM.

        Args:
            query: The user's question.
            
        Returns:
            True if query was processed successfully, False otherwise.
        """
        if not self.log_collection:
            print("Error: No logs loaded to query.", file=sys.stderr)
            return False

        llm_success, error_msg = self._ensure_llm()
        if not llm_success:
            print(f"Error: {error_msg}", file=sys.stderr)
            return False

        try:
            # No need to reload raw data, use the parsed log_collection
            # with open(self.output_path, 'r', encoding='utf-8-sig') as f:
            #     raw_log_data = json.load(f)

            response, _ = self.llm.query_logs(
                query=query,
                log_collection=self.log_collection, # Pass the LogCollection object
            )
            print(f"\n{response}\n")
            return True

        except FileNotFoundError:
            print(f"Error: Log file not found at {self.output_path}", file=sys.stderr)
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {self.output_path}", file=sys.stderr)
        except GeminiAPIError as e:
            print(f"Error querying LLM: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing query: {e}", file=sys.stderr)
        return False

    def run_interactive_mode(self) -> bool:
        """Start the interactive Q&A loop.
        
        Returns:
            True if interactive mode was started successfully, False otherwise.
        """
        if not self.log_collection:
            print("Error: No logs loaded. Cannot start interactive mode.", file=sys.stderr)
            return False

        # Verify LLM is available before starting interactive mode
        llm_success, error_msg = self._ensure_llm()
        if not llm_success:
            print(f"Error: Cannot start interactive mode - {error_msg}", file=sys.stderr)
            return False

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
                elif cmd_lower == "help":
                    print("Available commands:")
                    print("  help        - Show this help message")
                    print("  exit, quit  - Exit interactive mode")
                    print("  <question>  - Ask a question about the logs")
                else:
                    self.process_query(user_input)

            except (KeyboardInterrupt, EOFError):
                print("\nExiting interactive mode.")
                self.running = False
                break
            except Exception as e:
                print(f"Error in interactive mode: {e}", file=sys.stderr)
                self.running = False
                break
        
        return True 