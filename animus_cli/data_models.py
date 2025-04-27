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

        level_map = {
            "critical": cls.CRITICAL,
            "error": cls.ERROR,
            "warning": cls.WARNING,
            "information": cls.INFORMATION,
            "verbose": cls.VERBOSE,
        }
        return level_map.get(level_str.lower(), cls.UNKNOWN)

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
            level=EventLevel.from_string(data.get('Level', '')),
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
        """Create SystemInfo from a dictionary."""
        os_info = data.get('OS', {})
        comp_info = data.get('Computer', {})
        proc_info = data.get('Processor', {})
        disks_info = data.get('Disks', [])

        # Helper for safe type conversion
        def safe_int(value: Any) -> int:
            try:
                return int(value) if value is not None else 0
            except (ValueError, TypeError):
                return 0

        return cls(
            os_name=str(os_info.get('Caption', 'Unknown OS')),
            os_version=str(os_info.get('Version', 'Unknown')),
            os_build=str(os_info.get('BuildNumber', 'Unknown')),
            architecture=str(os_info.get('OSArchitecture', 'Unknown')),
            install_date=str(os_info.get('InstallDate', 'Unknown')),
            last_boot_time=str(os_info.get('LastBootUpTime', 'Unknown')),
            uptime=str(os_info.get('UpTime', 'Unknown')),
            manufacturer=str(comp_info.get('Manufacturer', 'Unknown')),
            model=str(comp_info.get('Model', 'Unknown')),
            system_type=str(comp_info.get('SystemType', 'Unknown')),
            processors=safe_int(comp_info.get('NumberOfProcessors')),
            memory=str(comp_info.get('TotalPhysicalMemory', 'Unknown')),
            computer_name=str(comp_info.get('Name', 'Unknown')),
            processor_name=str(proc_info.get('Name', 'Unknown')),
            cores=safe_int(proc_info.get('NumberOfCores')),
            logical_processors=safe_int(proc_info.get('NumberOfLogicalProcessors')),
            clock_speed=str(proc_info.get('MaxClockSpeedGHz', 'Unknown')),
            disks=disks_info if isinstance(disks_info, list) else []
        )

@dataclass
class LogCollection:
    """Represents a complete collection of logs and system info."""
    collection_time: str
    time_range: Dict[str, str]
    system_info: SystemInfo
    system_events: List[EventLogEntry]
    application_events: List[EventLogEntry]
    security_events: List[EventLogEntry]

    # Combined list of all events, calculated on demand
    _all_events: Optional[List[EventLogEntry]] = field(init=False, default=None)

    @property
    def all_events(self) -> List[EventLogEntry]:
        """Get all events combined (lazy loaded)."""
        if self._all_events is None:
            self._all_events = (
                self.system_events +
                self.application_events +
                self.security_events
            )
            # Optionally sort by time if needed, assuming time_created is parsable
            # self._all_events.sort(key=lambda e: e.time_created, reverse=True)
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
            "security": len(self.security_events),
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