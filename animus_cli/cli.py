#!/usr/bin/env python3
"""
Animus CLI - Main Module

This module provides the command-line interface for the Animus log analysis tool.
"""

import os
import sys
import json
import logging
import argparse
from typing import Optional, Dict, Any

from animus_cli.llm_manager import LLMManager, GeminiAPIError
from animus_cli.log_processor import LogProcessor

# Configure logging
log_level = os.environ.get('LOGLEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(message)s'  # Simplified format - just show the message
)
logger = logging.getLogger(__name__)

class AnimusCLI:
    """Main CLI class for Animus"""
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the Animus CLI.
        
        Args:
            verbose: Whether to show verbose output.
        """
        self.verbose = verbose
        self.llm = None
        self.log_processor = LogProcessor(verbose=verbose)
        self.raw_log_data = None
        self.processed_log_data = None
        
        # Set log level based on verbose flag
        if verbose:
            logger.setLevel(logging.DEBUG)
            logging.getLogger('animus_cli').setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.CRITICAL)  # Suppress all logging in non-verbose mode
            logging.getLogger('animus_cli').setLevel(logging.CRITICAL)
        
    def initialize_llm(self) -> None:
        """Initialize the LLM manager"""
        try:
            self.llm = LLMManager(verbose=self.verbose)
            if self.verbose:
                logger.debug("LLM manager initialized successfully")
        except GeminiAPIError as e:
            logger.error(f"Failed to initialize LLM: {e}")
            sys.exit(1)
            
    def load_logs(self, log_file: str) -> None:
        """
        Load and process logs from a file.
        
        Args:
            log_file: Path to the log file to load.
        """
        try:
            # Load raw JSON data
            with open(log_file, 'r') as f:
                self.raw_log_data = json.load(f)
            
            # Process the logs once
            self.processed_log_data = self.log_processor.process_logs(self.raw_log_data)
            
            if self.verbose:
                logger.debug(f"Loaded and processed logs from {log_file}")
                summary = self.processed_log_data.get("EventSummary", {})
                logger.debug(f"Processed {summary.get('TotalEvents', 0)} total events")
                
        except Exception as e:
            logger.error(f"Failed to load or process logs: {e}")
            sys.exit(1)
            
    def process_query(self, query: str) -> None:
        """
        Process a natural language query using the LLM.
        
        Args:
            query: The natural language query to process.
        """
        if not self.processed_log_data:
            error_msg = "No logs loaded. Please load logs first."
            logger.error(error_msg)
            print(f"\nError: {error_msg}")
            return
            
        if not self.llm:
            self.initialize_llm()
            
        try:
            # Query the LLM with the pre-processed log data
            response_text, generation_time = self.llm.query_logs(query, self.processed_log_data)
            
            # Check for error messages in the response
            if response_text.startswith("Error:"):
                print(f"\n{response_text}")
                if self.verbose:
                    print(f"Query took {generation_time:.2f} seconds")
            else:
                print(f"\n{response_text}")
                if self.verbose:
                    print(f"Query took {generation_time:.2f} seconds")
            
        except Exception as e:
            error_msg = f"Error processing query: {e}"
            logger.error(error_msg)
            if self.verbose:
                import traceback
                logger.error(traceback.format_exc())
            print(f"\nError: {error_msg}")
                
def main():
    """Main entry point for the CLI"""
    parser = argparse.ArgumentParser(description="Animus Log Analysis Tool")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--log-file", help="Path to log file to analyze")
    parser.add_argument("--query", help="Natural language query to process")
    
    args = parser.parse_args()
    
    cli = AnimusCLI(verbose=args.verbose)
    
    if args.log_file:
        cli.load_logs(args.log_file)
        
    if args.query:
        cli.process_query(args.query)
    else:
        # Interactive mode
        if args.verbose:
            print("\n==============================")
            print(" Animus Log Analysis Tool")
            print("==============================")
            print("Using model: gemini-2.5-pro-exp-03-25")
            print("Type 'exit' or 'quit' to end session.\n")
        
        while True:
            try:
                query = input("Animus> ")
                if query.lower() in ('exit', 'quit'):
                    break
                    
                cli.process_query(query)
                
            except KeyboardInterrupt:
                if args.verbose:
                    print("\nExiting...")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                if args.verbose:
                    import traceback
                    logger.error(traceback.format_exc())
                    
if __name__ == "__main__":
    main() 