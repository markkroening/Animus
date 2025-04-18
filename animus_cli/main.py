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

class AnimusCLI:
    """Main CLI class for Animus"""
    
    def __init__(self, auto_collect=True, auto_collect_age_hours=24, force_collect=False):
        self.running = False
        self.log_file = DEFAULT_OUTPUT_PATH
        self.logs_loaded = False
        self.log_data = None  # The raw JSON data
        self.logs = None  # The parsed LogCollection
        self.history_file = os.path.expanduser("~/.animus_history")
        self.auto_collect = auto_collect
        self.auto_collect_age_hours = auto_collect_age_hours
        self.force_collect = force_collect
        self.in_qa_mode = False
        self.qa_context = []  # Store conversation history for context
        
        # Only set up history if readline is available
        if READLINE_AVAILABLE:
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
        """Print the Animus CLI banner"""
        print(ANIMUS_BANNER)
        
    def print_help(self):
        """Print available commands and help information"""
        print(f"\n{Fore.CYAN}Available Commands:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}collect{Style.RESET_ALL} [hours] [max_events] [--no-security] [--force]")
        print(f"  Collect Windows Event Logs (default: past 48 hours, 500 events per log)")
        print(f"{Fore.YELLOW}load{Style.RESET_ALL} [filename]")
        print(f"  Load a previously collected log file (default: {os.path.basename(self.log_file)})")
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
        if self.logs_loaded:
            return True
            
        if os.path.exists(self.log_file):
            return self.load_logs(self.log_file)
        else:
            self.print_status(
                f"No log file found at {self.log_file}. Please collect logs first with 'collect'.", 
                "error"
            )
            return False
    
    def load_logs(self, filename=None):
        """Load logs from a JSON file"""
        if filename:
            self.log_file = filename
            
        try:
            self.print_status(f"Loading logs from {self.log_file}...")
            
            # First, check if the file is valid JSON
            try:
                # Try with utf-8-sig first to handle BOM
                try:
                    with open(self.log_file, 'r', encoding='utf-8-sig') as f:
                        raw_data = f.read()
                except UnicodeDecodeError:
                    # Fall back to regular utf-8
                    with open(self.log_file, 'r', encoding='utf-8') as f:
                        raw_data = f.read()
                    
                # Check for common encoding issues or malformed JSON
                if not raw_data or len(raw_data.strip()) == 0:
                    self.print_status("Log file exists but is empty", "error")
                    self.logs_loaded = False
                    return False
                    
                # Try to parse the JSON
                try:
                    self.log_data = json.loads(raw_data)
                except json.JSONDecodeError as e:
                    # Get more details about the JSON parsing error
                    line_no = e.lineno
                    col_no = e.colno
                    # Try to extract the problematic part for debugging
                    lines = raw_data.split('\n')
                    if 0 <= line_no - 1 < len(lines):
                        problem_line = lines[line_no - 1]
                        # Highlight the position of the error
                        error_indicator = ' ' * (col_no - 1) + '^'
                        error_context = f"Line {line_no}, position {col_no}:\n{problem_line}\n{error_indicator}"
                        self.print_status(f"JSON parse error: {e.msg}\n{error_context}", "error")
                    else:
                        self.print_status(f"JSON parse error: {e.msg} at line {line_no}, position {col_no}", "error")
                    
                    self.logs_loaded = False
                    return False
            except Exception as e:
                self.print_status(f"Error reading log file: {str(e)}", "error")
                self.logs_loaded = False
                return False
            
            # Parse the log file using our parser
            parsed_logs = LogParser.parse_file(self.log_file)
            
            if not parsed_logs:
                self.print_status("Failed to parse log file", "error")
                self.logs_loaded = False
                return False
                
            # Store the parsed data
            self.logs = parsed_logs
            
            # Print a summary
            event_counts = self.logs.event_count
            self.print_status(
                f"Successfully loaded {event_counts['total']} events "
                f"({event_counts['errors']} errors, {event_counts['warnings']} warnings)",
                "success"
            )
            
            self.logs_loaded = True
            return True
            
        except json.JSONDecodeError as e:
            # This should rarely happen now that we're handling JSON errors above
            self.print_status(f"Invalid JSON format in {self.log_file}: {str(e)}", "error")
        except FileNotFoundError:
            self.print_status(f"Log file not found: {self.log_file}", "error")
        except Exception as e:
            self.print_status(f"Error loading logs: {str(e)}", "error")
            
        self.logs_loaded = False
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
        if not os.path.exists(self.log_file):
            self.print_status("No existing log file found. Will collect logs automatically.", "info")
            return True
            
        try:
            # Check file age
            file_stat = os.stat(self.log_file)
            file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
            current_time = datetime.now()
            age_hours = (current_time - file_mtime).total_seconds() / 3600
            
            if age_hours > self.auto_collect_age_hours:
                self.print_status(
                    f"Log file is {age_hours:.1f} hours old (threshold: {self.auto_collect_age_hours} hours). Collecting fresh logs.", 
                    "info"
                )
                return True
                
            # Try to validate the logs
            try:
                with open(self.log_file, 'r') as f:
                    log_data = json.load(f)
                    if not isinstance(log_data, dict) or 'Events' not in log_data:
                        self.print_status("Existing log file has invalid format. Will collect fresh logs.", "warning")
                        return True
            except (json.JSONDecodeError, FileNotFoundError):
                self.print_status("Existing log file is corrupt or unreadable. Will collect fresh logs.", "warning")
                return True
                
            self.print_status(f"Using existing log file from {file_mtime.strftime('%Y-%m-%d %H:%M:%S')}", "info")
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
            summary = self.logs.summarize()
            
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
        """Main interactive command loop"""
        self.running = True
        self.print_banner()
        
        # Check if we should automatically collect logs on startup
        if self.should_collect_logs():
            self.print_status("Collecting logs on startup...", "info")
            self.handle_collect_command([])
        elif os.path.exists(self.log_file) and not self.logs_loaded:
            # Try to load existing logs
            self.load_logs()
            
        self.print_status("Type 'help' for available commands or 'exit' to quit")
        
        while self.running:
            try:
                # Display prompt
                if self.in_qa_mode:
                    user_input = input(f"{Fore.MAGENTA}question> {Style.RESET_ALL}").strip()
                else:
                    user_input = input(f"{Fore.GREEN}animus> {Style.RESET_ALL}").strip()
                
                # Skip empty input
                if not user_input:
                    continue
                    
                # Handle special case for Q&A mode
                if self.in_qa_mode:
                    if user_input.lower() in ('exit', 'quit', 'back', 'end'):
                        self.in_qa_mode = False
                        self.print_status("Exiting Q&A mode", "info")
                        continue
                    else:
                        self.handle_query(user_input, add_to_context=True)
                        continue
                    
                # Parse the command and arguments for normal mode
                try:
                    parts = shlex.split(user_input)
                    command = parts[0].lower()
                    args = parts[1:]
                except ValueError as e:
                    self.print_status(f"Invalid input: {e}", "error")
                    continue
                
                # Process commands
                if command in ['exit', 'quit']:
                    self.running = False
                    break
                elif command == 'help':
                    self.print_help()
                elif command == 'collect':
                    self.handle_collect_command(args)
                elif command == 'load':
                    filename = args[0] if args else self.log_file
                    self.load_logs(filename)
                elif command == 'status':
                    self.show_status()
                elif command == 'ask':
                    question = ' '.join(args)
                    if question:
                        self.handle_query(question)
                    else:
                        self.print_status("Please provide a question after 'ask'", "error")
                elif command == 'qa':
                    self.start_qa_mode()
                else:
                    # Treat unrecognized commands as questions if logs are loaded
                    self.handle_query(user_input)
                    
            except KeyboardInterrupt:
                print()  # Add a newline
                if self.in_qa_mode:
                    self.in_qa_mode = False
                    self.print_status("Exiting Q&A mode", "info")
                else:
                    self.print_status("Use 'exit' to quit", "info")
            except EOFError:
                print()  # Add a newline
                self.running = False
                break
            except Exception as e:
                self.print_status(f"Error: {e}", "error")
                
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
                self.log_file,
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
        """Start an interactive Q&A session"""
        if not self.check_log_loaded():
            return
            
        self.in_qa_mode = True
        self.qa_context = []  # Reset context
        
        print(f"\n{Fore.CYAN}═════════════════════════════════════════════════════{Style.RESET_ALL}")
        print(f"{Fore.MAGENTA}Interactive Q&A Mode{Style.RESET_ALL}")
        print(f"Ask questions about your Windows system and event logs.")
        print(f"Type {Fore.YELLOW}exit{Style.RESET_ALL}, {Fore.YELLOW}quit{Style.RESET_ALL}, or {Fore.YELLOW}back{Style.RESET_ALL} to return to the main CLI.")
        print(f"{Fore.CYAN}═════════════════════════════════════════════════════{Style.RESET_ALL}\n")
        
        # Provide a helpful starting prompt
        self.print_status("You can ask about errors, system information, specific event IDs, or search for keywords.", "info")
        
        # Show a summary of the system to help the user get started
        system = self.logs.system_info
        print(f"\n{Fore.CYAN}System Summary:{Style.RESET_ALL}")
        print(f"OS: {system.os_name} {system.os_version}")
        print(f"Model: {system.manufacturer} {system.model}")
        print(f"Uptime: {system.uptime}")
        
        # Show count of errors if any
        error_count = len(self.logs.error_events)
        warning_count = len(self.logs.warning_events)
        if error_count > 0:
            print(f"\n{Fore.RED}Found {error_count} error/critical events and {warning_count} warnings{Style.RESET_ALL}")
            print(f"Try asking: 'What errors have occurred?' or 'Show me recent errors'")
        else:
            print(f"\nNo critical errors found in the logs. Try asking about system information or events.")

    def handle_query(self, query, add_to_context=False):
        """Handle a query about the logs"""
        if not self.check_log_loaded():
            return
        
        # Format the query for display
        if self.in_qa_mode:
            print(f"{Fore.CYAN}Q: {query}{Style.RESET_ALL}")
        else:
            self.print_status(f"Query: {query}", "question")
            
        # Track the query in context if in QA mode
        if add_to_context:
            self.qa_context.append({"role": "user", "content": query})
            
        # Process the query
        answer = self.process_query(query)
        
        # Format and display the answer
        if self.in_qa_mode:
            print(f"{Fore.YELLOW}A: {Style.RESET_ALL}{answer}\n")
            # Add the answer to context
            self.qa_context.append({"role": "assistant", "content": answer})
        else:
            print(f"\n{answer}\n")
    
    def process_query(self, query):
        """Process a query and return an answer"""
        query_lower = query.lower()
        answer = ""
        
        # Use context to potentially improve answers in QA mode
        # This is a placeholder - in a real implementation, we'd use an LLM to process the context
        previous_questions = []
        if self.in_qa_mode and len(self.qa_context) > 0:
            previous_questions = [item["content"] for item in self.qa_context if item["role"] == "user"]
            
        # Extract event ID if present
        event_id_match = re.search(r'event\s+id\s*[:=]?\s*(\d+)', query_lower)
        if event_id_match:
            event_id = int(event_id_match.group(1))
            events = self.logs.events_by_id(event_id)
            
            if events:
                answer = f"Found {len(events)} events with ID {event_id}:\n\n"
                for i, event in enumerate(events[:5], 1):  # Show first 5
                    answer += f"{i}. [{event.time_created}] {event.provider_name}\n"
                    answer += f"   {event.message[:200]}...\n\n"
                if len(events) > 5:
                    answer += f"...and {len(events) - 5} more\n"
            else:
                answer = f"No events found with ID {event_id}"
            return answer
            
        # Error queries - look for words like errors, issues, problems, critical
        if any(word in query_lower for word in ["error", "issue", "problem", "critical", "fail", "crash"]):
            errors = self.logs.error_events
            if errors:
                answer = f"Found {len(errors)} error/critical events:\n\n"
                for i, event in enumerate(errors[:5], 1):  # Show first 5
                    answer += f"{i}. [{event.time_created}] {event.provider_name} (ID: {event.event_id})\n"
                    answer += f"   {event.message[:200]}...\n\n"
                if len(errors) > 5:
                    answer += f"...and {len(errors) - 5} more\n"
            else:
                answer = "No error events found in the collected logs."
            return answer
            
        # Warning queries
        if "warning" in query_lower:
            warnings = self.logs.warning_events
            if warnings:
                answer = f"Found {len(warnings)} warning events:\n\n"
                for i, event in enumerate(warnings[:5], 1):  # Show first 5
                    answer += f"{i}. [{event.time_created}] {event.provider_name} (ID: {event.event_id})\n"
                    answer += f"   {event.message[:200]}...\n\n"
                if len(warnings) > 5:
                    answer += f"...and {len(warnings) - 5} more\n"
            else:
                answer = "No warning events found in the collected logs."
            return answer
            
        # Recent events queries
        if any(word in query_lower for word in ["recent", "latest", "last", "new"]):
            events = self.logs.recent_events(10)  # Get 10 most recent
            if events:
                answer = f"Here are the 10 most recent events:\n\n"
                for i, event in enumerate(events, 1):
                    answer += f"{i}. [{event.time_created}] {event.provider_name} ({event.level.value}, ID: {event.event_id})\n"
                    answer += f"   {event.message[:100]}...\n\n"
            else:
                answer = "No events found in the collected logs."
            return answer
            
        # System information query
        if any(x in query_lower for x in ["system", "os", "hardware", "computer", "configuration", "specs", "about"]):
            system = self.logs.system_info
            answer = f"System Information:\n\n"
            answer += f"OS: {system.os_name} {system.os_version} (Build {system.os_build})\n"
            answer += f"Architecture: {system.architecture}\n"
            answer += f"Manufacturer: {system.manufacturer}\n"
            answer += f"Model: {system.model}\n"
            answer += f"Processor: {system.processor_name}\n"
            answer += f"Cores: {system.cores} physical, {system.logical_processors} logical\n"
            answer += f"Memory: {system.memory}\n"
            answer += f"Install Date: {system.install_date}\n"
            answer += f"Last Boot: {system.last_boot_time}\n"
            answer += f"Uptime: {system.uptime}\n"
            
            if system.disks:
                answer += f"\nDisks:\n"
                for disk in system.disks:
                    answer += f"  {disk.get('DeviceID', 'Unknown')}: " 
                    answer += f"{disk.get('Size', 'Unknown')} total, " 
                    answer += f"{disk.get('FreeSpace', 'Unknown')} free " 
                    answer += f"({disk.get('PercentFree', 'Unknown')})\n"
            return answer
            
        # Count or summary queries
        if any(word in query_lower for word in ["count", "summary", "statistics", "stats", "overview", "how many"]):
            counts = self.logs.event_count
            collection_time = self.logs.collection_time
            time_range = self.logs.time_range
            
            answer = f"Log Summary (collected on {collection_time}):\n\n"
            answer += f"Time Range: {time_range.get('StartTime', 'Unknown')} to {time_range.get('EndTime', 'Unknown')}\n\n"
            answer += f"Event Counts:\n"
            answer += f"- System: {counts['system']}\n"
            answer += f"- Application: {counts['application']}\n"
            answer += f"- Security: {counts['security']}\n"
            answer += f"- Total: {counts['total']}\n"
            answer += f"- Errors/Critical: {counts['errors']}\n"
            answer += f"- Warnings: {counts['warnings']}\n"
            return answer
        
        # Help queries - recognize various forms of help requests
        if any(word in query_lower for word in ["help", "how to", "commands", "usage", "what can you do", "what can i ask"]):
            answer = "Here are some things you can ask me about:\n\n"
            answer += "- 'Show me recent errors' - Display recent error events\n"
            answer += "- 'What warnings are there?' - List warning events\n" 
            answer += "- 'Tell me about event ID 1234' - Find events with a specific ID\n"
            answer += "- 'System information' - Show hardware and OS details\n"
            answer += "- 'Show recent events' - Display the most recent events\n"
            answer += "- 'How many events are there?' - Get counts and statistics\n"
            answer += "- 'Search for network' - Find events containing specific text\n\n"
            answer += "You can also ask for help or type 'exit' to leave Q&A mode."
            return answer
        
        # Generic text search for anything else
        if len(query) > 3:  # Only search if query is substantial
            events = self.logs.events_by_text(query)
            if events:
                answer = f"Found {len(events)} events matching '{query}':\n\n"
                for i, event in enumerate(events[:5], 1):  # Show first 5
                    answer += f"{i}. [{event.time_created}] {event.provider_name} ({event.level.value}, ID: {event.event_id})\n"
                    answer += f"   {event.message[:200]}...\n\n"
                if len(events) > 5:
                    answer += f"...and {len(events) - 5} more\n"
            else:
                answer = f"No events found matching '{query}'"
            return answer
            
        # Default response if no patterns matched
        answer = "I don't have enough information to answer that question specifically. Try asking about errors, warnings, system information, or specific event IDs.\n\nIn the future, this CLI will integrate with an LLM for more advanced analysis. For now, you can try rephrasing your question or type 'help' to see examples of what you can ask."
        return answer

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Animus CLI - Windows Event Log Analyzer")
    parser.add_argument("--collect-logs", action="store_true", help="Collect Windows Event Logs")
    parser.add_argument("--collect-now", action="store_true", help="Force immediate log collection regardless of existing log age")
    parser.add_argument("--output", "-o", default=DEFAULT_OUTPUT_PATH, help="Output file path for logs")
    parser.add_argument("--hours", type=int, default=48, help="Hours of logs to collect (default: 48)")
    parser.add_argument("--max-events", type=int, default=500, help="Maximum events per log type (default: 500)")
    parser.add_argument("--no-security", action="store_true", help="Exclude Security logs")
    parser.add_argument("--analyze", action="store_true", help="Start analysis mode (interactive Q&A)")
    parser.add_argument("--qa", action="store_true", help="Start interactive Q&A mode")
    parser.add_argument("--query", "-q", help="Single query mode (non-interactive)")
    parser.add_argument("--interactive", "-i", action="store_true", help="Start interactive CLI mode")
    parser.add_argument("--version", "-v", action="store_true", help="Show version information")
    parser.add_argument("--no-auto-collect", action="store_true", help="Disable automatic log collection on startup")
    parser.add_argument("--auto-collect-age", type=int, default=24, help="Auto-collect if logs are older than this many hours (default: 24)")
    
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

def analyze_logs(log_file_path, query=None, auto_collect=True, auto_collect_age=24, force_collect=False, qa_mode=False):
    """Analyze logs and optionally enter interactive Q&A mode"""
    # Check if log collection is needed
    if force_collect or (auto_collect and not check_log_freshness(log_file_path, auto_collect_age)):
        text = "Forced collection of fresh logs..." if force_collect else "Log file is outdated or missing. Collecting fresh logs..."
        print(text)
        collect_logs(log_file_path, force_collect=force_collect)
    
    if not os.path.exists(log_file_path):
        print(f"Error: Log file not found at {log_file_path}", file=sys.stderr)
        print("Please collect logs first using the --collect-logs option.", file=sys.stderr)
        return False
        
    print(f"Starting analysis of logs from {log_file_path}")
    
    # Create CLI instance and load logs
    cli = AnimusCLI(auto_collect=auto_collect, auto_collect_age_hours=auto_collect_age, force_collect=force_collect)
    cli.log_file = log_file_path
    
    # Load the logs
    if not cli.load_logs():
        return False
    
    # Handle different modes
    if query:
        # Single query mode - just answer and exit
        cli.handle_query(query)
        return True
    elif qa_mode:
        # Start in QA mode directly
        cli.start_qa_mode()
        cli.command_loop()
        return True
    else:
        # Regular command loop
        cli.command_loop()
        return True

def main():
    """Main entry point for the Animus CLI tool"""
    args = parse_arguments()
    
    # Show version and exit
    if args.version:
        print(f"Animus CLI v{ANIMUS_VERSION}")
        return
    
    # Check if PowerShell is available (required for log collection)
    if not check_powershell_requirements():
        sys.exit(1)
    
    # Set up auto-collection settings
    auto_collect = not args.no_auto_collect
    auto_collect_age = args.auto_collect_age
    force_collect = args.collect_now
        
    # Collect logs if requested or needed
    if args.collect_logs or args.collect_now:
        success = collect_logs(
            args.output,
            args.hours,
            args.max_events,
            not args.no_security,
            force_collect=args.collect_now
        )
        if not success:
            sys.exit(1)
    elif auto_collect and not check_log_freshness(args.output, auto_collect_age):
        print(f"Log file is outdated or missing. Collecting fresh logs...")
        success = collect_logs(
            args.output,
            args.hours,
            args.max_events, 
            not args.no_security
        )
        if not success:
            sys.exit(1)
    
    # Start interactive mode if requested
    if args.interactive or (not any([args.collect_logs, args.collect_now, args.query, args.analyze, args.qa]) and not args.version):
        cli = AnimusCLI(auto_collect=auto_collect, auto_collect_age_hours=auto_collect_age, force_collect=force_collect)
        cli.log_file = args.output
        cli.command_loop()
        return
    
    # Analyze logs if requested
    if args.analyze or args.query or args.qa:
        log_path = args.output
        success = analyze_logs(
            log_path, 
            args.query, 
            auto_collect=auto_collect, 
            auto_collect_age=auto_collect_age,
            force_collect=force_collect,
            qa_mode=args.qa
        )
        if not success:
            sys.exit(1)
    
    # If no action was specified and not in interactive mode, show help
    if not (args.collect_logs or args.collect_now or args.analyze or args.query or args.interactive or args.qa or args.version):
        parser = argparse.ArgumentParser()
        parser.print_help()

if __name__ == "__main__":
    main()
