"""
Log Processor for Animus CLI

This module processes Windows Event Logs to make them more efficient for LLM consumption by aggregating similar events, simplifying formatting, and generating statistics.
"""

import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple


class LogProcessor:
    """Processes raw logs to make them more efficient for LLM consumption."""
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the log processor.
        
        Args:
            verbose: Whether to show verbose output.
        """
        self.verbose = verbose
    
    def process_logs(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw log data to make it more LLM-friendly.
        
        Args:
            log_data: Raw log data dictionary as loaded from animus_logs.json
            
        Returns:
            Processed log data optimized for LLM consumption
        """
        if not log_data or not isinstance(log_data, dict):
            raise ValueError("Invalid log data format")
            
        # Create a new structure for processed logs
        processed_data = {
            "CollectionInfo": log_data.get("CollectionInfo", {}),
            "SystemInfo": self._extract_system_info(log_data.get("SystemInfo", {})),
            "EventSummary": self._generate_event_summary(log_data),
            "AggregatedEvents": {},
        }
        
        # Process events by log type
        events_data = log_data.get("Events", {})
        for log_type in ["System", "Application", "Security"]:
            if log_type in events_data:
                processed_data["AggregatedEvents"][log_type] = self._aggregate_events(
                    events_data[log_type]
                )
                
        return processed_data
    
    def _extract_system_info(self, system_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and normalize system information for better LLM consumption.
        
        Args:
            system_info: Raw system information dictionary
            
        Returns:
            Normalized system information
        """
        result = {}
        
        # Extract OS information
        os_info = system_info.get("OS", {})
        if os_info:
            result["OSVersion"] = f"{os_info.get('Caption', 'Unknown')} {os_info.get('Version', '')}"
            result["OSBuild"] = os_info.get("BuildNumber", "Unknown")
            result["InstallDate"] = os_info.get("InstallDate", "Unknown")
            result["LastBootTime"] = os_info.get("LastBootUpTime", "Unknown")
            result["Uptime"] = os_info.get("UpTime", "Unknown")
        
        # Extract Computer information
        computer_info = system_info.get("Computer", {})
        if computer_info:
            result["ComputerName"] = computer_info.get("MachineName", computer_info.get("Name", "Unknown"))
            result["Manufacturer"] = computer_info.get("Manufacturer", "Unknown")
            result["Model"] = computer_info.get("Model", "Unknown")
            result["TotalPhysicalMemory"] = computer_info.get("TotalPhysicalMemory", "Unknown")
        
        # Extract Processor information
        processor_info = system_info.get("Processor", {})
        if processor_info:
            result["Processor"] = processor_info
            
        # Extract Disk information
        result["Disks"] = system_info.get("Disks", [])
        
        return result
    
    def _aggregate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Aggregate identical events to reduce redundancy.
        
        Args:
            events: List of raw event dictionaries
            
        Returns:
            List of aggregated events with occurrence counts and timestamps
        """
        # Group events by their key attributes
        event_groups = defaultdict(list)
        
        for event in events:
            # Create a key based on Source, EventID, and partial Message
            # Getting first 100 chars of message to allow for minor differences
            source = event.get("ProviderName", "")
            event_id = event.get("EventID", 0)
            message = event.get("Message", "")
            message_key = message[:100] if message else ""
            
            # Create a compound key for grouping
            group_key = f"{source}|{event_id}|{message_key}"
            
            # Add to the appropriate group
            event_groups[group_key].append(event)
        
        # Convert groups into aggregated events
        aggregated_events = []
        
        for group_key, group_events in event_groups.items():
            # Use the first event as the template
            template_event = group_events[0].copy()
            
            # Extract all timestamps
            timestamps = [e.get("TimeCreated", "") for e in group_events]
            
            # Store aggregation data
            template_event["OccurrenceCount"] = len(group_events)
            template_event["Timestamps"] = sorted(timestamps, reverse=True)
            
            # Keep only essential fields to reduce size
            aggregated_event = {
                "LogName": template_event.get("LogName", ""),
                "Level": template_event.get("Level", ""),
                "EventID": template_event.get("EventID", 0),
                "ProviderName": template_event.get("ProviderName", ""),
                "Message": template_event.get("Message", ""),
                "OccurrenceCount": template_event["OccurrenceCount"],
                "Timestamps": template_event["Timestamps"][:10],  # Limit to first 10 timestamps
                "AdditionalTimestamps": len(template_event["Timestamps"]) - 10 if len(template_event["Timestamps"]) > 10 else 0
            }
            
            aggregated_events.append(aggregated_event)
        
        # Sort by count (most frequent first) and then by most recent timestamp
        aggregated_events.sort(
            key=lambda e: (-e["OccurrenceCount"], e["Timestamps"][0] if e["Timestamps"] else ""), 
            reverse=False
        )
        
        return aggregated_events
    
    def _generate_event_summary(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate statistical summary of events.
        
        Args:
            log_data: Raw log data dictionary
            
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
        
        events_data = log_data.get("Events", {})
        
        # Count by log type
        for log_type, events in events_data.items():
            summary["ByLogType"][log_type] = len(events)
            summary["TotalEvents"] += len(events)
            
            # Count by level
            level_counts = defaultdict(int)
            source_counts = defaultdict(int)
            event_id_counts = defaultdict(int)
            
            for event in events:
                level = event.get("Level", "")
                if level:
                    level_counts[level] += 1
                
                source = event.get("ProviderName", "")
                if source:
                    source_counts[source] += 1
                
                event_id = event.get("EventID", "")
                if event_id:
                    event_id_counts[event_id] += 1
            
            # Update level counts
            for level, count in level_counts.items():
                level_name = self._normalize_level_name(level)
                if level_name in summary["ByLevel"]:
                    summary["ByLevel"][level_name] += count
        
            # Find top sources for this log type
            top_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            summary["TopSources"].extend([
                {"Source": source, "Count": count, "LogType": log_type}
                for source, count in top_sources if count > 1
            ])
            
            # Find top event IDs for this log type
            top_event_ids = sorted(event_id_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            summary["TopEventIDs"].extend([
                {"EventID": str(event_id), "Count": count, "LogType": log_type}
                for event_id, count in top_event_ids if count > 1
            ])
        
        # Resort the global top lists
        summary["TopSources"] = sorted(summary["TopSources"], key=lambda x: x["Count"], reverse=True)[:10]
        summary["TopEventIDs"] = sorted(summary["TopEventIDs"], key=lambda x: x["Count"], reverse=True)[:10]
        
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
            output.append(f"OS: {sys_info.get('OSVersion', 'Unknown')}")
            output.append(f"Computer: {sys_info.get('ComputerName', 'Unknown')}")
            output.append(f"Uptime: {sys_info.get('Uptime', 'Unknown')}")
            output.append(f"CPU: {sys_info.get('Processor', 'Unknown')}")
            output.append(f"Memory: {sys_info.get('TotalPhysicalMemory', 'Unknown')}")
            output.append("")
        
        # Add collection info
        coll_info = processed_data.get("CollectionInfo", {})
        if coll_info:
            output.append("## COLLECTION INFORMATION")
            output.append(f"Collection Time: {coll_info.get('CollectionTime', 'Unknown')}")
            time_range = coll_info.get('TimeRange', {})
            output.append(f"Time Range: {time_range.get('Start', 'Unknown')} to {time_range.get('End', 'Unknown')}")
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
            output.append("## SIGNIFICANT EVENTS")
            
            # Process events by log type and severity
            for log_type, events in aggregated_events.items():
                # First add critical and error events
                critical_errors = [e for e in events if e.get("Level") in ["1", "2", "Critical", "Error"]]
                if critical_errors:
                    output.append(f"\n### {log_type} Critical/Error Events:")
                    for event in critical_errors[:10]:  # Limit to 10 most important
                        self._format_event(event, output)
                
                # Then add warning events
                warnings = [e for e in events if e.get("Level") in ["3", "Warning"]]
                if warnings:
                    output.append(f"\n### {log_type} Warning Events:")
                    for event in warnings[:5]:  # Limit to 5 warnings
                        self._format_event(event, output)
                
                # Add a small selection of information events if there are errors/warnings
                if critical_errors or warnings:
                    info_events = [e for e in events if e.get("Level") in ["4", "5", "Information", "Verbose"]]
                    if info_events:
                        output.append(f"\n### {log_type} Information Events (selected):")
                        # Prioritize frequent information events
                        sorted_info = sorted(info_events, key=lambda x: x.get("OccurrenceCount", 0), reverse=True)
                        for event in sorted_info[:3]:  # Just a few info events
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
            ts_str = ", ".join(timestamps[:3])
            if len(timestamps) > 3 or additional > 0:
                more_count = len(timestamps) - 3 + additional
                ts_str += f" and {more_count} more occurrences"
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