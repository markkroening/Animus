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
from typing import Optional, Tuple, Dict, Any
import google.generativeai as genai
from google.genai.types import Tool, GoogleSearch, GenerateContentConfig
import sys

from animus_cli.log_processor import LogProcessor

# Configure logging
logger = logging.getLogger(__name__)

class GeminiAPIError(Exception):
    """Custom exception for Gemini API related errors"""
    pass

class LLMManager:
    """Manager class for Google Gemini API integration"""
    
    def __init__(self,
                 model_name: str = 'gemini-2.5-flash-preview-04-17',
                 verbose: bool = False):
        """
        Initialize the LLM Manager for Gemini.
        
        Args:
            model_name: The Gemini model to use.
            verbose: Whether to show verbose output.
        """
        self.model_name = model_name
        self.verbose = verbose
        self.model = None
        self.log_processor = LogProcessor(verbose=verbose)
        
        # Set log level based on verbose flag
        if verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.CRITICAL)  # Suppress all logging in non-verbose mode
        
        # Get API key from system environment variable
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            error_msg = "GEMINI_API_KEY environment variable is not set. Please set it in your system environment variables."
            logger.error(error_msg)
            raise GeminiAPIError(error_msg)
             
        # Create the client instance
        try:
            # Configure the API
            genai.configure(api_key=self.api_key)
            
            # Create a generative model instance
            self.model = genai.GenerativeModel(
                model_name=self.model_name
            )
            
            if self.verbose:
                 logger.info(f"Using model: {self.model_name}")
        except Exception as e:
            error_msg = f"Failed to create Gemini model: {e}"
            logger.error(error_msg)
            raise GeminiAPIError(error_msg) from e
             
    def _format_query_content(self, query: str, processed_data: Dict[str, Any]) -> str:
         """
         Prepare a string containing processed log data and user query in a structured format
         """
         try:            
             # Validate input data
             if not processed_data:
                 raise ValueError("Processed data is empty")
                 
             if not isinstance(processed_data, dict):
                 raise ValueError(f"Processed data must be a dictionary, got {type(processed_data)}")
                 
             # Format the processed data for LLM consumption
             formatted_logs = self.log_processor.format_for_llm(processed_data)
             
             if not formatted_logs:
                 raise ValueError("Formatted logs are empty")

             if self.verbose:
                 # Logging happens within format_for_llm if needed, or add summary log here
                 summary = processed_data.get("EventSummary", {})
                 logger.info(f"Formatted logs: {summary.get('TotalEvents', 0)} total events. Formatted length: {len(formatted_logs)} chars")
                 
             # Save formatted logs to a file alongside the JSON
             try:
                 # Use default path in logs directory
                 logs_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Animus", "logs")
                 base_path = os.path.join(logs_dir, "animus_logs")
                 formatted_path = base_path.rsplit('.', 1)[0] + '_formatted.txt'
                 with open(formatted_path, 'w', encoding='utf-8') as f:
                     f.write(formatted_logs)
                 if self.verbose:
                     logger.info(f"Saved formatted logs to: {formatted_path}")
             except Exception as e:
                 logger.warning(f"Failed to save formatted logs: {e}")
                 
             # Check if processed logs exceeds size limit
             MAX_LOGS_CHARS = 100000
             if len(formatted_logs) > MAX_LOGS_CHARS:
                 logger.warning(f"Processed logs truncated from {len(formatted_logs)} to {MAX_LOGS_CHARS} chars")
                 print(f"Warning: Log summary was too long ({len(formatted_logs)} chars) and was truncated to {MAX_LOGS_CHARS} chars. Some details may be missing.", file=sys.stderr)
                 formatted_logs = formatted_logs[:MAX_LOGS_CHARS] + "\n... [truncated due to size limits]"
                 
             # Extract system information for personalized prompt
             sys_info_dict = processed_data.get("SystemInfo", {})
             if not sys_info_dict:
                 logger.warning("No system information found in processed data")
                 sys_info_dict = {}
                 
             computer_name = sys_info_dict.get('ComputerName', 'this computer')
             os_version = sys_info_dict.get('OSVersion', 'Windows')
             
             # Format system information section
             if sys_info_dict and "Error" not in sys_info_dict:
                 system_info_section = (
                     f"Computer Name: {sys_info_dict.get('ComputerName', 'Unknown')}\n"
                     f"OS Version: {sys_info_dict.get('OSVersion', 'Unknown')} {sys_info_dict.get('OSDisplayVersion', '')} (Build {sys_info_dict.get('OSBuildNumber', 'N/A')})\n"
                     f"Model: {sys_info_dict.get('CsManufacturer', 'Unknown')} {sys_info_dict.get('CsModel', 'Unknown')}\n"
                     f"Memory: {sys_info_dict.get('TotalPhysicalMemory', 'Unknown')}\n"
                     f"Install Date: {sys_info_dict.get('InstallDate', 'Unknown')}\n"
                     f"Last Boot: {sys_info_dict.get('LastBootTime', 'Unknown')}\n"
                     f"Uptime Hours: {sys_info_dict.get('UptimeHours', 'Unknown')}"
                 )
             else:
                 system_info_section = "System information unavailable."
                 
             # Create personalized system context
             personalized_context = (
                 f"You are {computer_name}, the system consciousness of a {os_version} computer, activated by Animus. "
"Your role is to assist a technician by answering their questions. Be technical, accurate, and concise. "
"You have access to: (1) A summary and list of aggregated recent notable system event logs provided below. Each event includes an explicit Level (Critical, Error, Warning, Information). (2) A Google Search tool for accessing external, up-to-date information. " # Explicitly mention both data sources
"Follow these instructions carefully: "
"1. Analyze the technician's question. "
"2. If the question is about system events, errors, status, or troubleshooting: first consult the provided log data (summary and event list). "
"3. If the log data provides a sufficient answer, formulate your response based on it. Cite specific event details (ID, Source, Message, Level) when helpful. "
"4. If the log data is insufficient OR the question asks for external/recent information (e.g., 'search for...', 'latest solutions for error X', 'details on event ID Y'), use the Google Search tool to find relevant, up-to-date information. " # Combined rule for when to search
"5. When asked about specific severity levels (e.g., 'critical events'), rely *only* on the explicit Level provided in the log data. Do not re-classify based on message content. "
"6. If the question is a general greeting, about your identity ('who are you'), or clearly unrelated to the system's status, events, or technical troubleshooting, answer it directly and briefly without referencing logs or using search. " # Refined non-technical handling
"7. Synthesize information from the logs and/or search results (if used) to provide a comprehensive and accurate answer to the technician's specific question. Use your internal knowledge to explain error codes or suggest general troubleshooting steps, but prioritize information from the logs or recent search results if available and relevant. " # Explain synthesis and priority
"8. When asked about recent or latest events, use the timestamps in the event list. "
"9. Always provide a helpful response, even if it's to state that the information isn't available in the logs or via search, or if more details are needed." # Combined accuracy/always respond
             )
                 
         except Exception as e:
             logger.error(f"Error formatting logs for LLM: {e}")
             import traceback
             logger.error(traceback.format_exc())
             raise ValueError(f"Failed to format log data for LLM: {e}") from e
         
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
             logger.info(f"Prompt structure:\n{full_prompt}")
         
         return full_prompt

    def query_logs(self, query: str, processed_data: Dict[str, Any], max_response_tokens: Optional[int] = None) -> Tuple[str, float]:
        """
        Process a query using the Gemini API.
        
        Args:
            query: The user's natural language question.
            processed_data: The pre-processed log data.
            max_response_tokens: Optional max tokens for the response.

        Returns:
            Tuple of (response text, generation time in seconds).
        """
        if not self.model:
            error_msg = "Error: Gemini model not ready."
            logger.error(error_msg)
            return error_msg, 0.0
             
        # Prepare content string
        try:
            content_prompt = self._format_query_content(query, processed_data)
            if self.verbose:
                logger.info(f"Content prompt length: {len(content_prompt)} characters")
                logger.info(f"First 500 chars of prompt: {content_prompt[:500]}")
        except Exception as e:
            error_msg = f"Error formatting query content: {e}"
            logger.error(error_msg)
            return error_msg, 0.0
        
        if self.verbose:
            print(f"\n--- Sending Prompt to Gemini ({len(content_prompt)} chars) ---")
            print(f"Query: {query}")
            print("-----------------------------------")

        start_time = time.time()
        try:
            # Configure generation parameters with higher token limits
            generation_config = genai.GenerationConfig(
                temperature=0.2,
                top_p=0.8,
                top_k=40,
                max_output_tokens=4096  # Increased from 2048
            )
            
            if self.verbose:
                logger.info(f"Generation config: {generation_config}")
            
            # Generate content using the model instance
            response = self.model.generate_content(
                content_prompt,
                generation_config=generation_config,
                safety_settings=[
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_NONE",
                    },
                ]
            )
            
            generation_time = time.time() - start_time
            
            if self.verbose:
                logger.info(f"Raw response type: {type(response)}")
                logger.info(f"Response attributes: {dir(response)}")
                if hasattr(response, 'prompt_feedback'):
                    logger.info(f"Prompt feedback: {response.prompt_feedback}")
            
            # Access response text safely
            try:
                result_text = response.text
                if not result_text.strip():
                    error_msg = "Error: Received empty response from Gemini"
                    logger.error(error_msg)
                    if self.verbose:
                        logger.error(f"Response object: {response}")
                        logger.error(f"Response attributes: {dir(response)}")
                        logger.error(f"Usage metadata: {getattr(response, 'usage_metadata', 'Not available')}")
                    return error_msg, generation_time
            except ValueError as e:
                block_reason = getattr(response.prompt_feedback, 'block_reason', None)
                block_reason_name = getattr(block_reason, 'name', 'Unknown') if block_reason else 'Unknown'
                error_msg = f"Response blocked by safety filter: {block_reason_name}"
                logger.error(f"{error_msg} - Original error: {e}")
                if self.verbose:
                    logger.error(f"Response object: {response}")
                    logger.error(f"Response attributes: {dir(response)}")
                return error_msg, generation_time
            except AttributeError as e:
                error_msg = "Error: Could not parse response from Gemini"
                logger.error(f"{error_msg} - Original error: {e}")
                if self.verbose:
                    logger.error(f"Response object: {response}")
                    logger.error(f"Response attributes: {dir(response)}")
                return error_msg, generation_time

            if self.verbose:
                logger.info(f"Gemini response received in {generation_time:.2f} seconds")
                logger.info(f"Response length: {len(result_text)} characters")
                logger.info(f"First 500 chars of response: {result_text[:500]}")
                
            return result_text, generation_time

        except Exception as e:
            error_msg = f"Unexpected error during Gemini query: {e}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            return error_msg, 0.0

    def query(self, formatted_text: str, query: str, max_response_tokens: Optional[int] = None) -> str:
        """
        Process a query using the Gemini API with pre-formatted text.
        
        Args:
            formatted_text: Pre-formatted text for the LLM.
            query: The user's natural language question.
            max_response_tokens: Optional max tokens for the response.

        Returns:
            Response text from the LLM.
        """
        if not self.model:
             return "Error: Gemini model not ready."
             
        # Prepare content string
        content_prompt = (
            f"--- Log Data ---\n{formatted_text}\n--- End Log Data ---\n\n"
            f"--- Technician Input ---\nTechnician Question: {query}\n--- End Technician Input ---\n\n"
            "Animus Answer:"
        )
        
        if self.verbose:
             print(f"\n--- Sending Prompt to Gemini ({len(content_prompt)} chars) ---")
             print(f"Query: {query}")
             print("-----------------------------------")

        try:
            # Configure generation parameters with tool usage enabled
            generation_config = GenerateContentConfig(
                temperature=0.2,
                top_p=0.8,
                top_k=40,
                max_output_tokens=max_response_tokens or 2048,
                tools=[Tool(google_search=GoogleSearch())],
                tool_config={
                    "function_calling_config": {
                        "mode": "AUTO"  # Changed from ANY to AUTO for better stability
                    }
                }
            )
            
            # Generate content using the model instance
            response = self.model.generate_content(
                content_prompt,
                config=generation_config,
                safety_settings=[
                    {
                        "category": "HARM_CATEGORY_HARASSMENT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_HATE_SPEECH",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_NONE",
                    },
                    {
                        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                        "threshold": "BLOCK_NONE",
                    },
                ]
            )
            
            # Access response text safely
            try:
                result_text = response.text
                if not result_text.strip():
                    error_msg = "Error: Received empty response from Gemini"
                    logger.error(error_msg)
                    if self.verbose:
                        logger.error(f"Response object: {response}")
                        logger.error(f"Response attributes: {dir(response)}")
                    return error_msg
            except ValueError as e:
                block_reason = getattr(response.prompt_feedback, 'block_reason', None)
                block_reason_name = getattr(block_reason, 'name', 'Unknown') if block_reason else 'Unknown'
                error_msg = f"Response blocked by safety filter: {block_reason_name}"
                logger.error(f"{error_msg} - Original error: {e}")
                if self.verbose:
                    logger.error(f"Response object: {response}")
                    logger.error(f"Response attributes: {dir(response)}")
                return error_msg
            except AttributeError as e:
                error_msg = "Error: Could not parse response from Gemini"
                logger.error(f"{error_msg} - Original error: {e}")
                if self.verbose:
                    logger.error(f"Response object: {response}")
                    logger.error(f"Response attributes: {dir(response)}")
                return error_msg
                
            return result_text

        except Exception as e:
            error_msg = f"Unexpected error during Gemini query: {e}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            return f"Unexpected error: {e}"

# Configure logging if module run directly
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s') 