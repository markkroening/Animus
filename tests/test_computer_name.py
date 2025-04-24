#!/usr/bin/env python3
"""
Test script to verify we're correctly capturing and displaying the computer name
"""

import json
import subprocess
import os
from animus_cli.log_processor import LogProcessor

def main():
    """Main function to test computer name collection"""
    print("Testing computer name collection")
    
    # Step 1: Run PowerShell script to collect logs
    print("1. Collecting logs with PowerShell...")
    script_path = os.path.join('powershell', 'collect_logs.ps1')
    output_path = 'test_logs.json'
    
    try:
        subprocess.run([
            'powershell',
            '-ExecutionPolicy', 'Bypass',
            '-File', script_path,
            '-OutputFile', output_path,
            '-HoursBack', '24',
            '-MaxEvents', '100' 
        ], check=True)
        
        print(f"Logs collected to {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error collecting logs: {e}")
        return 1
    
    # Step 2: Process the logs with our processor
    print("\n2. Processing logs with LogProcessor...")
    try:
        with open(output_path, 'r', encoding='utf-8-sig') as f:
            try:
                log_data = json.load(f)
            except json.JSONDecodeError:
                f.seek(0)
                log_data = json.load(f)
    except Exception as e:
        print(f"Error loading log file: {e}")
        return 1
    
    # Process the logs
    processor = LogProcessor(verbose=True)
    processed_data = processor.process_logs(log_data)
    
    # Step 3: Verify system info contains computer name
    print("\n3. Verifying system info contains computer name:")
    sys_info = processed_data.get("SystemInfo", {})
    computer_name = sys_info.get("ComputerName", "Not found")
    
    print(f"Computer Name: {computer_name}")
    
    # Check other system info fields
    print("\nOther System Info:")
    for key, value in sys_info.items():
        if key != "Processor" and key != "Disks":  # Skip complex objects
            print(f"- {key}: {value}")
    
    # Step 4: Format the logs for LLM
    print("\n4. Formatting logs for LLM...")
    formatted_text = processor.format_for_llm(processed_data)
    
    # Extract and show only the system information section
    system_section = ""
    in_system_section = False
    for line in formatted_text.split('\n'):
        if line.startswith('## SYSTEM INFORMATION'):
            in_system_section = True
            system_section += line + '\n'
        elif in_system_section:
            if line.startswith('##'):
                in_system_section = False
            else:
                system_section += line + '\n'
    
    print("\nSystem Information Section in LLM Format:")
    print("-" * 60)
    print(system_section)
    print("-" * 60)
    
    # Cleanup
    print("\nCleaning up test files...")
    try:
        os.remove(output_path)
        print(f"Removed {output_path}")
    except:
        print(f"Could not remove {output_path}")
    
    print("\nTest completed.")
    return 0

if __name__ == "__main__":
    exit(main()) 