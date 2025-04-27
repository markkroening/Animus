"""
Parses JSON log data into structured LogCollection objects.
"""

import json
import sys
from typing import Dict, Any, Optional
from pathlib import Path

from animus_cli.data_models import LogCollection, SystemInfo, EventLogEntry

class LogParser:
    """Parses Windows Event Logs from JSON data or file."""

    @staticmethod
    def parse_json_data(data: Dict[str, Any]) -> Optional[LogCollection]:
        """Parse JSON data (as dict) into a LogCollection.

        Args:
            data: The dictionary loaded from JSON.

        Returns:
            A LogCollection object or None if parsing fails.
        """
        try:
            collection_info = data.get('CollectionInfo', {})
            system_info_data = data.get('SystemInfo', {})
            events_data = data.get('Events', {})

            system_info = SystemInfo.from_dict(system_info_data)

            # Helper to parse event lists
            def parse_event_list(raw_events: list) -> list[EventLogEntry]:
                parsed = []
                if isinstance(raw_events, list):
                    for event_dict in raw_events:
                        if isinstance(event_dict, dict):
                            # Add basic check to skip clearly invalid entries
                            if event_dict.get('TimeCreated') or event_dict.get('Message'):
                                parsed.append(EventLogEntry.from_dict(event_dict))
                return parsed

            return LogCollection(
                collection_time=collection_info.get('CollectionTime', 'Unknown'),
                time_range=collection_info.get('TimeRange', {}),
                system_info=system_info,
                system_events=parse_event_list(events_data.get('System', [])),
                application_events=parse_event_list(events_data.get('Application', [])),
                security_events=parse_event_list(events_data.get('Security', []))
            )
        except Exception as e:
            # Keep minimal error logging for critical parsing failures
            print(f"Error: Failed to parse structured log data: {e}", file=sys.stderr)
            return None

    @staticmethod
    def parse_file(file_path: Path) -> Optional[LogCollection]:
        """Parse logs from a JSON file.

        Args:
            file_path: Path object pointing to the JSON log file.

        Returns:
            A LogCollection object or None if the file cannot be read or parsed.
        """
        try:
            # Assume UTF-8/UTF-8-SIG which PowerShell often outputs
            raw_data = file_path.read_text(encoding='utf-8-sig')

            if not raw_data.strip():
                print(f"Error: Log file is empty: {file_path}", file=sys.stderr)
                return None

            data = json.loads(raw_data)
            return LogParser.parse_json_data(data)

        except FileNotFoundError:
            print(f"Error: Log file not found: {file_path}", file=sys.stderr)
            return None
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON format in {file_path}: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Error parsing log file {file_path}: {e}", file=sys.stderr)
            return None 