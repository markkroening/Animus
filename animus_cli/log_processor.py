"""
Log Processor for Animus CLI

This module processes Windows Event Logs to make them more efficient for LLM consumption by aggregating similar events, simplifying formatting, and generating statistics.
"""

import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from animus_cli.data_models import LogCollection, SystemInfo, EventLogEntry # Import necessary models


class LogProcessor:
    """Processes raw logs to make them more efficient for LLM consumption."""
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the log processor.
        
        Args:
            verbose: Whether to show verbose output.
        """
        self.verbose = verbose
    
    def process_logs(self, log_collection: LogCollection) -> Dict[str, Any]:
        """
        Process raw log data to make it more LLM-friendly.
        
        Args:
            log_collection: Parsed LogCollection object
            
        Returns:
            Processed log data optimized for LLM consumption
        """
        if not log_collection:
            raise ValueError("Invalid log data format")
            
        # Create a new structure for processed logs
        processed_data = {
            # Extract top-level info from LogCollection
            "CollectionInfo": { # Nest collection info as format_for_llm expects
                "CollectionTime": log_collection.collection_time,
                "TimeRange": log_collection.time_range,
            },
            "SystemInfo": self._extract_system_info(log_collection.system_info),
            "EventSummary": self._generate_event_summary(log_collection),
            "AggregatedEvents": {},
        }
        
        # Process events by log type
        if log_collection.system_events:
            processed_data["AggregatedEvents"]["System"] = self._aggregate_events(
                log_collection.system_events
            )
        if log_collection.application_events:
            processed_data["AggregatedEvents"]["Application"] = self._aggregate_events(
                log_collection.application_events
            )
        # Add other log types here if LogCollection includes them in the future
        
        return processed_data
    
    def _extract_system_info(self, system_info_obj: Optional[SystemInfo]) -> Dict[str, Any]:
        """
        Convert SystemInfo object to a dictionary suitable for formatting.
        (Replaces old method that processed raw dict)
        
        Args:
            system_info_obj: Parsed SystemInfo object.
            
        Returns:
            Dictionary representation of SystemInfo.
        """
        if not system_info_obj:
            return {"Error": "SystemInfo not available"}
            
        # Convert dataclass to dict - simple approach
        # We might need more sophisticated handling for nested objects/enums if any
        try:
            # Use vars() for simple dataclass to dict conversion
            sys_info_dict = vars(system_info_obj)
            # Optionally filter or rename keys if needed for format_for_llm
            return sys_info_dict
        except TypeError:
             # Fallback or more robust conversion if needed
             return {"Error": "Could not convert SystemInfo to dict"}
    
    def _aggregate_events(self, events: List[EventLogEntry]) -> List[Dict[str, Any]]:
        """
        Aggregate identical events to reduce redundancy.
        
        Args:
            events: List of parsed EventLogEntry objects
            
        Returns:
            List of aggregated events with occurrence counts and timestamps
        """
        # Group events by their key attributes
        event_groups = defaultdict(list)
        
        for event in events:
            # Create a key based on Source, EventID, and partial Message
            # Getting first 100 chars of message to allow for minor differences
            source = event.provider_name or ""
            event_id = event.event_id or 0
            message = event.message or ""
            message_key = message[:100] if message else ""
            
            # Create a compound key for grouping
            group_key = f"{source}|{event_id}|{message_key}"
            
            # Add the event object to the appropriate group
            event_groups[group_key].append(event)
        
        # Convert groups into aggregated events
        aggregated_events = []
        
        for group_key, group_events in event_groups.items():
            # Use the first event as the template
            template_event = group_events[0]
            
            # Extract all timestamps
            timestamps = [e.time_created for e in group_events]
            
            # Keep only essential fields to reduce size
            aggregated_event = {
                "LogName": template_event.log_name,
                "Level": template_event.level.value, # Use enum value
                "EventID": template_event.event_id,
                "ProviderName": template_event.provider_name,
                "Message": template_event.message,
                "OccurrenceCount": len(group_events),
                "Timestamps": sorted(timestamps, reverse=True)[:10],  # Sort and Limit here
                "AdditionalTimestamps": len(timestamps) - 10 if len(timestamps) > 10 else 0
            }
            
            aggregated_events.append(aggregated_event)
        
        # Sort by count (most frequent first) and then by most recent timestamp
        aggregated_events.sort(
            key=lambda e: (-e["OccurrenceCount"], e["Timestamps"][0] if e["Timestamps"] else ""), 
            reverse=False
        )
        
        return aggregated_events
    
    def _generate_event_summary(self, log_collection: LogCollection) -> Dict[str, Any]:
        """
        Generate statistical summary of events.
        
        Args:
            log_collection: Parsed LogCollection object
            
        Returns:
            Dictionary with statistical summaries
        """
        summary = {
            "TotalEvents": 0,
            "ByLogType": {},
            "ByLevel": {
                "Critical": 0,
                "Error": 0,
                "Warning": 0,
                "Information": 0,
                "Verbose": 0
            },
            "TopSources": [],
            "TopEventIDs": []
        }
        
        all_events = log_collection.system_events + log_collection.application_events
        summary["TotalEvents"] = len(all_events)
        
        # Initialize counts
        summary["ByLogType"]["System"] = len(log_collection.system_events)
        summary["ByLogType"]["Application"] = len(log_collection.application_events)
        # Add other log types if they exist in LogCollection in the future
        
        level_counts = defaultdict(int)
        source_counts = defaultdict(int)
        event_id_counts = defaultdict(int)
        source_log_map = {}
        event_id_log_map = {}
        
        for event in all_events:
            # Count by level
            level_name = event.level.value # Use enum value
            if level_name == "Critical": # Debug print specifically for critical events
                print(f"DEBUG: Event {event.event_id} from {event.provider_name} counted as Critical.")
            if level_name in summary["ByLevel"]:
                summary["ByLevel"][level_name] += 1
            
            # Count sources and event IDs
            source = event.provider_name
            if source:
                source_counts[source] += 1
                source_log_map[source] = event.log_name # Store log type for summary
                
            event_id = event.event_id
            if event_id:
                event_id_str = str(event_id)
                event_id_counts[event_id_str] += 1
                event_id_log_map[event_id_str] = event.log_name # Store log type for summary
        
        # Find top sources globally
        top_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        summary["TopSources"] = [
            {"Source": source, "Count": count, "LogType": source_log_map.get(source, "Unknown")}
            for source, count in top_sources if count > 1
        ]
        
        # Find top event IDs globally
        top_event_ids = sorted(event_id_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        summary["TopEventIDs"] = [
            {"EventID": event_id, "Count": count, "LogType": event_id_log_map.get(event_id, "Unknown")}
            for event_id, count in top_event_ids if count > 1
        ]
        
        return summary
    
    def _normalize_level_name(self, level: str) -> str:
        """
        Normalize level names to standard values.
        
        Args:
            level: Raw level value
            
        Returns:
            Normalized level name
        """
        level_str = str(level).lower()
        
        if level_str in ["1", "critical"]:
            return "Critical"
        elif level_str in ["2", "error"]:
            return "Error"
        elif level_str in ["3", "warning"]:
            return "Warning"
        elif level_str in ["4", "information", "info"]:
            return "Information"
        elif level_str in ["5", "verbose"]:
            return "Verbose"
        else:
            return "Information"  # Default
    
    def format_for_llm(self, processed_data: Dict[str, Any]) -> str:
        """
        Format processed data into a concise text string for LLM consumption.
        
        Args:
            processed_data: Processed log data from process_logs
            
        Returns:
            Formatted string ready for LLM
        """
        output = []
        
        # Add system information
        sys_info = processed_data.get("SystemInfo", {})
        if sys_info:
            output.append("## SYSTEM INFORMATION")
            output.append(f"OS: {sys_info.get('os_version', 'Unknown')}")
            output.append(f"Computer: {sys_info.get('computer_name', 'Unknown')}")
            output.append(f"Uptime: {sys_info.get('uptime', 'Unknown')}")
            output.append("")
        
        # Add collection info
        coll_info = processed_data.get("CollectionInfo", {})
        if coll_info:
            output.append("## COLLECTION INFORMATION")
            output.append(f"Collection Time: {coll_info.get('CollectionTime', 'Unknown')}")
            time_range = coll_info.get('TimeRange', {})
            output.append(f"Time Range: {time_range.get('StartTime', 'Unknown')} to {time_range.get('EndTime', 'Unknown')}")
            output.append("")
        
        # Add event summary statistics
        summary = processed_data.get("EventSummary", {})
        if summary:
            output.append("## EVENT SUMMARY")
            output.append(f"Total Events: {summary.get('TotalEvents', 0)}")
            
            # Add by log type
            log_types = summary.get("ByLogType", {})
            output.append("Events by Log Type:")
            for log_type, count in log_types.items():
                output.append(f"- {log_type}: {count}")
            
            # Add by level
            levels = summary.get("ByLevel", {})
            print(f"DEBUG: Event counts by level in summary: {levels}")
            output.append("Events by Severity Level:")
            for level, count in levels.items():
                if count > 0:  # Only show non-zero counts
                    output.append(f"- {level}: {count}")
            
            # Add top sources
            top_sources = summary.get("TopSources", [])
            if top_sources:
                output.append("Top Event Sources:")
                for source in top_sources:
                    output.append(f"- {source['Source']} ({source['LogType']}): {source['Count']} events")
            
            # Add top event IDs
            top_event_ids = summary.get("TopEventIDs", [])
            if top_event_ids:
                output.append("Top Event IDs:")
                for event_id in top_event_ids:
                    output.append(f"- Event ID {event_id['EventID']} ({event_id['LogType']}): {event_id['Count']} occurrences")
            
            output.append("")
        
        # Add aggregated events
        aggregated_events = processed_data.get("AggregatedEvents", {})
        if aggregated_events:
            output.append("## AGGREGATED EVENTS")
            
            # Process events by log type and severity
            for log_type, events in aggregated_events.items():
                # Include ALL aggregated events for this log type
                if events: # Check if there are any events for this log type
                    output.append(f"\n### {log_type} Events:")
                    # Events are already sorted by frequency in _aggregate_events
                    for event in events:
                        self._format_event(event, output)
        
        return "\n".join(output)
    
    def _format_event(self, event: Dict[str, Any], output_lines: List[str]):
        """
        Format a single event for text output.
        
        Args:
            event: Event dictionary
            output_lines: List to append formatted lines to
        """
        # Base event info
        event_id = event.get("EventID", "?")
        source = event.get("ProviderName", "Unknown")
        level = event.get("Level", "")
        level_name = self._normalize_level_name(level)
        message = event.get("Message", "No message")
        
        # Format message: replace newlines with spaces, truncate if needed
        message = message.replace("\n", " ").replace("\r", "")
        if len(message) > 200:
            message = message[:197] + "..."
        
        # Count and timestamps
        count = event.get("OccurrenceCount", 1)
        timestamps = event.get("Timestamps", [])
        additional = event.get("AdditionalTimestamps", 0)
        
        # Format the output
        header = f"{level_name} | {source} | Event ID: {event_id} | Count: {count}"
        output_lines.append(header)
        output_lines.append(f"Message: {message}")
        
        # Add timestamps (first few)
        if timestamps:
            # Join all available timestamps (up to 10 most recent from aggregation)
            ts_str = ", ".join(timestamps)
            output_lines.append(f"When: {ts_str}")
        
        output_lines.append("")  # Empty line for spacing


def process_log_file(input_file: str, output_file: Optional[str] = None, verbose: bool = False) -> Tuple[str, Dict[str, Any]]:
    """
    Process a log file for LLM consumption.
    
    Args:
        input_file: Path to the input JSON log file
        output_file: Optional path to save the processed data as JSON
        verbose: Whether to show verbose output
        
    Returns:
        Tuple of (formatted text for LLM, processed data dictionary)
    """
    # Load the input file
    try:
        with open(input_file, 'r', encoding='utf-8-sig') as f:
            try:
                log_data = json.load(f)
            except json.JSONDecodeError:
                # Try with regular UTF-8
                f.seek(0)
                log_data = json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load log file: {e}")
    
    # Process the logs
    processor = LogProcessor(verbose=verbose)
    processed_data = processor.process_logs(log_data)
    
    # Format for LLM
    formatted_text = processor.format_for_llm(processed_data)
    
    # Save processed data if requested
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, indent=2)
        except Exception as e:
            print(f"Warning: Failed to save processed data: {e}")
    
    return formatted_text, processed_data


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python log_processor.py <input_file> [output_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        formatted_text, _ = process_log_file(input_file, output_file, verbose=True)
        print("\nFormatted Text Sample (first 1000 chars):")
        print("-" * 80)
        print(formatted_text[:1000])
        print("-" * 80)
        print(f"Full text length: {len(formatted_text)} characters")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1) 