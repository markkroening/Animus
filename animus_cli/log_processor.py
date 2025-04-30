import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple

"""
Log Processor for Animus CLI (Refactored)

This module takes raw log data (loaded from JSON produced by the updated 
collect_logs.ps1 script), processes it for efficiency by aggregating 
similar events, generating statistics, and formats it for LLM consumption.

Changes from previous version:
- Removed dependency on data_models (LogCollection, EventLogEntry, SystemInfo).
- Functions now directly process dictionaries/lists loaded from JSON.
- Simplified aggregation: focuses on grouping by Source/ID/Level. Dynamic message parsing removed for simplicity (can be added back if needed).
- Assumes input JSON structure from the refactored collect_logs.ps1 
 (e.g., has 'Events' key with a flat list of all event dicts).
"""

class LogProcessor:
    """Processes raw log dictionaries to make them more efficient for LLM consumption."""

    def __init__(self, verbose: bool = False):
        """
        Initialize the log processor.

        Args:
            verbose: Whether to show verbose output during processing.
        """
        self.verbose = verbose
        if self.verbose:
            print("[INFO] LogProcessor initialized.")

    def process_logs(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process raw log data dictionary to make it more LLM-friendly.

        Args:
            log_data: Dictionary loaded directly from the collector's JSON output.

        Returns:
            Processed log data dictionary optimized for LLM consumption.
        """
        if not log_data or not isinstance(log_data, dict):
            raise ValueError("Input log_data must be a non-empty dictionary.")

        if self.verbose:
            print(f"[INFO] Processing log data collected at: {log_data.get('CollectionTime', 'Unknown')}")

        # Extract raw events list
        # Assumes refactored PowerShell script outputs a flat list under 'Events' key
        raw_events: List[Dict[str, Any]] = log_data.get("Events", [])

        # Create a new structure for processed logs
        processed_data = {
            "CollectionInfo": {
                "CollectionTime": log_data.get("CollectionTime"),
                "TimeRange": log_data.get("TimeRange"),
            },
            # Directly use the SystemInfo dict from the input
            "SystemInfo": log_data.get("SystemInfo", {}),
            # Directly use the NetworkInfo dict (consider removing if not needed)
            "NetworkInfo": log_data.get("NetworkInfo", {}),
            # Generate summary based on raw events
            "EventSummary": self._generate_event_summary(raw_events),
            # Aggregate the raw events
            "AggregatedEvents": self._aggregate_events(raw_events),
        }

        if self.verbose:
            total_raw = len(raw_events)
            total_agg = len(processed_data.get("AggregatedEvents", []))
            print(f"[INFO] Aggregated {total_raw} raw events into {total_agg} distinct event groups.")

        return processed_data

    def _aggregate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Aggregate events based on key fields to reduce redundancy.
        Groups by LogName, ProviderName, EventID, and Level.

        Args:
            events: List of raw event dictionaries.

        Returns:
            List of aggregated event dictionaries with counts and timestamps.
        """
        event_groups = defaultdict(list)

        for event in events:
            # Create a grouping key
            # Using get() with default values for safety
            log_name = event.get("LogName", "Unknown")
            provider = event.get("ProviderName", "Unknown")
            event_id = event.get("EventID", 0)
            level = self._normalize_level_name(event.get("Level", "Information")) # Normalize level name here

            group_key = f"{log_name}|{provider}|{event_id}|{level}"
            event_groups[group_key].append(event)

        aggregated_events = []
        for group_key, group_events in event_groups.items():
            if not group_events:
                continue

            template_event = group_events[0] # Use first event as representative

            # Extract and sort timestamps (expecting ISO 8601 strings)
            timestamps = []
            for e in group_events:
                ts_str = e.get("TimeCreated")
                if ts_str is not None:  # Explicit check for None
                    try:
                        # Attempt to parse ISO 8601 string
                        # Note: Python < 3.11 might struggle with high-precision fractions or 'Z'
                        # Let's try removing 'Z' and handling potential microseconds manually
                        ts_str = ts_str.replace('Z', '+00:00')
                        # Handle potential high precision microseconds
                        if '.' in ts_str:
                             ts_base, ts_frac = ts_str.split('.', 1)
                             ts_frac = ts_frac.split('+')[0] # Get fraction part before timezone
                             ts_frac = (ts_frac + '000000')[:6] # Pad/truncate to 6 digits
                             ts_str = f"{ts_base}.{ts_frac}+00:00"

                        timestamps.append(datetime.fromisoformat(ts_str))
                    except (ValueError, AttributeError) as e:
                         # Handle cases where timestamp format might be unexpected
                         if self.verbose:
                             print(f"[WARN] Could not parse timestamp: {ts_str} for EventID {template_event.get('EventID')}. Error: {e}")
                         # Optionally add a placeholder or skip
            
            timestamps.sort() # Sort ascending (oldest first)

            # Keep only essential fields + aggregation info
            aggregated_event = {
                "LogName": template_event.get("LogName"),
                "Level": self._normalize_level_name(template_event.get("Level")), # Ensure normalized level
                "EventID": template_event.get("EventID"),
                "ProviderName": template_event.get("ProviderName"),
                # Use the message from the *first* event in the group as representative
                "Message": template_event.get("Message", "No message"),
                "OccurrenceCount": len(group_events),
                # Convert datetimes back to ISO strings for JSON
                "FirstTimestamp": timestamps[0].isoformat() if timestamps else None,
                "LastTimestamp": timestamps[-1].isoformat() if timestamps else None,
                # Show last 3 timestamps as examples (most recent)
                "ExampleTimestamps": [ts.isoformat() for ts in timestamps[-3:]] if timestamps else [],
                # DynamicParts removed for simplicity in this refactor
            }
            aggregated_events.append(aggregated_event)

        # Sort aggregated events: Most frequent first, then by most recent occurrence
        aggregated_events.sort(key=lambda e: (-e["OccurrenceCount"], e["LastTimestamp"] or ""), reverse=True)

        return aggregated_events

    def _generate_event_summary(self, all_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate statistical summary of events.

        Args:
            all_events: List of raw event dictionaries.

        Returns:
            Dictionary with statistical summaries.
        """
        summary = {
            "TotalEvents": len(all_events),
            "ByLogType": defaultdict(int),
            "ByLevel": defaultdict(int),
            "TopSources": [],
            "TopEventIDs": []
        }
        source_counts = defaultdict(int)
        event_id_counts = defaultdict(int)
        source_log_map = {} # Track which log a source first appeared in
        event_id_log_map = {} # Track which log an EventID first appeared in

        for event in all_events:
            log_name = event.get("LogName", "Unknown")
            level_name = self._normalize_level_name(event.get("Level", "Information"))
            provider = event.get("ProviderName", "Unknown")
            event_id = event.get("EventID", 0)

            summary["ByLogType"][log_name] += 1
            summary["ByLevel"][level_name] += 1

            if provider != "Unknown":
                source_counts[provider] += 1
                if provider not in source_log_map:
                    source_log_map[provider] = log_name

            if event_id != 0:
                event_id_str = str(event_id)
                event_id_counts[event_id_str] += 1
                if event_id_str not in event_id_log_map:
                   event_id_log_map[event_id_str] = log_name

        # Get top 5 sources (only those appearing more than once)
        top_sources = sorted(source_counts.items(), key=lambda item: item[1], reverse=True)
        summary["TopSources"] = [
            {"Source": source, "Count": count, "LogType": source_log_map.get(source, "Unknown")}
            for source, count in top_sources if count > 1
        ][:5]

        # Get top 5 event IDs (only those appearing more than once)
        top_event_ids = sorted(event_id_counts.items(), key=lambda item: item[1], reverse=True)
        summary["TopEventIDs"] = [
             {"EventID": event_id, "Count": count, "LogType": event_id_log_map.get(event_id, "Unknown")}
            for event_id, count in top_event_ids if count > 1
        ][:5]

        # Convert defaultdicts back to regular dicts for cleaner output
        summary["ByLogType"] = dict(summary["ByLogType"])
        summary["ByLevel"] = dict(summary["ByLevel"])


        return summary

    def _normalize_level_name(self, level: Optional[str]) -> str:
        """
        Normalize level names (strings) to standard capitalized values.

        Args:
            level: Raw level string (e.g., "Error", "Warning", "information").

        Returns:
            Normalized level name ("Critical", "Error", "Warning", "Information", "Verbose").
        """
        level_str = str(level).lower().strip() if level else "information" # Default to information if None/empty

        if level_str == "critical": # Assuming PowerShell uses 'Critical'
            return "Critical"
        elif level_str == "error":
            return "Error"
        elif level_str == "warning":
            return "Warning"
        elif level_str == "information":
            return "Information"
        elif level_str == "verbose":
            return "Verbose"
        else:
            # Attempt to map potential numeric levels if Get-WinEvent used those? (Less likely with LevelDisplayName)
            if level_str == "1": return "Critical"
            if level_str == "2": return "Error"
            if level_str == "3": return "Warning"
            if level_str == "4": return "Information"
            if level_str == "5": return "Verbose"
            return "Information" # Default if unrecognized

    def format_for_llm(self, processed_data: Dict[str, Any]) -> str:
        """
        Format processed data into a concise text string for LLM consumption.

        Args:
            processed_data: Processed log data dictionary from process_logs.

        Returns:
            Formatted string ready for LLM prompt context.
        """
        output_lines = []

        # Add system information
        sys_info = processed_data.get("SystemInfo", {})
        if sys_info:
            output_lines.append("## SYSTEM INFORMATION ##")
            # Use .get() for safe access
            output_lines.append(f"- OS: {sys_info.get('OSVersion', 'N/A')} {sys_info.get('OSDisplayVersion', '')} (Build {sys_info.get('OSBuildNumber', 'N/A')})")
            output_lines.append(f"- Computer: {sys_info.get('ComputerName', 'N/A')} ({sys_info.get('CsManufacturer', 'N/A')} {sys_info.get('CsModel', 'N/A')})")
            output_lines.append(f"- Memory: {sys_info.get('TotalPhysicalMemory', 'N/A')}")
            output_lines.append(f"- Install Date: {sys_info.get('InstallDate', 'N/A')}")
            output_lines.append(f"- Last Boot: {sys_info.get('LastBootTime', 'N/A')}")
            output_lines.append(f"- Uptime Hours: {sys_info.get('UptimeHours', 'N/A')}")
            output_lines.append("")

        # Add network information (Optional - maybe omit for LLM context?)
        net_info = processed_data.get("NetworkInfo", {})
        if net_info and net_info.get("Adapters"):
            output_lines.append("## ACTIVE NETWORK ADAPTERS ##")
            for adapter in net_info["Adapters"][:2]: # Limit to first 2 adapters for brevity
                output_lines.append(f"- Name: {adapter.get('Name', 'N/A')} ({adapter.get('Description', 'N/A')})")
                output_lines.append(f"  Status: {adapter.get('Status', 'N/A')}, MAC: {adapter.get('MACAddress', 'N/A')}")
                output_lines.append(f"  IPv4: {adapter.get('IPv4Address', 'N/A')}, Gateway: {adapter.get('Gateway', 'N/A')}")
                if adapter.get('DNSServers'):
                    output_lines.append(f"  DNS: {', '.join(adapter['DNSServers'])}")
            if len(net_info["Adapters"]) > 2:
                 output_lines.append("  (Additional adapters omitted for brevity)")
            output_lines.append("")

        # Add collection info
        coll_info = processed_data.get("CollectionInfo", {})
        if coll_info and coll_info.get("TimeRange"):
            output_lines.append("## COLLECTION INFO ##")
            tr = coll_info.get("TimeRange", {})
            output_lines.append(f"- Logs Collected At: {coll_info.get('CollectionTime', 'N/A')}")
            output_lines.append(f"- Covering Period: {tr.get('StartTime', 'N/A')} to {tr.get('EndTime', 'N/A')}")
            output_lines.append("")

        # Add event summary statistics
        summary = processed_data.get("EventSummary", {})
        if summary:
            output_lines.append("## EVENT SUMMARY ##")
            output_lines.append(f"- Total Events Found: {summary.get('TotalEvents', 0)}")
            levels = summary.get("ByLevel", {})
            level_summary = ", ".join(f"{lvl}: {cnt}" for lvl, cnt in levels.items() if cnt > 0)
            output_lines.append(f"- Counts by Level: {level_summary if level_summary else 'None'}")

            top_src = summary.get("TopSources", [])
            if top_src:
                 output_lines.append("- Top Sources:")
                 for item in top_src:
                      output_lines.append(f"  - {item['Source']} ({item['LogType']}): {item['Count']} times")

            top_ids = summary.get("TopEventIDs", [])
            if top_ids:
                 output_lines.append("- Top Event IDs:")
                 for item in top_ids:
                      output_lines.append(f"  - ID {item['EventID']} ({item['LogType']}): {item['Count']} times")
            output_lines.append("")

        # Add aggregated events
        aggregated_events = processed_data.get("AggregatedEvents", [])
        if aggregated_events:
            output_lines.append("## AGGREGATED EVENT DETAILS (Sorted by Frequency) ##")
            # Limit number of events sent to LLM? Maybe top 20-30?
            # Or filter by severity? e.g. Critical, Error, Warning only?
            # For now, include all aggregated events. Add filtering logic here if needed.
            # Example: events_to_format = [e for e in aggregated_events if e['Level'] in ['Critical', 'Error', 'Warning']][:30]
            events_to_format = aggregated_events # Include all for now

            if not events_to_format:
                 output_lines.append("No significant events found matching current filters.")
            else:
                for event in events_to_format:
                    self._format_event(event, output_lines)
            
            if len(aggregated_events) > len(events_to_format):
                 output_lines.append(f"... ({len(aggregated_events) - len(events_to_format)} additional aggregated event groups omitted)")


        return "\n".join(output_lines)

    def _format_event(self, event: Dict[str, Any], output_lines: List[str]):
        """
        Format a single aggregated event dictionary for concise text output.

        Args:
            event: Aggregated event dictionary.
            output_lines: List to append formatted lines to.
        """
        event_id = event.get("EventID", "?")
        source = event.get("ProviderName", "Unknown")
        level = event.get("Level", "Information") # Already normalized in _aggregate_events
        message = event.get("Message", "No message")  # Default to "No message" if None
        count = event.get("OccurrenceCount", 1)
        first_ts = event.get("FirstTimestamp")
        last_ts = event.get("LastTimestamp")
        example_ts_list = event.get("ExampleTimestamps", [])

        # Format message: replace newlines, trim whitespace
        if message is not None:  # Only process if message is not None
            message = message.replace("\n", " ").replace("\r", "").strip()
        else:
            message = "No message provided"  # Fallback if message is None

        # Create output string
        header = f"[{level}] EventID: {event_id} | Source: {source} | Count: {count}"
        output_lines.append(header)
        output_lines.append(f"  Msg: {message}")
        if count > 1 and first_ts and last_ts:
             output_lines.append(f"  First: {first_ts} | Last: {last_ts}")
        elif last_ts: # Handle single occurrence case
             output_lines.append(f"  Time: {last_ts}")

        # Optionally show example timestamps if count > 1 and different from first/last
        # if count > 1 and example_ts_list and len(example_ts_list) > 1:
        #    output_lines.append(f"  Recent Times: {', '.join(example_ts_list)}")

        output_lines.append("") # Blank line between entries


def process_log_file(input_file: str, output_file: Optional[str] = None, verbose: bool = False) -> Tuple[str, Dict[str, Any]]:
    """
    Loads a JSON log file, processes it, formats it for LLM, and optionally saves outputs.

    Args:
        input_file: Path to the input JSON log file from collect_logs.ps1.
        output_file: Optional path to save the processed data dictionary as JSON.
                     A corresponding _formatted.txt file will also be saved.
        verbose: Whether to show verbose output.

    Returns:
        Tuple of (formatted text string for LLM, processed data dictionary).
    """
    if verbose:
        print(f"[INFO] Loading log file: {input_file}")
    try:
        # Try UTF-8 first, then UTF-8-SIG (handles PowerShell BOM)
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
        except UnicodeDecodeError:
            if verbose:
                 print("[INFO] UTF-8 decode failed, trying utf-8-sig...")
            with open(input_file, 'r', encoding='utf-8-sig') as f:
                log_data = json.load(f)
        except json.JSONDecodeError as e:
             raise RuntimeError(f"Failed to decode JSON from log file: {e}")

    except FileNotFoundError:
         raise FileNotFoundError(f"Input log file not found: {input_file}")
    except Exception as e:
        raise RuntimeError(f"Failed to load log file '{input_file}': {e}")

    # Process the loaded data
    processor = LogProcessor(verbose=verbose)
    processed_data = processor.process_logs(log_data)

    # Format for LLM
    if verbose:
        print("[INFO] Formatting processed data for LLM...")
    formatted_text = processor.format_for_llm(processed_data)

    # Save processed data and formatted text if output file requested
    if output_file:
        if verbose:
             print(f"[INFO] Saving processed outputs (JSON and TXT) to base path: {output_file}")
        try:
            # Ensure output directory exists
            output_dir = os.path.dirname(output_file)
            if output_dir:
                 os.makedirs(output_dir, exist_ok=True)

            # Save processed data dictionary as JSON
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, indent=2, ensure_ascii=False)
            if verbose:
                print(f"[SUCCESS] Saved processed JSON data to: {output_file}")

            # Save formatted text to a corresponding .txt file
            formatted_output_path = os.path.splitext(output_file)[0] + '_formatted.txt'
            with open(formatted_output_path, 'w', encoding='utf-8') as f:
                f.write(formatted_text)
            if verbose:
                print(f"[SUCCESS] Saved formatted text to: {formatted_output_path}")

        except Exception as e:
            # Log warning but don't fail the whole process if saving fails
            print(f"[WARN] Failed to save output file(s) based on '{output_file}': {e}")

    return formatted_text, processed_data


# --- Main execution block for testing ---
if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) < 2:
        print(f"Usage: python {os.path.basename(__file__)} <input_json_file> [output_json_file]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    try:
        print(f"Processing {input_path}...")
        # Set verbose=True for detailed output during processing
        formatted_llm_text, final_processed_data = process_log_file(input_path, output_path, verbose=True)
        print("\n" + "="*80)
        print("Processing Complete.")
        print(f"Formatted text length for LLM: {len(formatted_llm_text)} characters")
        if output_path:
             print(f"Processed JSON saved to: {output_path}")
             print(f"Formatted text saved to: {os.path.splitext(output_path)[0] + '_formatted.txt'}")
        print("="*80)
        print("\nFormatted Text Sample (first 1500 chars):")
        print("-" * 80)
        print(formatted_llm_text[:1500])
        if len(formatted_llm_text) > 1500:
            print("...")
        print("-" * 80)

    except FileNotFoundError as e:
         print(f"\n[ERROR] Input file not found: {e}")
         sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] An error occurred during processing: {e}")
        import traceback
        traceback.print_exc() # Print full traceback for debugging
        sys.exit(1)