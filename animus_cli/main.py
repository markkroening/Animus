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

# Handle readline support based on platform
if IS_WINDOWS:
    try:
        # Try to use pyreadline3 on Windows
        import pyreadline3
        READLINE_AVAILABLE = True
    except ImportError:
        READLINE_AVAILABLE = False
        print("Warning: Command history not available. Install pyreadline3 with: pip install pyreadline3")
else:
    try:
        # Use standard readline on Unix/Linux/Mac
        import readline
        READLINE_AVAILABLE = True
    except ImportError:
        READLINE_AVAILABLE = False
        print("Warning: readline module not available. Command history will be disabled.")

# Create dummy readline functions if not available
if not READLINE_AVAILABLE:
    class DummyReadline:
        def read_history_file(self, *args, **kwargs):
            pass
        
        def write_history_file(self, *args, **kwargs):
            pass
            
        def set_history_length(self, *args, **kwargs):
            pass
    
    # Create a readline module with dummy methods
    if "readline" not in sys.modules:
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

# Define paths with platform-appropriate separators
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
POWERSHELL_DIR = os.path.join(PROJECT_ROOT, "powershell")
LOG_COLLECTOR_SCRIPT = os.path.join(POWERSHELL_DIR, "collect_logs.ps1")
DEFAULT_OUTPUT_PATH = os.path.join(PROJECT_ROOT, "animus_logs.json")

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
        normalized = level_str.lower() if level_str else ""
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
        # Extract and convert fields with proper validation
        try:
            return cls(
                time_created=str(data.get('TimeCreated', '')),
                log_name=str(data.get('LogName', '')),
                level=EventLevel.from_string(str(data.get('Level', ''))),
                event_id=int(data.get('EventID', 0)),
                provider_name=str(data.get('ProviderName', '')),
                message=str(data.get('Message', '')),
                machine_name=str(data.get('MachineName', '')),
                user_id=str(data.get('UserId', '')) if data.get('UserId') else None,
                task_display_name=str(data.get('TaskDisplayName', '')) if data.get('TaskDisplayName') else None,
                process_id=int(data.get('ProcessId', 0)) if data.get('ProcessId') else None,
                thread_id=int(data.get('ThreadId', 0)) if data.get('ThreadId') else None
            )
        except (ValueError, TypeError) as e:
            # If conversion fails, create a minimal entry with error info
            return cls(
                time_created=str(data.get('TimeCreated', '')),
                log_name=str(data.get('LogName', '')),
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
            # Extract OS info
            os_info = data.get('OS', {})
            computer_info = data.get('Computer', {})
            processor_info = data.get('Processor', {})
            disks_info = data.get('Disks', [])
            
            return cls(
                # OS info
                os_name=str(os_info.get('Caption', 'Unknown OS')),
                os_version=str(os_info.get('Version', 'Unknown')),
                os_build=str(os_info.get('BuildNumber', 'Unknown')),
                architecture=str(os_info.get('OSArchitecture', 'Unknown')),
                install_date=str(os_info.get('InstallDate', 'Unknown')),
                last_boot_time=str(os_info.get('LastBootUpTime', 'Unknown')),
                uptime=str(os_info.get('UpTime', 'Unknown')),
                
                # Computer info
                manufacturer=str(computer_info.get('Manufacturer', 'Unknown')),
                model=str(computer_info.get('Model', 'Unknown')),
                system_type=str(computer_info.get('SystemType', 'Unknown')),
                processors=int(computer_info.get('NumberOfProcessors', 0)),
                memory=str(computer_info.get('TotalPhysicalMemory', 'Unknown')),
                
                # Processor info
                processor_name=str(processor_info.get('Name', 'Unknown')),
                cores=int(processor_info.get('NumberOfCores', 0)),
                logical_processors=int(processor_info.get('NumberOfLogicalProcessors', 0)),
                clock_speed=str(processor_info.get('MaxClockSpeedGHz', 'Unknown')),
                
                # Disks info
                disks=disks_info if isinstance(disks_info, list) else []
            )
        except (ValueError, TypeError) as e:
            # Return a minimal valid object if parsing fails
            return cls(
                os_name="Error parsing system info",
                os_version="Unknown",
                os_build="Unknown",
                architecture="Unknown",
                install_date="Unknown",
                last_boot_time="Unknown",
                uptime="Unknown",
                manufacturer="Unknown",
                model="Unknown",
                system_type="Unknown",
                processors=0,
                memory="Unknown",
                processor_name="Unknown",
                cores=0,
                logical_processors=0,
                clock_speed="Unknown",
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
    
    # Helper properties
    @property
    def all_events(self) -> List[EventLogEntry]:
        """Get all events combined"""
        return self.system_events + self.application_events + self.security_events
    
    @property
    def error_events(self) -> List[EventLogEntry]:
        """Get all error and critical events"""
        return [e for e in self.all_events 
                if e.level in (EventLevel.ERROR, EventLevel.CRITICAL)]
    
    @property
    def warning_events(self) -> List[EventLogEntry]:
        """Get all warning events"""
        return [e for e in self.all_events if e.level == EventLevel.WARNING]
    
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
        # This is a simple implementation assuming events are already sorted by time
        # We could add explicit sorting by parsed datetime if needed
        return self.all_events[:count]
    
    def summarize(self) -> Dict[str, Any]:
        """Generate a summary of the log collection"""
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
            "recent_errors": [
                {
                    "time": e.time_created,
                    "id": e.event_id,
                    "source": e.provider_name,
                    "message": e.message[:100] + ("..." if len(e.message) > 100 else "")
                }
                for e in self.error_events[:5]  # Show 5 most recent errors
            ]
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
        
        # Parse events
        events_data = data.get('Events', {})
        
        # Parse System events
        system_events = []
        for event_data in events_data.get('System', []):
            try:
                system_events.append(EventLogEntry.from_dict(event_data))
            except Exception as e:
                print(f"Error parsing System event: {e}")
        
        # Parse Application events
        application_events = []
        for event_data in events_data.get('Application', []):
            try:
                application_events.append(EventLogEntry.from_dict(event_data))
            except Exception as e:
                print(f"Error parsing Application event: {e}")
        
        # Parse Security events
        security_events = []
        for event_data in events_data.get('Security', []):
            try:
                security_events.append(EventLogEntry.from_dict(event_data))
            except Exception as e:
                print(f"Error parsing Security event: {e}")
        
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
            # Try with utf-8-sig first to handle BOM
            try:
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    try:
                        json_data = json.load(f)
                        return LogParser.parse_json(json_data)
                    except json.JSONDecodeError:
                        # If this fails, we'll fall back to regular utf-8 below
                        pass
            except Exception:
                # Fall back to regular utf-8
                pass
                
            # Try regular utf-8
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    json_data = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"Error: Invalid JSON format in file: {file_path}. Error: {e}")
                    # Try to diagnose the JSON issue
                    f.seek(0)  # Go back to start of file
                    content = f.read(1000)  # Read first 1000 chars for diagnosis
                    print(f"File starts with: {content[:100]}...")
                    return None
                
            return LogParser.parse_json(json_data)
        except FileNotFoundError:
            print(f"Error: File not found: {file_path}")
            return None
        except Exception as e:
            print(f"Error parsing log file: {e}")
            # Try to print more debugging info
            import traceback
            traceback.print_exc()
            return None

# Import LLM Manager
from .llm_manager import LLMManager, LlamaModelError

class AnimusCLI:
    """Main CLI application class for Animus"""
    
    def __init__(self, auto_collect=True, auto_collect_age_hours=24, force_collect=False, 
                 model_path=None, context_size=2048, qa_mode=False, verbose=False):
        """
        Initialize the Animus CLI
        
        Args:
            auto_collect: Whether to automatically collect logs if needed
            auto_collect_age_hours: Max age of logs before auto-collection
            force_collect: Whether to force log collection
            model_path: Path to Llama model file
            context_size: Token context size for LLM
            qa_mode: Whether to start in QA mode immediately
            verbose: Whether to show verbose output
        """
        self.logs_path = None
        self.log_collection = None
        self.auto_collect = auto_collect
        self.auto_collect_age = auto_collect_age_hours
        self.force_collect = force_collect
        
        # LLM settings
        self.model_path = model_path
        self.context_size = context_size
        self.verbose = verbose
        self.llm_manager = None
        self.llm_available = False  # Will be set to True if model can be loaded
        
        # Interactive mode settings
        self.qa_mode = qa_mode
        self.history_file = os.path.join(os.path.expanduser("~"), ".animus_history")
        self.qa_context = [] # Initialize QA context list
        
        # Initialize colorama
        init(autoreset=True)
        
        # Setup readline for history
        self.setup_history()
    
    def setup_history(self):
        """Set up command history for the interactive mode"""
        if not READLINE_AVAILABLE:
            return
            
        # Configure readline to store history
        try:
            if IS_WINDOWS:
                # Windows uses pyreadline3
                import pyreadline3.readline as readline
            else:
                # Unix systems use standard readline
                import readline
                
            readline.read_history_file(self.history_file)
            # Set history file size limit
            readline.set_history_length(1000)
        except (FileNotFoundError, IOError, ImportError):
            # History file doesn't exist yet or other issue
            pass
        except Exception as e:
            print(f"Error setting up command history: {e}", file=sys.stderr)
    
    def save_history(self):
        """Save command history on exit"""
        if not READLINE_AVAILABLE:
            return
            
        try:
            if IS_WINDOWS:
                import pyreadline3.readline as readline
            else:
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
        """Print the Animus CLI banner with Llama attribution"""
        print(ANIMUS_BANNER)
        
        # Display Llama attribution
        print(f"{Fore.MAGENTA}Built with Llama{Style.RESET_ALL} - AI-powered log analysis")
        
        # If verbose, show additional model info
        if self.verbose and self.model_path:
            model_name = os.path.basename(self.model_path)
            print(f"Using model: {model_name}")
            
        print() # Add a newline for better spacing
        
    def print_help(self):
        """Print available commands and help information"""
        print(f"\n{Fore.CYAN}Available Commands:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}collect{Style.RESET_ALL} [hours] [max_events] [--no-security] [--force]")
        print(f"  Collect Windows Event Logs (default: past 48 hours, 500 events per log)")
        print(f"{Fore.YELLOW}load{Style.RESET_ALL} [filename]")
        print(f"  Load a previously collected log file (default: {os.path.basename(self.logs_path)})")
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
            
        if os.path.exists(self.logs_path):
            return self.load_logs(self.logs_path)
        else:
            self.print_status(
                f"No log file found at {self.logs_path}. Please collect logs first with 'collect'.", 
                "error"
            )
            return False
    
    def load_logs(self, filename=None):
        """Load logs from a JSON file"""
        if filename:
            self.logs_path = filename
            
        try:
            self.print_status(f"Loading logs from {self.logs_path}...")
            
            # First, check if the file is valid JSON
            try:
                # Try with utf-8-sig first to handle BOM
                try:
                    with open(self.logs_path, 'r', encoding='utf-8-sig') as f:
                        raw_data = f.read()
                except UnicodeDecodeError:
                    # Fall back to regular utf-8
                    with open(self.logs_path, 'r', encoding='utf-8') as f:
                        raw_data = f.read()
                    
                # Check for common encoding issues or malformed JSON
                if not raw_data or len(raw_data.strip()) == 0:
                    self.print_status("Log file exists but is empty", "error")
                    self.log_collection = None
                    return False
                    
                # Try to parse the JSON
                try:
                    self.log_collection = LogParser.parse_file(self.logs_path)
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
            self.print_status(f"Invalid JSON format in {self.logs_path}: {str(e)}", "error")
        except FileNotFoundError:
            self.print_status(f"Log file not found: {self.logs_path}", "error")
        except Exception as e:
            self.print_status(f"Error loading logs: {str(e)}", "error")
            
        self.log_collection = None
        return False

    def should_collect_logs(self):
        """Determine if logs should be automatically collected"""
        # Force collection if requested
        if self.force_collect:
            self.print_status("Forced log collection requested. Collecting fresh logs.", "info")
            return True
            
        if not self.auto_collect:
            return False
            
        # Check if log file exists
        if not os.path.exists(self.logs_path):
            self.print_status("No existing log file found. Will collect logs automatically.", "info")
            return True
            
        try:
            # Check file age
            file_stat = os.stat(self.logs_path)
            file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
            current_time = datetime.now()
            age_hours = (current_time - file_mtime).total_seconds() / 3600
            
            if age_hours > self.auto_collect_age:
                self.print_status(
                    f"Log file is {age_hours:.1f} hours old (threshold: {self.auto_collect_age} hours). Collecting fresh logs.", 
                    "info"
                )
                return True
                
            # Try to validate the logs
            try:
                with open(self.logs_path, 'r') as f:
                    log_data = json.load(f)
                    if not isinstance(log_data, dict) or 'Events' not in log_data:
                        self.print_status("Existing log file has invalid format. Will collect fresh logs.", "warning")
                        return True
            except (json.JSONDecodeError, FileNotFoundError):
                self.print_status("Existing log file is corrupt or unreadable. Will collect fresh logs.", "warning")
                return True
                
            return False
            
        except Exception as e:
            self.print_status(f"Error checking log file: {e}. Will collect fresh logs.", "warning")
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

        # Initial log collection/loading
        if self.should_collect_logs():
            self.print_status("Collecting logs...", "info") # Keep brief message
            self.handle_collect_command([])
        elif os.path.exists(self.logs_path) and not self.log_collection:
            self.load_logs()

        # Show System Summary and Error counts if logs loaded
        if self.log_collection:
            system = self.log_collection.system_info
            print(f"\n{Fore.CYAN}System Summary:{Style.RESET_ALL}")
            print(f"OS: {system.os_name} {system.os_version}")
            print(f"Model: {system.manufacturer} {system.model}")
            print(f"Uptime: {system.uptime}")

            error_count = len(self.log_collection.error_events)
            warning_count = len(self.log_collection.warning_events)
            if error_count > 0:
                print(f"\n{Fore.RED}Found {error_count} error/critical events and {warning_count} warnings{Style.RESET_ALL}")
            else:
                print(f"\nNo critical errors found in the logs.")
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
                self.logs_path,
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
        # We don't need to check logs here anymore, command_loop does
        return True # Indicate QA mode was set

    def handle_query(self, query, add_to_context=False):
        """Handle a query about the logs"""
        if not self.check_log_loaded():
            # This check might be redundant now command_loop ensures logs exist
            # but keep it as a safeguard
            return

        # Track the query in context
        if add_to_context:
            self.qa_context.append({"role": "user", "content": query})

        # Process the query
        answer = self.process_query(query)

        # Format and display the answer (Removed A: prefix)
        print(f"{Style.RESET_ALL}{answer}\n")
        # Add the answer to context
        self.qa_context.append({"role": "assistant", "content": answer})
    
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
        if not self.llm_manager:
            try:
                self.print_status("Initializing LLM for analysis...", "info")
                self.llm_manager = LLMManager(
                    model_path=self.model_path,
                    context_size=self.context_size,
                    verbose=self.verbose
                )
                self.llm_manager.load_model()
                self.llm_available = True
                self.print_status("LLM initialized successfully", "success")
            except LlamaModelError as e:
                self.print_status(f"Failed to initialize LLM: {e}", "error")
                self.print_status("Continuing with basic analysis only.", "warning")
                self.llm_available = False
            except Exception as e:
                self.print_status(f"Unexpected error initializing LLM: {e}", "error")
                self.llm_available = False

        # If LLM is available, use it to process the query
        if self.llm_available and self.llm_manager:
            stop_event = threading.Event()
            animation_thread = None
            response = "Error: LLM response was not generated." # Default/error response
            generation_time = 0
            llm_success = False

            try:
                # Get the raw log data
                with open(self.logs_path, 'r', encoding='utf-8') as f:
                    raw_log_data = json.load(f)

                # Start animation thread
                animation_thread = threading.Thread(target=thinking_animation, args=(stop_event,))
                animation_thread.daemon = True # Allows main thread to exit even if animation hangs
                animation_thread.start()

                # Process with LLM
                response, generation_time = self.llm_manager.query_logs(
                    query=query,
                    log_data=raw_log_data,
                    max_response_tokens=1024
                )
                llm_success = True # Mark success if query_logs returns

            except LlamaModelError as e:
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
        """Provide a basic analysis without LLM"""
        # Basic keyword matching
        query_lower = query.lower()
        
        results = []
        
        # Check for common query patterns
        if "error" in query_lower or "critical" in query_lower:
            errors = self.log_collection.error_events[:5]  # Show top 5 errors
            if errors:
                results.append("Found recent errors/critical events:")
                for e in errors:
                    results.append(f"- {e.time_created}: {e.provider_name} (EventID: {e.event_id})")
                    results.append(f"  {e.message[:150]}..." if len(e.message) > 150 else f"  {e.message}")
            else:
                results.append("No error or critical events found in the logs.")
                
        elif "warning" in query_lower:
            warnings = self.log_collection.warning_events[:5]
            if warnings:
                results.append("Found recent warnings:")
                for w in warnings:
                    results.append(f"- {w.time_created}: {w.provider_name} (EventID: {w.event_id})")
                    results.append(f"  {w.message[:150]}..." if len(w.message) > 150 else f"  {w.message}")
            else:
                results.append("No warning events found in the logs.")
                
        elif "reboot" in query_lower or "restart" in query_lower or "shutdown" in query_lower:
            # Look for common reboot/shutdown event IDs
            reboot_events = []
            for e in self.log_collection.all_events:
                # Common Windows reboot/shutdown related events
                if (e.provider_name.lower() == "user32" and e.event_id == 1074) or \
                   (e.provider_name.lower() == "kernel-power" and e.event_id == 41) or \
                   "restart" in e.message.lower() or "shutdown" in e.message.lower() or \
                   "power off" in e.message.lower():
                    reboot_events.append(e)
                    
            if reboot_events:
                results.append("Found events related to system restart/shutdown:")
                for e in reboot_events[:5]:
                    results.append(f"- {e.time_created}: {e.provider_name} (EventID: {e.event_id})")
                    results.append(f"  {e.message[:150]}..." if len(e.message) > 150 else f"  {e.message}")
            else:
                results.append("No clear shutdown/restart events found in the logs.")
                
        else:
            # Generic case - just show system summary and recent events
            results.append("Without LLM capabilities, only basic analysis is available.")
            results.append("Here's a summary of the logs:")
            results.append(f"- System: {self.log_collection.system_info.os_name} ({self.log_collection.system_info.os_version})")
            results.append(f"- Last Boot: {self.log_collection.system_info.last_boot_time}")
            results.append(f"- Total Events: {self.log_collection.event_count['total']}")
            results.append(f"- Errors: {self.log_collection.event_count['errors']}")
            results.append(f"- Warnings: {self.log_collection.event_count['warnings']}")
            
            # Show some recent events
            results.append("\nRecent events:")
            for e in self.log_collection.all_events[:5]:
                results.append(f"- {e.time_created}: {e.level.name} from {e.provider_name} (ID: {e.event_id})")
                
            results.append("\nTry asking about specific errors, warnings, or reboots.")
            results.append("To use AI-powered analysis, please install the Llama model.")
            
        return "\n".join(results)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Animus - Windows Event Log Analysis CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
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
    parser.add_argument("--model-path", 
                        help="Path to Llama model file (llama-2-7b-chat.Q4_0.gguf)",
                        type=str)
    
    parser.add_argument("--context-size", 
                        help="Token context size for the LLM",
                        type=int,
                        default=4096)
    
    parser.add_argument("--verbose", "-v", 
                        help="Enable verbose output", 
                        action="store_true")
    
    return parser.parse_args()

def collect_logs(output_path, hours_back=48, max_events=500, include_security=True, force_collect=False):
    """Call PowerShell script to collect Windows Event Logs"""
    if force_collect:
        print(f"Forcing collection of fresh logs...")
    else:
        print(f"Collecting logs from the past {hours_back} hours...")
    
    # Prepare PowerShell command with appropriate path handling
    security_param = "false" if not include_security else "true"
    
    # Ensure the script path is properly formatted
    script_path = os.path.normpath(LOG_COLLECTOR_SCRIPT)
    output_file_path = os.path.normpath(output_path)
    
    # For Security logs on Windows, we need to run PowerShell as Administrator
    admin_note = ""
    if include_security and IS_WINDOWS:
        admin_note = "\nNote: For Security logs, PowerShell may need to run as Administrator."
    
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
        # Run the PowerShell script
        process = subprocess.run(
            ps_command,
            capture_output=True,
            text=True,
            check=True
        )
        
        # Print output from the script
        print(process.stdout)
        
        if "Security logs" in process.stdout and "0" in process.stdout and include_security:
            print(f"Warning: No Security logs were collected. This might be due to permission issues.{admin_note}")
        
        if process.returncode != 0:
            print(f"Error running log collector: {process.stderr}", file=sys.stderr)
            return False
            
        # Verify the output file was created
        if not os.path.exists(output_path):
            print(f"Error: Log file was not created at {output_path}", file=sys.stderr)
            return False
        
        # Verify JSON validity - try with utf-8-sig first
        try:
            with open(output_path, 'r', encoding='utf-8-sig') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            # Try with regular utf-8
            try:
                with open(output_path, 'r', encoding='utf-8') as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                print(f"Warning: Generated JSON file appears to be invalid: {e}")
                print("This might indicate an issue with the PowerShell script output.")
                return False
            
        print(f"Logs successfully collected and saved to {output_path}")
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
                force_collect=False, qa_mode=False, model_path=None, context_size=2048,
                verbose=False):
    """
    Analyze logs with the Animus CLI

    Args:
        log_file_path: Path to the logs JSON file
        query: Optional single query to process
        auto_collect: Whether to automatically collect logs if needed
        auto_collect_age: Max age of logs before auto-collection
        force_collect: Whether to force log collection
        qa_mode: Whether to start in QA mode
        model_path: Path to Llama model file
        context_size: Token context size for LLM
        verbose: Whether to show verbose output
    """
    # Create CLI object
    cli = AnimusCLI(
        auto_collect=auto_collect,
        auto_collect_age_hours=auto_collect_age,
        force_collect=force_collect,
        model_path=model_path,
        context_size=context_size,
        qa_mode=qa_mode, # Pass the initial qa_mode flag
        verbose=verbose
    )

    # Set logs path
    cli.logs_path = log_file_path

    # Initial log check/collection happens within command_loop now for better message order
    # # Check if logs exist and are fresh
    # if not os.path.exists(log_file_path) or force_collect:
    #     if auto_collect:
    #         cli.handle_collect_command([])
    #     else:
    #         cli.print_status(f"Log file not found at {log_file_path}", "error")
    #         return 1
    # elif auto_collect and not check_log_freshness(log_file_path, auto_collect_age):
    #     cli.print_status(f"Logs are older than {auto_collect_age} hours, collecting fresh logs...", "info")
    #     cli.handle_collect_command([])

    # Loading logs also happens within command_loop
    # # Try to load logs
    # if not cli.load_logs(log_file_path):
    #     return 1

    # Process single query and exit if provided
    if query:
        # Need to ensure logs are loaded before processing single query
        if not cli.load_logs(log_file_path):
             return 1 # Exit if logs can't be loaded
        print(f"{Fore.CYAN}Query: {Fore.WHITE}{query}")
        result = cli.process_query(query)
        print(f"\n{result}")
        return 0

    # If not a single query, start the command loop
    # The loop will handle QA mode startup messages internally
    # if qa_mode:
    #     cli.start_qa_mode() # This only sets the flag now

    cli.command_loop()
    return 0

def main():
    """Main entry point for the Animus CLI"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Run analysis
    return analyze_logs(
        log_file_path=args.output,
        query=args.query,
        auto_collect=not args.no_auto_collect,
        auto_collect_age=args.hours,
        force_collect=args.collect,
        qa_mode=args.qa or args.interactive,
        model_path=args.model_path,
        context_size=args.context_size,
        verbose=args.verbose
    )

if __name__ == "__main__":
    main()
