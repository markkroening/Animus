#!/usr/bin/env python3
"""
Animus CLI - LLM Manager Module

This module handles the integration with the Google Gemini API 
using the google-genai SDK.
"""

import os
import time
import json
import logging
from typing import Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import google.generativeai as genai

from animus_cli.log_processor import LogProcessor, process_log_file

# Configure logging
logger = logging.getLogger(__name__)

# Load API Key from .env file
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class GeminiAPIError(Exception):
    """Custom exception for Gemini API related errors"""
    pass

class LLMManager:
    """Manager class for Google Gemini API integration"""
    
    def __init__(self, 
                 model_name: str = 'gemini-1.5-flash-latest', 
                 api_key: Optional[str] = None,
                 verbose: bool = False):
        """
        Initialize the LLM Manager for Gemini.
        
        Args:
            model_name: The Gemini model to use (e.g., 'gemini-1.5-flash-latest').
            api_key: Google API Key. If None, uses GEMINI_API_KEY from .env.
            verbose: Whether to show verbose output.
        """
        self.model_name = model_name
        self.api_key = api_key or GEMINI_API_KEY
        self.verbose = verbose
        self.model = None
        self.log_processor = LogProcessor(verbose=verbose)
        
        if not self.api_key:
             raise GeminiAPIError("Gemini API Key not found. Please set GEMINI_API_KEY in your .env file or provide it during initialization.")
             
        # Create the client instance
        try:
            # Configure the API
            genai.configure(api_key=self.api_key)
            
            # Create a generative model instance
            self.model = genai.GenerativeModel(model_name=self.model_name)
            
            if self.verbose:
                 logger.info(f"Using model: {self.model_name}")
        except Exception as e:
             raise GeminiAPIError(f"Failed to create Gemini model: {e}") from e
             
        # System context for prompts
        self.system_context = (
            "You are Animus, an AI assistant analyzing Windows Event Logs. "
            "You have been provided with processed Windows Event Log data and system information. "
            "The data contains summarized information about events from System, Application, and Security logs, "
            "as well as system information and statistics. "
            "Focus on identifying potential issues and suggesting concise, actionable remediation steps based *only* on the provided logs and system info. "
            "If the user asks about Animus itself or greets you, answer directly without analyzing the logs."
        )
        
    def _format_query_content(self, query: str, log_data: Dict[str, Any]) -> str:
         """
         Prepare a string containing processed log data and user query
         """
         # Process the raw log data to make it more LLM-friendly
         try:
             # Process the logs through our new processor
             processed_data = self.log_processor.process_logs(log_data)
             
             # Get the formatted text representation
             formatted_logs = self.log_processor.format_for_llm(processed_data)
             
             if self.verbose:
                 logger.info(f"Processed log data: {len(formatted_logs)} characters")
                 
             # Check if processed logs exceeds size limit
             MAX_LOGS_CHARS = 100000  # Increased limit since processed data should be smaller
             if len(formatted_logs) > MAX_LOGS_CHARS:
                 logger.warning(f"Processed logs truncated from {len(formatted_logs)} to {MAX_LOGS_CHARS} chars")
                 formatted_logs = formatted_logs[:MAX_LOGS_CHARS] + "\n... [truncated due to size limits]"
                 
             # Extract system information for personalized prompt
             sys_info = processed_data.get("SystemInfo", {})
             computer_name = sys_info.get("ComputerName", "this computer")
             os_version = sys_info.get("OSVersion", "Windows")
             
             # Create personalized system context
             personalized_context = (
                 f"You are {computer_name}, a {os_version} computer. "
                 "You have been brought to life by Animus, summoned to answer questions to aid in troubleshooting. "
                 "You have been given access to a collection of the most recent event logs to work with. "
                 "Be technical and concise with your responses, and support your troubleshooting holistically with the events you are given."
             )
                 
         except Exception as e:
             logger.error(f"Error processing logs: {e}")
             # Fallback to using JSON if processing fails
             formatted_logs = json.dumps(log_data, indent=2)[:50000] + "\n... [truncated due to size limits]"
             personalized_context = self.system_context
         
         # Combine all content
         full_prompt = f"{personalized_context}\n\nLog Data:\n{formatted_logs}\n\nUser Query: {query}"
         
         if self.verbose:
             logger.info(f"Total prompt size: {len(full_prompt)} characters")
         
         return full_prompt

    def query_logs(self, query: str, log_data: Dict[str, Any], max_response_tokens: Optional[int] = None) -> Tuple[str, float]:
        """
        Process a query using the Gemini API.
        
        Args:
            query: The user's natural language question.
            log_data: The log data to analyze.
            max_response_tokens: Optional max tokens for the response.

        Returns:
            Tuple of (response text, generation time in seconds).
        """
        if not self.model:
             return "Error: Gemini model not ready.", 0.0
             
        # Prepare content string
        content_prompt = self._format_query_content(query, log_data)
        
        if self.verbose:
             print(f"\n--- Sending Prompt to Gemini ({len(content_prompt)} chars) ---")
             print(f"Query: {query}")
             print("-----------------------------------")

        start_time = time.time()
        try:
            # Configure generation parameters
            generation_config = genai.GenerationConfig(
                temperature=0.2,
                top_p=0.8,
                top_k=40,
                max_output_tokens=max_response_tokens or 2048
            )
            
            # Generate content using the model instance
            response = self.model.generate_content(
                content_prompt,
                generation_config=generation_config
            )
            
            generation_time = time.time() - start_time
            
            # Access response text safely
            try:
                 result_text = response.text
            except ValueError:
                 block_reason = getattr(response.prompt_feedback, 'block_reason', None)
                 block_reason_name = getattr(block_reason, 'name', 'Unknown') if block_reason else 'Unknown'
                 result_text = f"Response blocked by safety filter: {block_reason_name}"
            except AttributeError:
                 result_text = "Error: Could not parse response from Gemini."

            if self.verbose:
                logger.info(f"Gemini response received in {generation_time:.2f} seconds")
                
            return result_text, generation_time

        except Exception as e:
            logger.error(f"Unexpected error during Gemini query: {e}")
            return f"Unexpected error: {e}", 0.0

# Configure logging if module run directly
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') 