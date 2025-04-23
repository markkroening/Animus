#!/usr/bin/env python3
# Animus CLI - Main Entry Point
# This script serves as the main command-line interface for the Animus local log analysis tool

import os
import sys
import json
import argparse
import subprocess
import shlex
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import re
from colorama import Fore, Style, init
from tabulate import tabulate

# Platform-specific imports
import platform
import threading # Added for animation
IS_WINDOWS = platform.system() == "Windows"

# Determine if running as a bundled executable (PyInstaller)
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # Running in a bundle
    IS_BUNDLED = True
    # Base path is the directory containing the executable
    APP_BASE_DIR = os.path.dirname(sys.executable)
    # Path to bundled data files (like the PowerShell script)
    BUNDLED_DATA_DIR = sys._MEIPASS
else:
    # Running as a normal script
    IS_BUNDLED = False
    # Base path is the project root (assuming standard structure)
    APP_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    BUNDLED_DATA_DIR = APP_BASE_DIR # Not strictly needed, but avoids errors

# Adjust paths based on execution context
if not IS_BUNDLED:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
    POWERSHELL_DIR = os.path.join(PROJECT_ROOT, "powershell")
    LOG_COLLECTOR_SCRIPT = os.path.join(POWERSHELL_DIR, "collect_logs.ps1")
    DEFAULT_OUTPUT_PATH = os.path.join(os.getcwd(), "logs", "animus_logs.json")
    os.makedirs(os.path.dirname(DEFAULT_OUTPUT_PATH), exist_ok=True)

# Unused! These comments and code are for local Llama model files, not needed for Google Gemini API
# Handle command history support via standard readline
try:
    import readline
    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False
    print("Warning: Command history not available. Install the 'readline' module.")

# Provide dummy readline if not available
if not READLINE_AVAILABLE:
    class DummyReadline:
        def read_history_file(self, *args, **kwargs): pass
        def write_history_file(self, *args, **kwargs): pass
        def set_history_length(self, *args, **kwargs): pass
    sys.modules["readline"] = DummyReadline()

try:
    import colorama
    from colorama import Fore, Style
    colorama.init(autoreset=True)
    COLOR_SUPPORT = True
except ImportError:
    COLOR_SUPPORT = False
    # Define fallback color codes (empty strings)
    class DummyColor:
        def __getattr__(self, name):
            return ""
    Fore = Style = DummyColor()

# CLI constants
ANIMUS_VERSION = "0.1.0"
ANIMUS_BANNER = f"""
{Fore.CYAN}╔═══════════════════════════════════════════════════════════╗
{Fore.CYAN}║ {Fore.YELLOW}  _____          .__                         {Fore.CYAN}        ║
{Fore.CYAN}║ {Fore.YELLOW} /  _  \\   ____  |__|  _____   __ __  ______ {Fore.CYAN}        ║
{Fore.CYAN}║ {Fore.YELLOW}/  /_\\  \\ /    \\ |  | /     \\ |  |  \\/  ___/ {Fore.CYAN}        ║
{Fore.CYAN}║ {Fore.YELLOW}/    |    \\   |  \\|  ||  Y Y  \\|  |  /\\___ \\  {Fore.CYAN}        ║
{Fore.CYAN}║ {Fore.YELLOW}\\____|__  /___|  /|__||__|_|  /|____//____  > {Fore.CYAN}        ║
{Fore.CYAN}║ {Fore.YELLOW}        \\/     \\/          \\/            \\/  {Fore.CYAN}        ║
{Fore.CYAN}╠═══════════════════════════════════════════════════════════╣
{Fore.CYAN}║ {Fore.WHITE}Windows Event Log Analysis CLI {Fore.GREEN}v{ANIMUS_VERSION}                {Fore.CYAN}  ║
{Fore.CYAN}╚═══════════════════════════════════════════════════════════╝{Style.RESET_ALL}
"""

# Define structured data classes for logs
class EventLevel(Enum):
    CRITICAL = "Critical"
    ERROR = "Error"
    WARNING = "Warning"
    INFORMATION = "Information"
    VERBOSE = "Verbose"
    UNKNOWN = "Unknown"
    
    @classmethod
    def from_string(cls, level_str: str) -> 'EventLevel':
        """Convert string level to enum"""
        if not level_str:
            return cls.UNKNOWN
            
        normalized = level_str.lower()
        if "critical" in normalized:
            return cls.CRITICAL
        elif "error" in normalized:
            return cls.ERROR
        elif "warn" in normalized:
            return cls.WARNING
        elif "info" in normalized:
            return cls.INFORMATION
        elif "verbose" in normalized:
            return cls.VERBOSE
        else:
            return cls.UNKNOWN

@dataclass
class EventLogEntry:
    """Structured representation of a Windows Event Log entry"""
    time_created: str
    log_name: str
    level: EventLevel
    event_id: int
    provider_name: str
    message: str
    machine_name: str
    user_id: Optional[str] = None
    task_display_name: Optional[str] = None
    process_id: Optional[int] = None
    thread_id: Optional[int] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventLogEntry':
        """Create an EventLogEntry from a dictionary (JSON)"""
        try:
            # Extract required fields with defaults
            time_created = data.get('TimeCreated', '')
            log_name = data.get('LogName', '')
            level_str = data.get('Level', '')
            event_id = int(data.get('EventID', 0)) 
            provider_name = data.get('ProviderName', '')
            message = data.get('Message', '')
            machine_name = data.get('MachineName', '')
            
            # Optional fields
            user_id = data.get('UserId')
            task_name = data.get('TaskDisplayName')
            
            # Process and thread IDs - only convert if present
            process_id = None
            if 'ProcessId' in data:
                try:
                    process_id = int(data['ProcessId'])
                except (ValueError, TypeError):
                    pass
                    
            thread_id = None
            if 'ThreadId' in data:
                try:
                    thread_id = int(data['ThreadId'])
                except (ValueError, TypeError):
                    pass
            
            return cls(
                time_created=time_created,
                log_name=log_name,
                level=EventLevel.from_string(level_str),
                event_id=event_id,
                provider_name=provider_name,
                message=message,
                machine_name=machine_name,
                user_id=user_id,
                task_display_name=task_name,
                process_id=process_id,
                thread_id=thread_id
            )
        except Exception as e:
            # If conversion fails, create a minimal entry with error info
            return cls(
                time_created='',
                log_name='',
                level=EventLevel.ERROR,
                event_id=0,
                provider_name="Parser",
                message=f"Error parsing event: {e}",
                machine_name="",
            )

@dataclass
class SystemInfo:
    """System information parsed from logs"""
    os_name: str
    os_version: str
    os_build: str
    architecture: str
    install_date: str
    last_boot_time: str
    uptime: str
    
    manufacturer: str
    model: str
    system_type: str
    processors: int
    memory: str
    
    processor_name: str
    cores: int
    logical_processors: int
    clock_speed: str
    
    disks: List[Dict[str, str]]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemInfo':
        """Create SystemInfo from a dictionary (JSON)"""
        try:
            # Extract data from sections
            os_info = data.get('OS', {})
            computer_info = data.get('Computer', {})
            processor_info = data.get('Processor', {})
            disks_info = data.get('Disks', [])
            
            # Safe conversion helpers
            def safe_str(obj, default='Unknown'):
                return str(obj) if obj is not None else default
                
            def safe_int(obj, default=0):
                try:
                    return int(obj) if obj is not None else default
                except (ValueError, TypeError):
                    return default
            
            # Create object with safe type conversions
            return cls(
                # OS info
                os_name=safe_str(os_info.get('Caption', 'Unknown OS')),
                os_version=safe_str(os_info.get('Version')),
                os_build=safe_str(os_info.get('BuildNumber')),
                architecture=safe_str(os_info.get('OSArchitecture')),
                install_date=safe_str(os_info.get('InstallDate')),
                last_boot_time=safe_str(os_info.get('LastBootUpTime')),
                uptime=safe_str(os_info.get('UpTime')),
                
                # Computer info
                manufacturer=safe_str(computer_info.get('Manufacturer')),
                model=safe_str(computer_info.get('Model')),
                system_type=safe_str(computer_info.get('SystemType')),
                processors=safe_int(computer_info.get('NumberOfProcessors')),
                memory=safe_str(computer_info.get('TotalPhysicalMemory')),
                
                # Processor info
                processor_name=safe_str(processor_info.get('Name')),
                cores=safe_int(processor_info.get('NumberOfCores')),
                logical_processors=safe_int(processor_info.get('NumberOfLogicalProcessors')),
                clock_speed=safe_str(processor_info.get('MaxClockSpeedGHz')),
                
                # Disks info
                disks=disks_info if isinstance(disks_info, list) else []
            )
        except Exception:
            # Return a minimal valid object if parsing fails
            return cls(
                os_name="Error parsing system info",
                os_version="Unknown", os_build="Unknown", architecture="Unknown",
                install_date="Unknown", last_boot_time="Unknown", uptime="Unknown",
                manufacturer="Unknown", model="Unknown", system_type="Unknown",
                processors=0, memory="Unknown",
                processor_name="Unknown", cores=0, logical_processors=0, clock_speed="Unknown",
                disks=[]
            )

@dataclass
class LogCollection:
    """Complete log collection with metadata and events"""
    # Collection metadata
    collection_time: str
    time_range: Dict[str, str]
    
    # System information
    system_info: SystemInfo
    
    # Event logs by type
    system_events: List[EventLogEntry]
    application_events: List[EventLogEntry]
    security_events: List[EventLogEntry]
    
    # Cache for event lists
    _all_events: Optional[List[EventLogEntry]] = None
    _error_events: Optional[List[EventLogEntry]] = None
    _warning_events: Optional[List[EventLogEntry]] = None
    
    def __post_init__(self):
        """Initialize calculated fields to None to trigger lazy loading"""
        self._all_events = None 
        self._error_events = None
        self._warning_events = None
    
    # Helper properties with caching
    @property
    def all_events(self) -> List[EventLogEntry]:
        """Get all events combined (cached)"""
        if self._all_events is None:
            self._all_events = self.system_events + self.application_events + self.security_events
        return self._all_events
    
    @property
    def error_events(self) -> List[EventLogEntry]:
        """Get all error and critical events (cached)"""
        if self._error_events is None:
            self._error_events = [e for e in self.all_events 
                    if e.level in (EventLevel.ERROR, EventLevel.CRITICAL)]
        return self._error_events
    
    @property
    def warning_events(self) -> List[EventLogEntry]:
        """Get all warning events (cached)"""
        if self._warning_events is None:
            self._warning_events = [e for e in self.all_events if e.level == EventLevel.WARNING]
        return self._warning_events
    
    @property
    def event_count(self) -> Dict[str, int]:
        """Get counts of events by type"""
        return {
            "system": len(self.system_events),
            "application": len(self.application_events),
            "security": len(self.security_events),
            "total": len(self.all_events),
            "errors": len(self.error_events),
            "warnings": len(self.warning_events)
        }
    
    def events_by_id(self, event_id: int) -> List[EventLogEntry]:
        """Find events by ID"""
        return [e for e in self.all_events if e.event_id == event_id]
    
    def events_by_provider(self, provider: str) -> List[EventLogEntry]:
        """Find events by provider name"""
        provider_lower = provider.lower()
        return [e for e in self.all_events 
                if provider_lower in e.provider_name.lower()]

    def events_by_text(self, text: str) -> List[EventLogEntry]:
        """Find events containing text in message"""
        text_lower = text.lower()
        return [e for e in self.all_events 
                if text_lower in e.message.lower()]
    
    def recent_events(self, count: int = 10) -> List[EventLogEntry]:
        """Get most recent events"""
        return self.all_events[:min(count, len(self.all_events))]
    
    def summarize(self) -> Dict[str, Any]:
        """Generate a summary of the log collection"""
        error_preview = []
        for i, e in enumerate(self.error_events):
            if i >= 5:  # Limit to 5 errors
                break
            message = e.message
            if len(message) > 100:
                message = message[:100] + "..."
            error_preview.append({
                "time": e.time_created,
                "id": e.event_id,
                "source": e.provider_name,
                "message": message
            })
            
        return {
            "collection_time": self.collection_time,
            "time_range": self.time_range,
            "event_counts": self.event_count,
            "system": {
                "os": f"{self.system_info.os_name} ({self.system_info.os_version})",
                "model": f"{self.system_info.manufacturer} {self.system_info.model}",
                "processor": self.system_info.processor_name,
                "memory": self.system_info.memory,
                "uptime": self.system_info.uptime
            },
            "recent_errors": error_preview
        }

class LogParser:
    """Parser for Windows Event Logs JSON"""
    
    @staticmethod
    def parse_json(json_data: Union[str, Dict[str, Any]]) -> Optional[LogCollection]:
        """Parse JSON data into structured log collection"""
        
        # Convert string to dict if needed
        if isinstance(json_data, str):
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError:
                print("Error: Invalid JSON format")
                return None
        else:
            data = json_data
            
        # Basic validation of expected structure
        if not isinstance(data, dict):
            print("Error: Log data is not a dictionary")
            return None
            
        # Extract collection info
        collection_info = data.get('CollectionInfo', {})
        collection_time = collection_info.get('CollectionTime', 'Unknown')
        time_range = collection_info.get('TimeRange', {})
        
        # Parse system info
        system_info_data = data.get('SystemInfo', {})
        system_info = SystemInfo.from_dict(system_info_data)
        
        # Parse events - optimize by avoiding redundant exception handling
        events_data = data.get('Events', {})
        
        # Helper function to process events in bulk
        def process_events(event_list, log_type):
            result = []
            for event_data in event_list:
                try:
                    result.append(EventLogEntry.from_dict(event_data))
                except Exception as e:
                    # Silent exception handling to improve performance
                    pass
            return result
        
        # Process all event types
        system_events = process_events(events_data.get('System', []), 'System')
        application_events = process_events(events_data.get('Application', []), 'Application')
        security_events = process_events(events_data.get('Security', []), 'Security')
        
        # Create and return the complete collection
        return LogCollection(
            collection_time=collection_time,
            time_range=time_range,
            system_info=system_info,
            system_events=system_events,
            application_events=application_events,
            security_events=security_events
        )
    
    @staticmethod
    def parse_file(file_path: str) -> Optional[LogCollection]:
        """Parse logs from a JSON file"""
        try:
            # Try direct loading with utf-8 - most common case first
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return LogParser.parse_json(json.load(f))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # If failed, try with utf-8-sig for BOM handling
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    return LogParser.parse_json(json.load(f))
        except FileNotFoundError:
            print(f"Error: File not found: {file_path}")
            return None
        except Exception as e:
            print(f"Error parsing log file: {e}")
            return None

# Import LLM Manager
from .llm_manager import LLMManager, GeminiAPIError
from .log_processor import process_log_file

class AnimusCLI:
    """Main CLI application class for Animus"""
    
    def __init__(self, auto_collect=True, auto_collect_age_hours=24, force_collect=False,
                 qa_mode=False, verbose=False, output_path=None, model_name='gemini-1.5-flash-latest'):
        """
        Initialize the Animus CLI
        
        Args:
            auto_collect: Whether to automatically collect logs if needed
            auto_collect_age_hours: Max age of logs before auto-collection
            force_collect: Whether to force log collection
            qa_mode: Whether to start in QA mode immediately
            verbose: Whether to show verbose output
            output_path: Path to the output JSON file
            model_name: Name of the Gemini model to use
        """
        self.auto_collect = auto_collect
        self.auto_collect_age_hours = auto_collect_age_hours
        self.force_collect = force_collect
        self.qa_mode = qa_mode
        self.verbose = verbose
        self.model_name = model_name

        # Determine output path
        self.output_path = output_path or DEFAULT_OUTPUT_PATH
        self.print_status(f"Using log file: {self.output_path}", "info")
        if self.qa_mode:
             self.print_status(f"Using model: {self.model_name}", "info")

        self.log_collection: Optional[LogCollection] = None
        self.last_query_time = 0
        self.history_file = os.path.join(APP_BASE_DIR, ".animus_history") # History file relative to app base
        self.llm = None # Initialize LLM instance placeholder
        self.stop_animation = threading.Event() # For thinking animation

        self.setup_history()
    
    def setup_history(self):
        """Set up command history for the interactive mode"""
        if not READLINE_AVAILABLE:
            return
        
        # Configure readline to store history via standard module
        try:
            import readline

            readline.read_history_file(self.history_file)
            # Set history file size limit
            readline.set_history_length(1000)
        except Exception as e:
            print(f"Error setting up command history: {e}", file=sys.stderr)
    
    def save_history(self):
        """Save command history on exit"""
        if not READLINE_AVAILABLE:
            return
        
        try:
            import readline

            readline.write_history_file(self.history_file)
        except (IOError, ImportError) as e:
            print(f"Error saving command history: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Unexpected error saving history: {e}", file=sys.stderr)
    
    def print_status(self, message, message_type="info"):
        """Print a formatted status message"""
        prefix_map = {
            "info": f"{Fore.BLUE}[INFO]{Style.RESET_ALL}",
            "success": f"{Fore.GREEN}[SUCCESS]{Style.RESET_ALL}",
            "error": f"{Fore.RED}[ERROR]{Style.RESET_ALL}",
            "warning": f"{Fore.YELLOW}[WARNING]{Style.RESET_ALL}",
            "question": f"{Fore.MAGENTA}[QUESTION]{Style.RESET_ALL}",
        }
        prefix = prefix_map.get(message_type.lower(), prefix_map["info"])
        print(f"{prefix} {message}")
        
    def print_banner(self):
        """Print the Animus CLI banner"""
        print(ANIMUS_BANNER)
        
        # Display model attribution
        print(f"{Fore.MAGENTA}Powered by Google Gemini{Style.RESET_ALL} - AI-powered log analysis")
        
        # Show basic usage instructions
        print(f"\n{Fore.CYAN}Usage:{Style.RESET_ALL}")
        print("- Type your question about the Windows Event Logs")
        print("- Type 'exit' or press Ctrl+C to quit")
        print("- Type 'help' for more information")
        print(f"\n{Fore.YELLOW}Tip:{Style.RESET_ALL} Ask about errors, warnings, or system issues in natural language.")
        print("=" * 60)
        
    def print_help(self):
        """Print available commands and help information"""
        print(f"\n{Fore.CYAN}Available Commands:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}collect{Style.RESET_ALL} [hours] [max_events] [--no-security] [--force]")
        print(f"  Collect Windows Event Logs (default: past 48 hours, 500 events per log)")
        print(f"{Fore.YELLOW}load{Style.RESET_ALL} [filename]")
        print(f"  Load a previously collected log file (default: {os.path.basename(self.output_path)})")
        print(f"{Fore.YELLOW}status{Style.RESET_ALL}")
        print(f"  Show information about currently loaded logs")
        print(f"{Fore.YELLOW}ask{Style.RESET_ALL} <question>")
        print(f"  Ask a single question about the loaded logs")
        print(f"{Fore.YELLOW}qa{Style.RESET_ALL}")
        print(f"  Enter interactive Q&A mode for multiple questions")
        print(f"{Fore.YELLOW}help{Style.RESET_ALL}")
        print(f"  Show this help message")
        print(f"{Fore.YELLOW}exit{Style.RESET_ALL} (or {Fore.YELLOW}quit{Style.RESET_ALL})")
        print(f"  Exit the Animus CLI")
        print(f"\nYou can also enter your question directly at the prompt to ask about the logs.")
        
    def check_log_loaded(self):
        """Check if logs are loaded and load if file exists but not loaded"""
        if self.log_collection:
            return True
            
        if os.path.exists(self.output_path):
            return self.load_logs(self.output_path)
        else:
            self.print_status(
                f"No log file found at {self.output_path}. Please collect logs first with 'collect'.", 
                "error"
            )
            return False
    
    def load_logs(self, filename=None):
        """Load logs from a JSON file"""
        if filename:
            self.output_path = filename
            
        try:
            self.print_status(f"Loading logs from {self.output_path}...")
            
            # First, check if the file is valid JSON
            try:
                # Try with utf-8-sig first to handle BOM
                try:
                    with open(self.output_path, 'r', encoding='utf-8-sig') as f:
                        raw_data = f.read()
                except UnicodeDecodeError:
                    # Fall back to regular utf-8
                    with open(self.output_path, 'r', encoding='utf-8') as f:
                        raw_data = f.read()
                    
                # Check for common encoding issues or malformed JSON
                if not raw_data or len(raw_data.strip()) == 0:
                    self.print_status("Log file exists but is empty", "error")
                    self.log_collection = None
                    return False
                    
                # Try to parse the JSON
                try:
                    self.log_collection = LogParser.parse_file(self.output_path)
                except Exception as e:
                    self.print_status(f"Error parsing log file: {e}", "error")
                    self.log_collection = None
                    return False
            except Exception as e:
                self.print_status(f"Error reading log file: {str(e)}", "error")
                self.log_collection = None
                return False
            
            # Store the parsed data
            self.log_collection = self.log_collection
            
            # Print a summary
            event_counts = self.log_collection.event_count
            self.print_status(
                f"Successfully loaded {event_counts['total']} events "
                f"({event_counts['errors']} errors, {event_counts['warnings']} warnings)",
                "success"
            )
            
            return True
            
        except json.JSONDecodeError as e:
            # This should rarely happen now that we're handling JSON errors above
            self.print_status(f"Invalid JSON format in {self.output_path}: {str(e)}", "error")
        except FileNotFoundError:
            self.print_status(f"Log file not found: {self.output_path}", "error")
        except Exception as e:
            self.print_status(f"Error loading logs: {str(e)}", "error")
            
        self.log_collection = None
        return False

    def should_collect_logs(self):
        """Determine if logs should be automatically collected"""
        # Always collect fresh logs on startup
        self.print_status("Collecting fresh logs...", "info")
        return True
    
    def show_status(self):
        """Show information about the currently loaded logs"""
        if not self.check_log_loaded():
            return
            
        try:
            # Use our structured data to display info
            summary = self.log_collection.summarize()
            
            print(f"\n{Fore.CYAN}Log Information:{Style.RESET_ALL}")
            print(f"Collection Time: {summary['collection_time']}")
            
            # Time range
            time_range = summary['time_range']
            start_time = time_range.get('StartTime', 'Unknown')
            end_time = time_range.get('EndTime', 'Unknown')
            print(f"Time Range: {start_time} to {end_time}")
            
            # Event counts
            counts = summary['event_counts']
            print(f"Event Counts:")
            print(f"  - System: {counts['system']}")
            print(f"  - Application: {counts['application']}")
            print(f"  - Security: {counts['security']}")
            print(f"  - Total: {counts['total']}")
            print(f"  - Errors/Critical: {counts['errors']}")
            print(f"  - Warnings: {counts['warnings']}")
            
            # System Information
            system = summary['system']
            print(f"System Information:")
            print(f"  - OS: {system['os']}")
            print(f"  - Model: {system['model']}")
            print(f"  - Processor: {system['processor']}")
            print(f"  - Memory: {system['memory']}")
            print(f"  - Uptime: {system['uptime']}")
            
            # Recent errors if any
            recent_errors = summary['recent_errors']
            if recent_errors:
                print(f"\n{Fore.RED}Recent Errors:{Style.RESET_ALL}")
                for i, error in enumerate(recent_errors, 1):
                    print(f"  {i}. [{error['time']}] {error['source']} (ID: {error['id']})")
                    print(f"     {error['message']}")
        except Exception as e:
            self.print_status(f"Error reading log information: {e}", "error")
            import traceback
            traceback.print_exc()
    
    def command_loop(self):
        """Main interactive Q&A loop (simplified)"""
        self.running = True
        self.print_banner()

        # Only load logs if we don't already have them loaded
        # We skip collection here since it's already done in analyze_logs
        if not self.log_collection and os.path.exists(self.output_path):
            self.load_logs()

        # Show System Summary and Error counts if logs loaded
        if self.log_collection:
            system = self.log_collection.system_info
            print(f"\n{Fore.CYAN}System Summary:{Style.RESET_ALL}")
            print(f"OS: {system.os_name} {system.os_version}")
            print(f"Model: {system.manufacturer} {system.model}")
            print(f"Uptime: {system.uptime}")

            print() # Add a blank line before the prompt
        else:
            # If logs couldn't be loaded/collected, we can't proceed with Q&A
            self.print_status("Failed to load or collect logs. Cannot start Q&A.", "error")
            self.running = False # Prevent loop from starting

        while self.running:
            try:
                # Always use the Q&A prompt, now changed to Animus>
                user_input = input(f"{Fore.MAGENTA}Animus> {Style.RESET_ALL}").strip()

                # Skip empty input
                if not user_input:
                    continue

                # Treat all input as a query
                self.handle_query(user_input, add_to_context=True)

            except (KeyboardInterrupt, EOFError):
                print() # Add a newline for clean exit
                self.running = False
                break
            except Exception as e:
                self.print_status(f"Error: {e}", "error")
                # Optionally add: self.running = False # to exit on error

        # Save history before exit
        self.save_history()
        self.print_status("Goodbye!", "info")
    
    def handle_collect_command(self, args):
        """Handle the collect command with optional arguments"""
        # Parse collect command arguments
        hours = 48
        max_events = 500
        include_security = True
        force_collect = '--force' in args
        
        try:
            # Simple positional argument parsing
            if len(args) >= 1 and args[0].isdigit():
                hours = int(args[0])
            if len(args) >= 2 and args[1].isdigit():
                max_events = int(args[1])
            if '--no-security' in args:
                include_security = False
                
            # Collect logs
            success = collect_logs(
                self.output_path,
                hours,
                max_events,
                include_security,
                force_collect
            )
            
            # Try to load the logs if collection was successful
            if success:
                self.load_logs()
                
        except Exception as e:
            self.print_status(f"Error during log collection: {e}", "error")
    
    def start_qa_mode(self):
        """Mark the CLI to run in Q&A mode (simplified)"""
        self.qa_mode = True
        # After setting the flag, start the interactive command loop
        self.command_loop()
        return True

    def handle_query(self, query, add_to_context=False):
        """Handle a query about the logs"""
        if not self.check_log_loaded():
            # This check might be redundant now command_loop ensures logs exist
            # but keep it as a safeguard
            return

        # Process the query
        answer = self.process_query(query)

        # Format and display the answer (Removed A: prefix)
        print(f"{Style.RESET_ALL}{answer}\n")
    
    def process_query(self, query):
        """
        Process a natural language query about the logs
        
        Args:
            query: The question to process
            
        Returns:
            The LLM-generated answer or a placeholder if LLM not available
        """
        # --- Animation Function ---
        def thinking_animation(stop_event):
            animation_chars = ['   ', '.  ', '.. ', '...']
            idx = 0
            while not stop_event.is_set():
                print(f"Thinking{animation_chars[idx % len(animation_chars)]}   \r", end='', flush=True)
                idx += 1
                time.sleep(0.3)
            # Clear the animation line when stopped
            print('            \r', end='', flush=True)

        # Check if logs are loaded
        if not self.log_collection:
            self.print_status("No logs loaded. Please load logs first.", "error")
            return "No logs are loaded to analyze. Use 'load' to load logs."

        # Try to initialize LLM if not done yet
        if not self.llm:
            try:
                self.print_status("Initializing LLM for analysis...", "info")
                self.llm = LLMManager(
                    model_name=self.model_name,
                    verbose=self.verbose
                )
                self.print_status("LLM initialized successfully", "success")
            except GeminiAPIError as e:
                self.print_status(f"Failed to initialize LLM: {e}", "error")
                self.print_status("Continuing with basic analysis only.", "warning")
            except Exception as e:
                self.print_status(f"Unexpected error initializing LLM: {e}", "error")

        # If LLM manager was successfully initialized, use it.
        if self.llm:
            stop_event = threading.Event()
            animation_thread = None
            response = "Error: LLM response was not generated." # Default/error response
            generation_time = 0
            llm_success = False

            try:
                # Get the raw log data
                with open(self.output_path, 'r', encoding='utf-8') as f:
                    raw_log_data = json.load(f)

                # Start animation thread
                animation_thread = threading.Thread(target=thinking_animation, args=(stop_event,))
                animation_thread.daemon = True # Allows main thread to exit even if animation hangs
                animation_thread.start()

                # Process with LLM
                response, generation_time = self.llm.query_logs(
                    query=query,
                    log_data=raw_log_data,
                )
                llm_success = True # Mark success if query_logs returns

            except GeminiAPIError as e:
                self.print_status(f"LLM analysis failed: {e}", "error")
                # Keep llm_success as False
            except Exception as e:
                self.print_status(f"Error during analysis: {e}", "error")
                # Keep llm_success as False
            finally:
                # Ensure animation stops
                if animation_thread is not None:
                    stop_event.set()
                    # Don't necessarily need to join if it's a daemon thread,
                    # but joining ensures the line clearing happens.
                    animation_thread.join(timeout=1.0) # Wait briefly for cleanup

            # After try/except/finally, decide what to return
            if llm_success:
                if self.verbose:
                    self.print_status(f"Analysis completed in {generation_time:.2f} seconds", "success")
                return response
            else:
                 # If LLM failed, fall back
                 return self._fallback_analysis(query)

        else:
            # LLM was not available in the first place
            return self._fallback_analysis(query)
            
    def _fallback_analysis(self, query):
        """
        Perform basic non-LLM analysis for fallback
        
        Args:
            query: The user's query
            
        Returns:
            A simple analysis based on basic rules
        """
        # This is a basic fallback when LLM is not available
        if not self.log_collection:
            return "No logs loaded. Please load logs first."
        
        # Very simple keyword matching
        query_lower = query.lower()
        results = []
        
        # Handle basic informational queries
        if any(word in query_lower for word in ["hi", "hello", "hey"]):
            results.append("Hello! I'm Animus, a tool for analyzing Windows event logs. How can I help you today?")
            return "\n".join(results)

        if any(term in query_lower for term in ["what can you do", "help", "capabilities", "commands"]):
            return (
                "I can analyze your Windows event logs and answer questions about them.\n"
                "Try asking questions about system errors, application crashes, unexpected reboots, etc."
            )
        
        # Handle queries about system information
        if any(term in query_lower for term in ["system info", "about this system", "computer info", "specs", "hardware"]):
            sys_info = self.log_collection.system_info
            results.append(f"System Information:")
            results.append(f"- OS: {sys_info.os_name} ({sys_info.os_version})")
            results.append(f"- Manufacturer: {sys_info.manufacturer}")
            results.append(f"- Model: {sys_info.model}")
            results.append(f"- Processor: {sys_info.processor_name}")
            results.append(f"- Memory: {sys_info.memory}")
            results.append(f"- Uptime: {sys_info.uptime}")
            results.append(f"- Installation Date: {sys_info.install_date}")
            return "\n".join(results)
        
        # Handle queries about events
        if any(term in query_lower for term in ["errors", "critical", "warnings"]):
            # Show summary of errors/warnings
            error_count = len(self.log_collection.error_events)
            warning_count = len(self.log_collection.warning_events)
            results.append(f"Found {error_count} errors/critical events and {warning_count} warnings.")
            
            # Show the 5 most recent errors
            if error_count > 0:
                results.append("\nRecent errors/critical events:")
                for i, event in enumerate(self.log_collection.error_events[:5]):
                    results.append(f"{i+1}. [{event.time_created}] {event.provider_name} (ID: {event.event_id}): {event.message[:100]}...")
            
            # Show the 5 most recent warnings if specifically asked about warnings
            if "warning" in query_lower and warning_count > 0:
                results.append("\nRecent warnings:")
                for i, event in enumerate(self.log_collection.warning_events[:5]):
                    results.append(f"{i+1}. [{event.time_created}] {event.provider_name} (ID: {event.event_id}): {event.message[:100]}...")
            
            return "\n".join(results)
        
        # Handle reboot queries
        if any(term in query_lower for term in ["reboot", "restart", "shutdown", "crash"]):
            # Look for common reboot-related events
            power_events = self.log_collection.events_by_provider("Kernel-Power")
            kernel_events = self.log_collection.events_by_provider("Microsoft-Windows-Kernel")
            
            if power_events:
                results.append(f"Found {len(power_events)} power-related events.")
                # Show the 3 most recent power events
                results.append("\nRecent power events:")
                for i, event in enumerate(power_events[:3]):
                    results.append(f"{i+1}. [{event.time_created}] Event ID {event.event_id}: {event.message[:100]}...")
            
            if not results:
                results.append("No specific reboot or power events found in the logs.")
            
            return "\n".join(results)
            
        # Generic fallback for other queries
        if not results:
            results.append("Basic analysis: I don't have enough information to answer that question.")
            results.append("\nTry asking about specific errors, warnings, or reboots.")
            results.append("For more detailed analysis, the Google Gemini API is being used.")
            
        return "\n".join(results)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Animus - Windows Event Log Analysis CLI",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Log collection options
    parser.add_argument("--output", "-o", 
                        help="Path to write/read the log JSON file",
                        default=DEFAULT_OUTPUT_PATH)
    
    parser.add_argument("--hours", "-H", 
                        help="Hours of logs to collect", 
                        type=int, 
                        default=48)
    
    parser.add_argument("--max-events", "-m", 
                        help="Maximum events per log type to collect", 
                        type=int, 
                        default=500)
    
    parser.add_argument("--collect", "-c", 
                        help="Force collection of logs even if recent logs exist", 
                        action="store_true")
    
    parser.add_argument("--no-auto-collect", 
                        help="Disable automatic log collection", 
                        action="store_true")
    
    parser.add_argument("--no-security", 
                        help="Skip collection of security logs", 
                        action="store_true")
    
    # Interaction options
    parser.add_argument("--interactive", "-i", 
                        help="Start in interactive mode", 
                        action="store_true")
    
    parser.add_argument("--qa", "-Q", 
                        help="Start directly in Q&A mode", 
                        action="store_true")
    
    parser.add_argument("--query", "-q", 
                        help="Process a single query and exit",
                        type=str)
    
    # LLM options
    parser.add_argument("--verbose", "-v", 
                        help="Enable verbose output", 
                        action="store_true")
    
    parser.add_argument("--model-name",
                       help="Name of the Gemini model to use (default: gemini-1.5-flash-latest)",
                       type=str,
                       default="gemini-1.5-flash-latest")
    
    # Parse arguments
    return parser.parse_args()

def collect_logs(output_path, hours_back=48, max_events=500, include_security=True, force_collect=False):
    """Call PowerShell script to collect Windows Event Logs"""
    # Prepare PowerShell command with appropriate path handling
    security_param = "false" if not include_security else "true"
    
    # Ensure the script path is properly formatted
    script_path = os.path.normpath(LOG_COLLECTOR_SCRIPT)
    output_file_path = os.path.normpath(output_path)
    
    # For Security logs on Windows, we need to run PowerShell as Administrator
    admin_note = ""
    if include_security and IS_WINDOWS:
        admin_note = "\nNote: For Security logs may need admin privileges."
    
    ps_command = [
        "powershell", 
        "-ExecutionPolicy", "Bypass", 
        "-File", script_path,
        "-OutputFile", output_file_path,
        "-HoursBack", str(hours_back),
        "-MaxEvents", str(max_events),
        "-IncludeSecurity", security_param
    ]
    
    try:
        process = subprocess.run(
            ps_command,
            capture_output=True,
            text=True,
            check=True
        )
        
        if process.returncode != 0:
            print(f"Error running log collector: {process.stderr}", file=sys.stderr)
            return False
            
        # Verify the output file was created
        if not os.path.exists(output_path):
            print(f"Error: Log file was not created at {output_path}", file=sys.stderr)
            return False
        
        # Verify JSON validity
        try:
            with open(output_path, 'r', encoding='utf-8-sig') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            # Try with regular utf-8
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                return False
            
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error executing PowerShell script: {e}", file=sys.stderr)
        if e.stderr:
            print(f"PowerShell Error: {e.stderr}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return False

def check_log_freshness(log_file_path, max_age_hours=24):
    """Check if the log file exists and is fresh enough"""
    if not os.path.exists(log_file_path):
        return False
        
    try:
        # Check file age
        file_stat = os.stat(log_file_path)
        file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
        current_time = datetime.now()
        age_hours = (current_time - file_mtime).total_seconds() / 3600
        
        return age_hours <= max_age_hours
    except Exception:
        # If any error occurs during checking, assume it's not fresh
        return False

def check_powershell_requirements():
    """Check if PowerShell is available with necessary execution policy"""
    try:
        # Check if PowerShell is available
        process = subprocess.run(
            ["powershell", "-Command", "Write-Output $PSVersionTable.PSVersion"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Extract version from output
        for line in process.stdout.split('\n'):
            if "." in line and any(c.isdigit() for c in line):
                version = line.strip()
                print(f"PowerShell version detected: {version}")
                break
        
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: PowerShell is not available or cannot be executed.", file=sys.stderr)
        print("Please ensure PowerShell is installed and accessible in your PATH.", file=sys.stderr)
        return False

def analyze_logs(log_file_path, query=None, auto_collect=True, auto_collect_age=24,
                force_collect=False, qa_mode=False, model_name=None, verbose=False):
    """
    Analyze logs with the Animus CLI

    Args:
        log_file_path: Path to the logs JSON file
        query: Optional single query to process
        auto_collect: Whether to automatically collect logs if needed
        auto_collect_age: Max age of logs before auto-collection
        force_collect: Whether to force log collection
        qa_mode: Whether to start in QA mode
        model_name: Name of the Gemini model to use
        verbose: Whether to show verbose output
    """
    # Check PowerShell requirements early (only if needed)
    if IS_WINDOWS and auto_collect:
        if not check_powershell_requirements():
            print(f"{Fore.RED}PowerShell requirements not met. Log collection might fail.")
            # Decide if we should exit or just warn - for now, warn
            # return 1 # Or sys.exit(1)

    # Check for Gemini API key if in QA mode
    if qa_mode:
        from dotenv import load_dotenv
        load_dotenv()
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            print(f"{Fore.RED}WARNING: GEMINI_API_KEY not found in environment or .env file.")
            print(f"{Fore.YELLOW}Create a .env file with GEMINI_API_KEY=your_api_key to enable AI analysis.")
            print(f"{Fore.YELLOW}You can get a key from https://ai.google.dev/")
            print(f"{Fore.YELLOW}Continuing with basic analysis only.{Style.RESET_ALL}")

    # Instantiate the CLI controller
    # Pass the explicit output path from args if provided
    cli = AnimusCLI(
        auto_collect=auto_collect,
        auto_collect_age_hours=auto_collect_age,
        force_collect=force_collect,
        qa_mode=qa_mode,
        verbose=verbose,
        output_path=log_file_path,
        model_name=model_name or "gemini-1.5-flash-latest"
    )

    # Don't print banner in analyze_logs when in QA mode (to avoid duplication)
    if not qa_mode:
        cli.print_banner()

    try:
        # Load initial logs (or collect if needed)
        if force_collect or not os.path.exists(cli.output_path) or (auto_collect and check_log_freshness(cli.output_path, auto_collect_age) is False):
            cli.print_status("Collecting logs...", "info")
            success = collect_logs(
                output_path=cli.output_path, # Use resolved output path
                hours_back=auto_collect_age,
                force_collect=force_collect
            )
            
            if success:
                cli.load_logs() # Load after successful collection
            else:
                cli.print_status("Log collection failed. Trying to load existing logs...", "warning")
                cli.load_logs() # Attempt to load anyway if collection fails
        else:
            cli.load_logs() # Just load existing logs
        
        # If a specific query is provided, process it and exit
        if query:
            if not cli.check_log_loaded(): return 1 # Ensure logs are loaded
            if not qa_mode:
                 cli.print_status("Query provided but QA mode is not enabled. Use --qa to ask questions.", "warning")
                 return 1 # Exit if not in QA mode but query given
            else:
                 cli.print_status(f"Processing query: {query}")
                 cli.process_query(query) # Process the single query in QA mode
                 return 0 # Exit after single query

        # If QA mode is enabled (and no single query was given), start the interactive loop
        elif qa_mode:
            if not cli.check_log_loaded(): return 1
            cli.start_qa_mode() # Start interactive Q&A
            return 0

        # If not QA mode and no query, maybe just show status?
        else:
            cli.print_status("No query provided and QA mode not enabled. Showing log status.")
            cli.show_status()
            return 0

    except KeyboardInterrupt:
        print("Exiting Animus CLI.")
        return 1
    finally:
        cli.save_history()

def main():
    """CLI Entry Point"""
    if IS_WINDOWS:
        init(autoreset=True) # Initialize colorama on Windows

    args = parse_arguments()

    # Map log collection flags
    auto_collect = not args.no_auto_collect
    auto_collect_age = args.hours
    force_collect = args.collect

    # Set verbosity based on args
    verbose = args.verbose

    # Determine log file path
    log_file_path = args.output if args.output else DEFAULT_OUTPUT_PATH
    # Ensure the directory for the log file exists (skip if no directory in path)
    output_dir = os.path.dirname(log_file_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Call the main analysis function with mapped arguments
    exit_code = analyze_logs(
        log_file_path=log_file_path,
        query=args.query,
        auto_collect=auto_collect,
        auto_collect_age=auto_collect_age,
        force_collect=force_collect,
        qa_mode=args.qa,
        model_name=args.model_name,
        verbose=verbose
    )

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
