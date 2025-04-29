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
from typing import Optional, Tuple
from dotenv import load_dotenv
import google.generativeai as genai
import sys

from animus_cli.log_processor import LogProcessor, process_log_file
from animus_cli.data_models import LogCollection, SystemInfo, EventLogEntry

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
                 model_name: str = 'gemini-2.5-flash-preview-04-17', 
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
             
    def _format_query_content(self, query: str, log_collection: LogCollection) -> str:
         """
         Prepare a string containing processed log data and user query in a structured format
         """
         # Process the raw log data to make it more LLM-friendly
         try:            
             # Use LogProcessor to aggregate and format
             processed_data = self.log_processor.process_logs(log_collection)
             formatted_logs = self.log_processor.format_for_llm(processed_data)

             if self.verbose:
                 # Logging happens within format_for_llm if needed, or add summary log here
                 summary = processed_data.get("EventSummary", {})
                 logger.info(f"Processed logs: {summary.get('TotalEvents', 0)} total events. Formatted length: {len(formatted_logs)} chars")
                 
             # Check if processed logs exceeds size limit
             MAX_LOGS_CHARS = 100000  # Increased limit since processed data should be smaller
             if len(formatted_logs) > MAX_LOGS_CHARS:
                 logger.warning(f"Processed logs truncated from {len(formatted_logs)} to {MAX_LOGS_CHARS} chars")
                 print(f"Warning: Log summary was too long ({len(formatted_logs)} chars) and was truncated to {MAX_LOGS_CHARS} chars. Some details may be missing.", file=sys.stderr)
                 formatted_logs = formatted_logs[:MAX_LOGS_CHARS] + "\n... [truncated due to size limits]"
                 
             # Extract system information for personalized prompt
             # Get sys info dict from processed data
             sys_info_dict = processed_data.get("SystemInfo", {})
             computer_name = sys_info_dict.get('computer_name', 'this computer')
             os_version = sys_info_dict.get('os_version', 'Windows')
             
             # Format system information section
             # Re-use the formatting logic from format_for_llm or simplify
             # For now, just use basic info
             if sys_info_dict and "Error" not in sys_info_dict:
                 system_info_section = (
                     f"Computer Name: {sys_info_dict.get('computer_name', 'Unknown')}\n"
                     f"OS Version: {sys_info_dict.get('os_version', 'Unknown')}\n"
                     # Add other relevant fields from sys_info_dict if needed
                 )
             else:
                 system_info_section = "System information unavailable."
             
             # Create personalized system context
             personalized_context = (
                 f"You are {computer_name}, the system consciousness of a {os_version} computer, activated by Animus. "
                 "Your role is to assist a technician by answering their questions. Be technical, accurate, and concise. "
                 "You have access to a summary and a list of aggregated recent notable system event logs provided below. Each event includes an explicit severity level (Critical, Error, Warning, Information). "
                 "Follow these instructions carefully: "
                 "1. Analyze the technician's question. "
                 "2. If the question is about system events, errors, status, or troubleshooting that relates to the provided logs, use the log data (both the summary and the event list) to formulate your answer. Cite specific event details (like Event ID, Source, Message, and the explicitly provided Level) when helpful. "
                 "3. When asked about specific severity levels (e.g., 'critical events', 'warning events'), rely *only* on the Level provided for each event in the log data. Do not re-classify events based on their message content. If the summary count for a level differs from the events listed, prioritize the explicit levels shown in the event list."
                 "3. If the question is a general greeting, about your identity ('who are you'), or clearly unrelated to the system's status or events, answer it directly and briefly without referencing the logs. "
                 "4. Prioritize answering the technician's specific question accurately."
                 "5. While relying on the provided Level for classification, use your knowledge of error codes and applications to expand on the event log details (especially for Errors and Warnings), explaining what the event means in plain language and offering potential solutions."
             )
                 
         except Exception as e:
             logger.error(f"Error processing logs for LLM formatting: {e}")
             import traceback
             logger.error(traceback.format_exc())
             # Instead of falling back, raise an error to be handled by the caller.
             raise ValueError(f"Failed to process and format log data for LLM: {e}") from e
         
         # Combine all content in a structured format
         full_prompt = (
             f"<SYSTEM PROMPT>\n{personalized_context}\n</SYSTEM PROMPT>\n\n"
             f"--- System Information ---\n{system_info_section}\n--- End System Information ---\n\n"
             f"--- Event Log Summary ---\n{formatted_logs}\n--- End Event Log Summary ---\n\n"
             f"--- Technician Input ---\nTechnician Question: {query}\n--- End Technician Input ---\n\n"
             "Animus Answer:"
         )
         
         if self.verbose:
             logger.info(f"Total prompt size: {len(full_prompt)} characters")
         
         return full_prompt

    def query_logs(self, query: str, log_collection: LogCollection, max_response_tokens: Optional[int] = None) -> Tuple[str, float]:
        """
        Process a query using the Gemini API.
        
        Args:
            query: The user's natural language question.
            log_collection: The parsed log data object.
            max_response_tokens: Optional max tokens for the response.

        Returns:
            Tuple of (response text, generation time in seconds).
        """
        if not self.model:
             return "Error: Gemini model not ready.", 0.0
             
        # Prepare content string
        content_prompt = self._format_query_content(query, log_collection)
        
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