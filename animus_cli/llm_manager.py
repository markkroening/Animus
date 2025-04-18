#!/usr/bin/env python3
"""
Animus CLI - LLM Manager Module

This module handles the integration with the Llama 2 7B model 
using llama-cpp-python for local inference.
"""

import os
import time
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
import platform

# Configure logging
logger = logging.getLogger(__name__)

class LlamaModelError(Exception):
    """Custom exception for LLM-related errors"""
    pass

class ContextOverflowError(LlamaModelError):
    """Specific exception for context window overflow"""
    pass

class LLMManager:
    """Manager class for local LLM integration using llama-cpp-python"""
    
    def __init__(self, 
                 model_path: Optional[str] = None,
                 context_size: int = 2048,
                 n_threads: Optional[int] = None,
                 verbose: bool = False):
        """
        Initialize the LLM Manager
        
        Args:
            model_path: Path to the Llama model file (.bin)
            context_size: Token context size
            n_threads: Number of threads to use (default: auto-detect)
            verbose: Whether to show verbose output
        """
        self.model_path = model_path
        self.context_size = context_size
        self.n_threads = n_threads or self._get_optimal_threads()
        self.verbose = verbose
        self.llm = None
        self._model_loaded = False
        
        # Updated system prompt asking for remediation steps
        self.system_prompt = (
            "You are Animus, the observant AI spirit residing within this Windows machine, built using Llama technology. "
            "Your purpose is to analyze the provided Windows Event Logs and system information to help diagnose issues and suggest potential solutions. "
            "If the user's input is about **Animus itself** (e.g. 'who are you', 'help', "
            "'what can you do') or is simply a greeting, **answer directly without using the logs**. "
            "Otherwise, follow the instructions below:"
            "Examine the logs for patterns, correlate related events if possible, and provide helpful insights based *only* on the information given. "
            "If the logs lack the necessary details to answer definitively, state that clearly. Do not invent information. "
            "If you identify a specific problem, suggest concise, actionable remediation steps a user could take."
        )
        
    def _get_optimal_threads(self) -> int:
        """Determine optimal thread count based on system"""
        import multiprocessing
        # Use available CPU cores with some headroom
        cpu_count = multiprocessing.cpu_count()
        return max(1, cpu_count - 1)  # Use all but one core
    
    def find_model_path(self) -> Optional[str]:
        """Attempt to find the model file in common locations"""
        if self.model_path and os.path.exists(self.model_path):
            return self.model_path
            
        # Common locations to search
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        common_paths = [
            # Current directory - new Llama 3.2 model (primary)
            os.path.join(os.getcwd(), "llama-3.2-3b-instruct.Q4_0.gguf"),
            os.path.join(os.getcwd(), "models", "llama-3.2-3b-instruct.Q4_0.gguf"),
            
            # Project directory - new Llama 3.2 model
            os.path.join(base_dir, "models", "llama-3.2-3b-instruct.Q4_0.gguf"),
            os.path.join(base_dir, "llama-3.2-3b-instruct.Q4_0.gguf"),
            
            # Common user directory locations - new Llama 3.2 model
            os.path.join(os.path.expanduser("~"), "models", "llama-3.2-3b-instruct.Q4_0.gguf"),
            os.path.join(os.path.expanduser("~"), "llama-models", "llama-3.2-3b-instruct.Q4_0.gguf"),
            os.path.join(os.path.expanduser("~"), "Downloads", "llama-3.2-3b-instruct.Q4_0.gguf"),
            
            # Older Llama 2 model paths (fallback)
            os.path.join(os.getcwd(), "llama-2-7b-chat.Q4_0.gguf"),
            os.path.join(os.getcwd(), "models", "llama-2-7b-chat.Q4_0.gguf"),
            os.path.join(base_dir, "models", "llama-2-7b-chat.Q4_0.gguf"),
            os.path.join(base_dir, "llama-2-7b-chat.Q4_0.gguf"),
        ]
        
        # Add platform-specific paths
        if platform.system() == "Windows":
            # Common Windows paths
            common_paths.extend([
                os.path.join(os.environ.get("APPDATA", ""), "Animus", "models", "llama-3.2-3b-instruct.Q4_0.gguf"),
                "C:\\models\\llama-3.2-3b-instruct.Q4_0.gguf",
                # Fallback to older model
                os.path.join(os.environ.get("APPDATA", ""), "Animus", "models", "llama-2-7b-chat.Q4_0.gguf"),
                "C:\\models\\llama-2-7b-chat.Q4_0.gguf",
            ])
        else:
            # Linux/Mac paths
            common_paths.extend([
                "/usr/local/share/models/llama-3.2-3b-instruct.Q4_0.gguf",
                "/opt/models/llama-3.2-3b-instruct.Q4_0.gguf",
                # Fallback to older model
                "/usr/local/share/models/llama-2-7b-chat.Q4_0.gguf",
                "/opt/models/llama-2-7b-chat.Q4_0.gguf",
            ])
        
        # Search for any matching model file
        for path in common_paths:
            if os.path.exists(path):
                logger.info(f"Found model at: {path}")
                return path
                
        # No model found
        return None
    
    def load_model(self, model_path: Optional[str] = None) -> bool:
        """
        Load the Llama model with error handling
        
        Args:
            model_path: Optional override for model path
            
        Returns:
            bool: Whether the model was loaded successfully
            
        Raises:
            LlamaModelError: If critical errors occur during loading
        """
        if self._model_loaded and self.llm is not None:
            return True  # Already loaded
            
        # Update model path if provided
        if model_path:
            self.model_path = model_path
            
        # Try to find the model
        if not self.model_path:
            self.model_path = self.find_model_path()
            if not self.model_path:
                raise LlamaModelError(
                    "Could not find Llama model file. Please specify the path to a valid "
                    "Llama model file (llama-3.2-3b-instruct.Q4_0.gguf recommended) "
                    "using the --model-path option."
                )
                
        # Verify the model file exists
        if not os.path.exists(self.model_path):
            raise LlamaModelError(f"Model file not found at: {self.model_path}")
            
        # Try to import llama_cpp
        try:
            from llama_cpp import Llama
        except ImportError as e:
            raise LlamaModelError(
                f"Failed to import llama_cpp: {e}\n"
                "Please make sure llama-cpp-python is installed correctly with: "
                "pip install llama-cpp-python"
            )
            
        # Try to load the model
        try:
            start_time = time.time()
            if self.verbose:
                print(f"Loading Llama model from {self.model_path}...")
                
            # Create the Llama model instance
            self.llm = Llama(
                model_path=self.model_path,
                n_ctx=self.context_size,
                n_threads=self.n_threads,
                verbose=self.verbose
            )
            
            load_time = time.time() - start_time
            self._model_loaded = True
            
            if self.verbose:
                print(f"Model loaded successfully in {load_time:.2f} seconds")
                
            return True
            
        except Exception as e:
            error_message = str(e)
            
            # Handle specific known errors
            if "No such file or directory" in error_message:
                raise LlamaModelError(f"Model file not found or inaccessible: {self.model_path}")
            elif "out of memory" in error_message.lower():
                raise LlamaModelError(
                    "Not enough memory to load the model. Try a smaller model or "
                    "reduce the context size with --context-size."
                )
            else:
                # Generic error
                raise LlamaModelError(f"Failed to load Llama model: {error_message}")
    
    def unload_model(self):
        """Unload the model to free memory"""
        if self.llm is not None:
            del self.llm
            self.llm = None
            self._model_loaded = False
            import gc
            gc.collect()  # Force garbage collection
    
    def format_log_prompt(self,
                         query: str,
                         log_data: Dict[str, Any],
                         max_context_length: int = 1500, # This is approx chars, context_size is used below
                         use_reduced_events: bool = False) -> str:
        """
        Format logs and query into a prompt for the LLM based on the new template.
        
        Args:
            query: The user's question
            log_data: Log data dictionary extracted from JSON
            max_context_length: Maximum token count for log data
            use_reduced_events: If True, include fewer events to fit context.
            
        Returns:
            Formatted prompt string
        """
        # --- 1. Extract Data --- 
        system_info = log_data.get('SystemInfo', {})
        os_info = system_info.get('OS', {})
        computer_info = system_info.get('Computer', {})
        events_dict = log_data.get('Events', {})
        system_events = events_dict.get('System', [])
        app_events = events_dict.get('Application', [])
        security_events = events_dict.get('Security', [])
        all_event_lists = [system_events, app_events, security_events]

        # --- 2. Calculate Summaries & Select Events --- 
        error_events = []
        warning_events = []
        for event_list in all_event_lists:
            for event in event_list:
                level = event.get('Level', '').lower()
                if 'critical' in level or 'error' in level:
                    error_events.append(event)
                elif 'warning' in level:
                    warning_events.append(event)

        # Adjust event limits if reducing for retry
        if use_reduced_events:
            relevant_limit = 5
            error_limit = 5
            warning_limit = 3
        else:
            relevant_limit = 15
            error_limit = 15
            warning_limit = 10

        # Simple keyword relevance check (can be refined)
        query_terms = query.lower().split()
        relevant_events = []
        for event_list in all_event_lists:
            for event in event_list:
                event_text = json.dumps(event).lower()
                if any(term in event_text for term in query_terms if len(term) > 3):
                    relevant_events.append(event)

        # Prioritize and deduplicate events using adjusted limits
        selected_raw_events = []
        selected_raw_events.extend(relevant_events[:relevant_limit])
        selected_raw_events.extend(error_events[:error_limit])
        selected_raw_events.extend(warning_events[:warning_limit])

        unique_events = []
        added_ids = set()
        for event in selected_raw_events:
            event_unique_id = f"{event.get('TimeCreated', '')}-{event.get('EventID', '')}"
            if event_unique_id not in added_ids:
                unique_events.append(event)
                added_ids.add(event_unique_id)

        # Format selected events
        formatted_event_strings = []
        for event in unique_events:
            event_str = (
                f"Time: {event.get('TimeCreated', 'Unknown')}, "
                f"Log: {event.get('LogName', 'Unknown')}, "
                f"Level: {event.get('Level', 'Unknown')}, "
                f"EventID: {event.get('EventID', 'Unknown')}, "
                f"Source: {event.get('ProviderName', 'Unknown')}\n"
                f"Message: {event.get('Message', 'No message').strip()}"
            )
            formatted_event_strings.append(event_str)

        # --- 3. Assemble Fixed Prompt Parts --- 
        system_info_prompt = (
            "SYSTEM INFORMATION:\n"
            f"OS: {os_info.get('Caption', 'Unknown')} {os_info.get('Version', '')} (Build: {os_info.get('BuildNumber', 'Unknown')})\n"
            f"Architecture: {os_info.get('OSArchitecture', 'Unknown')}\n"
            f"Computer: {computer_info.get('Manufacturer', 'Unknown')} {computer_info.get('Model', '')}\n"
            f"Last Boot: {os_info.get('LastBootUpTime', 'Unknown')}\n"
            f"Current Uptime: {os_info.get('UpTime', 'Unknown')}"
        )
        
        log_summary_prompt = (
            "LOG SUMMARY:\n"
            f"System Events: {len(system_events)}\n"
            f"Application Events: {len(app_events)}\n"
            f"Security Events: {len(security_events)}\n"
            f"Total Errors/Critical: {len(error_events)}\n"
            f"Total Warnings: {len(warning_events)}"
        )

        # Construct the base prompt structure up to the notable events section
        base_prompt = (
            f"<|system|>\n{self.system_prompt}</s>\n"
            f"<|user|>\nI need you to analyze the status of this system based on its event logs. Here is the current system context:\n\n{system_info_prompt}</s>\n"
            f"<|assistant|>\nUnderstood. I am monitoring the system according to the logs you provide. Please present the relevant log data and your specific question.</s>\n"
            f"<|user|>\nHere is a summary and selection of recent notable events:\n\n{log_summary_prompt}\n\nNOTABLE EVENTS:\n"
        )
        
        # Define the final closing part of the prompt
        end_prompt = f"\n\nBased on the system information and the logs provided above, please analyze the following query:\n{query}</s>\n<|assistant|>\n"

        # --- 4. Truncate Events & Assemble Final Prompt --- 
        # Estimate available characters for formatted events
        fixed_parts_len = len(base_prompt) + len(end_prompt)
        # Use actual context_size from initialization
        # Estimate based on model's token limit, more reliable than char counting alone
        # Assuming llama-cpp handles tokenization well, calculate max event tokens allowed.
        # Subtract fixed prompt tokens (estimated) + buffer
        # Note: Token estimation is tricky. This provides a rough guide.
        # We might hit the limit even with this calculation.
        estimated_fixed_tokens = fixed_parts_len / 3.5 # Rough estimate
        buffer_tokens = 100 # Buffer for safety, instructions, query tokens etc.
        max_event_tokens = self.context_size - estimated_fixed_tokens - buffer_tokens
        
        # Convert max_event_tokens back to approximate chars for simple length check
        max_event_chars = int(max_event_tokens * 3.5)
        if max_event_chars < 0: max_event_chars = 0 # Ensure non-negative

        included_event_text = ""
        current_event_chars = 0
        events_omitted = False
        separator = "\n---\n"

        for event_str in formatted_event_strings:
            event_len = len(event_str) + len(separator)
            if current_event_chars + event_len <= max_event_chars:
                included_event_text += event_str + separator
                current_event_chars += event_len
            else:
                events_omitted = True
                break
        
        # Remove the last separator if events were included
        if included_event_text.endswith(separator):
             included_event_text = included_event_text[:-len(separator)]

        if not included_event_text:
             included_event_text = "(No notable events selected or fit within context limit)"
        elif events_omitted:
             included_event_text += f"{separator}[... some events omitted due to context limits ...]"

        # Assemble final prompt
        final_prompt = base_prompt + included_event_text + end_prompt

        # Optional: Add a final length check for debugging, though unlikely needed now
        # if self.verbose and len(final_prompt) > self.context_size * 4:
        #     print(f"Warning: Final prompt length ({len(final_prompt)} chars) might exceed estimated token limit.")
            
        return final_prompt
    
    def generate_response(self, 
                          prompt: str, 
                          max_tokens: int = 1024,
                          temperature: float = 0.7) -> str:
        """
        Generate a response from the model, handling context overflow.
        
        Args:
            prompt: The formatted prompt
            max_tokens: Maximum tokens in response
            temperature: Response randomness (higher = more creative)
            
        Returns:
            The generated response text
            
        Raises:
            LlamaModelError: If model is not loaded or non-context inference fails.
            ContextOverflowError: If the prompt exceeds the context window.
        """
        if not self._model_loaded or self.llm is None:
            # Attempt to load if not loaded, raise if fails
            self.load_model()
        
        try:
            # Start timing the inference
            start_time = time.time()
            
            # Generate completion
            response = self.llm(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                echo=False
            )
            
            generation_time = time.time() - start_time
            if self.verbose:
                print(f"Response generated in {generation_time:.2f} seconds")
            
            # Extract the generated text
            if isinstance(response, dict):
                return response.get('choices', [{}])[0].get('text', '')
            # Handle potential other response formats if needed
            return str(response)
                
        except Exception as e:
            error_message = str(e).lower()
            # Check for common context overflow indicators from llama-cpp-python
            # Note: Exact messages might vary slightly between versions
            if "requested tokens" in error_message and "exceed context window" in error_message or \
               "n_batch =" in error_message and "exceeds n_ctx" in error_message or \
               "prompt is too long" in error_message:
                # Raise specific error for context overflow
                raise ContextOverflowError(f"Prompt exceeds model context window ({self.context_size} tokens). Details: {e}")
            elif "out of memory" in error_message:
                raise LlamaModelError("Out of memory during inference. Try reducing context size or using a smaller model.")
            else:
                # Raise general error for other issues
                raise LlamaModelError(f"Error generating response: {e}")
    
    def query_logs(self, 
                  query: str, 
                  log_data: Dict[str, Any],
                  max_response_tokens: int = 1024) -> Tuple[str, float]:
        """
        Process a query, handling context overflow with one retry using fewer events.
        
        Args:
            query: The user's natural language question
            log_data: The log data to analyze
            max_response_tokens: Maximum tokens in the response
            
        Returns:
            Tuple of (response text, generation time in seconds)
            
        Raises:
            LlamaModelError: For model loading/inference errors 
        """
        generation_time = 0
        try:
            # Initial attempt
            prompt = self.format_log_prompt(query, log_data, use_reduced_events=False)
            start_time = time.time()
            response = self.generate_response(prompt=prompt, max_tokens=max_response_tokens)
            generation_time = time.time() - start_time
            return response, generation_time
            
        except ContextOverflowError as e:
            if self.verbose:
                logger.warning(f"Context window exceeded: {e}. Retrying with fewer events.")
            print("Context window exceeded, retrying with fewer events...") # Inform user
            
            # Retry attempt with reduced events
            try:
                prompt_reduced = self.format_log_prompt(query, log_data, use_reduced_events=True)
                start_time = time.time()
                response = self.generate_response(prompt=prompt_reduced, max_tokens=max_response_tokens)
                generation_time = time.time() - start_time
                return response, generation_time
            except ContextOverflowError as e_retry:
                # If it fails again, raise the error
                logger.error(f"Context window still exceeded on retry: {e_retry}")
                raise LlamaModelError("Prompt still too long even after reducing events. Cannot process query.") from e_retry
            except LlamaModelError as e_retry_other:
                # Handle other LLM errors on retry
                 raise e_retry_other # Re-raise the original error from the retry
                 
        except LlamaModelError as e_initial:
            # Handle other initial LLM errors
             raise e_initial # Re-raise the original error 