#!/usr/bin/env python3
"""
Test script for the Animus log processor.

This script demonstrates how the log processor improves log efficiency for LLM consumption.
"""

import os
import json
import sys
from animus_cli.log_processor import process_log_file

def main():
    """Main entry point for the test script"""
    
    # Check that the log file exists
    log_file = 'animus_logs.json'
    if not os.path.exists(log_file):
        print(f"Error: Log file {log_file} not found.")
        print("Please run the log collector first to generate logs.")
        return 1
    
    # Process the log file
    print(f"Processing log file: {log_file}")
    try:
        # Process the logs
        formatted_text, processed_data = process_log_file(
            log_file, 
            output_file='animus_processed_logs.json',
            verbose=True
        )
        
        # Get original file size
        original_size = os.path.getsize(log_file)
        processed_size = os.path.getsize('animus_processed_logs.json')
        text_size = len(formatted_text)
        
        print("\n--- RESULTS ---")
        print(f"Original JSON size: {original_size:,} bytes")
        print(f"Processed JSON size: {processed_size:,} bytes")
        print(f"Formatted text size: {text_size:,} characters")
        print(f"Compression ratio: {processed_size/original_size:.2%}")
        
        # Show a sample of the formatted text
        print("\n--- FORMATTED TEXT SAMPLE (first 1000 chars) ---")
        print("-" * 80)
        print(formatted_text[:1000])
        print("-" * 80)
        
        # Show event count comparisons
        event_summary = processed_data.get('EventSummary', {})
        aggregated_events = processed_data.get('AggregatedEvents', {})
        
        if event_summary and aggregated_events:
            print("\n--- EVENT COUNT COMPARISON ---")
            
            # Get total event count from summary
            total_raw_events = event_summary.get('TotalEvents', 0)
            
            # Count aggregated events
            total_aggregated = 0
            for log_type, events in aggregated_events.items():
                total_aggregated += len(events)
            
            if total_raw_events > 0:
                print(f"Raw event count: {total_raw_events:,}")
                print(f"Aggregated event count: {total_aggregated:,}")
                print(f"Aggregation ratio: {total_aggregated/total_raw_events:.2%}")
                print(f"Event reduction: {(total_raw_events - total_aggregated):,} events")
        
        print("\nProcessed log data saved to: animus_processed_logs.json")
        print("This processed format is now ready for LLM consumption.")
        
        return 0
        
    except Exception as e:
        print(f"Error processing logs: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 