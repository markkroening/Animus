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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
        self.log_data = None
        
    def initialize_llm(self) -> None:
        """Initialize the LLM manager"""
        try:
            self.llm = LLMManager(verbose=self.verbose)
            if self.verbose:
                logger.info("LLM manager initialized successfully")
        except GeminiAPIError as e:
            logger.error(f"Failed to initialize LLM: {e}")
            sys.exit(1)
            
    def load_logs(self, log_file: str) -> None:
        """
        Load logs from a file.
        
        Args:
            log_file: Path to the log file to load.
        """
        try:
            with open(log_file, 'r') as f:
                self.log_data = json.load(f)
            if self.verbose:
                logger.info(f"Loaded logs from {log_file}")
        except Exception as e:
            logger.error(f"Failed to load logs: {e}")
            sys.exit(1)
            
    def process_query(self, query: str) -> None:
        """
        Process a natural language query using the LLM.
        
        Args:
            query: The natural language query to process.
        """
        if not self.log_data:
            logger.error("No logs loaded. Please load logs first.")
            return
            
        if not self.llm:
            self.initialize_llm()
            
        try:
            # Process logs and format for LLM
            processed_data = self.log_processor.process_logs(self.log_data)
            formatted_data = self.log_processor.format_for_llm(processed_data)
            
            # Query the LLM
            response = self.llm.query_logs(query, formatted_data)
            print("\nResponse:")
            print(response)
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            if self.verbose:
                import traceback
                logger.error(traceback.format_exc())
                
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
        print("Animus Log Analysis Tool")
        print("Type 'exit' to quit")
        
        while True:
            try:
                query = input("\nEnter your query: ")
                if query.lower() == 'exit':
                    break
                    
                cli.process_query(query)
                
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                if args.verbose:
                    import traceback
                    logger.error(traceback.format_exc())
                    
if __name__ == "__main__":
    main() 