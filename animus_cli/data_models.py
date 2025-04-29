"""
Data models for representing Windows Event Log data.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional

class EventLevel(Enum):
    """Enumeration for standard event levels."""
    CRITICAL = "Critical"
    ERROR = "Error"
    WARNING = "Warning"
    INFORMATION = "Information"
    VERBOSE = "Verbose"
    UNKNOWN = "Unknown"

    @classmethod
    def from_string(cls, level_str: Optional[str]) -> 'EventLevel':
        """Safely convert a string level to an EventLevel enum member."""
        if not level_str:
            return cls.UNKNOWN

        # Ensure input is treated as string before calling .lower()
        level_str = str(level_str).lower() # Convert to string and lower case

        level_map = {
            # Map both text names and common numeric codes
            "critical": cls.CRITICAL, "1": cls.CRITICAL,
            "error": cls.ERROR,       "2": cls.ERROR,
            "warning": cls.WARNING,     "3": cls.WARNING,
            "information": cls.INFORMATION, "4": cls.INFORMATION, "info": cls.INFORMATION,
            "verbose": cls.VERBOSE,     "5": cls.VERBOSE,
        }
        return level_map.get(level_str, cls.UNKNOWN) # Use level_str directly as it's already lowercase

@dataclass
class EventLogEntry:
    """Structured representation of a single Windows Event Log entry."""
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
        """Create an EventLogEntry from a dictionary (e.g., from JSON)."""
        # Helper for safe type conversion
        def safe_int(value: Any) -> Optional[int]:
            try:
                return int(value) if value is not None else None
            except (ValueError, TypeError):
                return None

        return cls(
            time_created=str(data.get('TimeCreated', '')),
            log_name=str(data.get('LogName', '')),
            level=EventLevel.from_string(data.get('EntryType', '')),
            event_id=safe_int(data.get('EventID')) or 0,
            provider_name=str(data.get('ProviderName', '')),
            message=str(data.get('Message', '')),
            machine_name=str(data.get('MachineName', '')),
            user_id=data.get('UserId'), # Assumes string or None
            task_display_name=data.get('TaskDisplayName'), # Assumes string or None
            process_id=safe_int(data.get('ProcessId')),
            thread_id=safe_int(data.get('ThreadId'))
        )

@dataclass
class SystemInfo:
    """Structured representation of system information."""
    os_name: str = "Unknown"
    os_version: str = "Unknown"
    os_build: str = "Unknown"
    architecture: str = "Unknown"
    install_date: str = "Unknown"
    last_boot_time: str = "Unknown"
    uptime: str = "Unknown"
    manufacturer: str = "Unknown"
    model: str = "Unknown"
    system_type: str = "Unknown"
    processors: int = 0
    memory: str = "Unknown"
    processor_name: str = "Unknown"
    cores: int = 0
    logical_processors: int = 0
    clock_speed: str = "Unknown"
    computer_name: str = "Unknown"
    disks: List[Dict[str, str]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemInfo':
        """Create SystemInfo from a dictionary provided by collect_logs.ps1."""
        # PowerShell script provides a flat dictionary
        return cls(
            # Map keys from PowerShell script output
            computer_name=str(data.get('ComputerName', 'Unknown')),
            os_version=str(data.get('OSVersion', 'Unknown')),
            last_boot_time=str(data.get('LastBootTime', 'Unknown')),
            uptime=str(data.get('Uptime', 'Unknown')) + " hours", # Add units
            
            # Other fields not provided by the current script
            os_name="Unknown",
            os_build="Unknown",
            architecture="Unknown",
            install_date="Unknown",
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
    """Represents a complete collection of logs and system info."""
    collection_time: str
    time_range: Dict[str, str]
    system_info: SystemInfo
    system_events: List[EventLogEntry]
    application_events: List[EventLogEntry]

    # Combined list of all events, calculated on demand
    _all_events: Optional[List[EventLogEntry]] = field(init=False, default=None)

    @property
    def all_events(self) -> List[EventLogEntry]:
        """Get all events combined (lazy loaded)."""
        if self._all_events is None:
            self._all_events = (
                self.system_events +
                self.application_events
            )
        return self._all_events

    @property
    def error_events(self) -> List[EventLogEntry]:
        """Get all error and critical events."""
        return [
            e for e in self.all_events
            if e.level in (EventLevel.ERROR, EventLevel.CRITICAL)
        ]

    @property
    def warning_events(self) -> List[EventLogEntry]:
        """Get all warning events."""
        return [
            e for e in self.all_events
            if e.level == EventLevel.WARNING
        ]

    @property
    def event_count(self) -> Dict[str, int]:
        """Get counts of events by type."""
        return {
            "system": len(self.system_events),
            "application": len(self.application_events),
            "total": len(self.all_events),
            "errors": len(self.error_events),
            "warnings": len(self.warning_events)
        }

    def get_summary(self) -> Dict[str, Any]:
        """Generate a concise summary of the log collection."""
        counts = self.event_count
        sys_info = self.system_info
        return {
            "collection_time": self.collection_time,
            "time_range": self.time_range,
            "event_counts": counts,
            "system_summary": {
                "os": f"{sys_info.os_name} ({sys_info.os_version})",
                "computer": sys_info.computer_name,
                "model": f"{sys_info.manufacturer} {sys_info.model}",
                "uptime": sys_info.uptime,
            },
            "error_count": counts["errors"],
            "warning_count": counts["warnings"],
        } 