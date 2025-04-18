# Animus CLI

## Overview
Animus CLI is a local Windows Event Log analysis tool that uses natural language processing to help technicians quickly analyze and understand system events. This tool runs entirely on the local Windows machine with no cloud dependencies.

## Features

- **Log Collection**: Automatically gathers Windows Event Logs (System, Application, Security) and system metadata.
- **System Information**: Collects detailed information about the OS, hardware, and system configuration.
- **Local Analysis**: Processes logs locally with no data leaving the machine.
- **Natural Language Interface**: Ask questions about your system in plain English.
- **Interactive CLI**: User-friendly command-line interface with command history and colorful output.
- **Automatic Log Collection**: Automatically collects fresh logs on startup if existing logs are outdated.
- **Structured Data**: Parses logs into structured data objects for easy querying and analysis.
- **Smart Queries**: Built-in support for querying logs by event ID, error type, or keywords.
- **Conversational Q&A Mode**: Dedicated interactive mode for asking multiple questions about your logs.

## Requirements

- Windows 10 or 11
- PowerShell 5.1 or higher
- Python 3.9+

## Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd animus
   ```

2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Interactive CLI Mode

The easiest way to use Animus is through its interactive CLI:

```
python -m animus_cli.main
```

This launches an interactive shell where you can run commands such as:

- `collect` - Collect Windows Event Logs
- `status` - Show information about loaded logs
- `qa` - Enter interactive Q&A mode for multiple questions
- `help` - Display available commands
- `exit` or `quit` - Exit the CLI

### Interactive Q&A Mode

The Q&A mode provides a dedicated environment for asking multiple questions about your logs:

```
python -m animus_cli.main --qa
```

Or from the interactive CLI:
```
animus> qa
```

In Q&A mode:
- You'll get a special prompt for entering questions
- The interface is optimized for back-and-forth conversation
- Type `exit`, `quit`, or `back` to return to the main CLI
- The system maintains conversation context for more natural interactions

Example Q&A session:
```
Q: What errors have occurred recently?
A: Found 3 error/critical events:

1. [2023-05-15 14:23:45] Application Error (ID: 1000)
   The program crashed because of a null reference exception...

...and 2 more

Q: Tell me about my system
A: System Information:

OS: Windows 11 Pro 22H2 (Build 22621)
Architecture: 64-bit
Manufacturer: Dell Inc.
...
```

### Automatic Log Collection

By default, the CLI will automatically collect fresh logs in these scenarios:
- When no log file exists
- When the existing log file is older than 24 hours
- When the existing log file is invalid or corrupted

You can control this behavior with these command-line options:
- `--no-auto-collect` - Disable automatic log collection on startup
- `--auto-collect-age HOURS` - Set the age threshold for auto-collection (default: 24 hours)

### Collecting Logs

To manually collect Windows Event Logs:

```
python -m animus_cli.main --collect-logs
```

Or from the interactive CLI:
```
animus> collect
```

To force immediate collection of fresh logs, regardless of when logs were last collected:

```
python -m animus_cli.main --collect-now
```

Or from the interactive CLI:
```
animus> collect --force
```

This will gather logs from the past 48 hours and save them to `animus_logs.json` in the project root.

#### Options:

- `--output/-o <path>` - Specify custom output file location
- `--hours <number>` - Collect logs from the past N hours (default: 48)
- `--max-events <number>` - Maximum number of events per log type (default: 500)
- `--no-security` - Exclude Security logs (which can be large)

Example:
```
python -m animus_cli.main --collect-logs --hours 24 --max-events 1000 --output my_logs.json
```

In interactive mode:
```
animus> collect 24 1000 --no-security
```

### Querying Logs

Animus provides several ways to query your logs. In the interactive CLI or Q&A mode, you can:

1. **View log status**:
   ```
   animus> status
   ```
   Shows an overview of the loaded logs, including counts, time range, and recent errors.

2. **Search for specific event IDs**:
   ```
   animus> event id: 1234
   ```
   or
   ```
   animus> find event id 1234
   ```

3. **Search for error events**:
   ```
   animus> errors
   ```
   or
   ```
   animus> show errors
   ```

4. **Get system information**:
   ```
   animus> system information
   ```
   or
   ```
   animus> computer
   ```
   or
   ```
   animus> hardware
   ```

5. **Search by keywords**:
   ```
   animus> service failure
   ```
   (searches for "service failure" in event messages)

6. **Ask about recent events**:
   ```
   animus> show recent events
   ```

7. **Get statistics and counts**:
   ```
   animus> how many events are there?
   ```
   or
   ```
   animus> event summary
   ```

### Command-line Arguments

```
usage: main.py [-h] [--collect-logs] [--collect-now] [--output OUTPUT] [--hours HOURS]
               [--max-events MAX_EVENTS] [--no-security] [--analyze]
               [--qa] [--query QUERY] [--interactive] [--version] 
               [--no-auto-collect] [--auto-collect-age HOURS]

Animus CLI - Windows Event Log Analyzer

options:
  -h, --help            show this help message and exit
  --collect-logs        Collect Windows Event Logs
  --collect-now         Force immediate log collection regardless of existing log age
  --output OUTPUT, -o OUTPUT
                        Output file path for logs
  --hours HOURS         Hours of logs to collect (default: 48)
  --max-events MAX_EVENTS
                        Maximum events per log type (default: 500)
  --no-security         Exclude Security logs
  --analyze, -a         Start analysis mode (interactive Q&A)
  --qa                  Start interactive Q&A mode
  --query QUERY, -q QUERY
                        Single query mode (non-interactive)
  --interactive, -i     Start interactive CLI mode
  --version, -v         Show version information
  --no-auto-collect     Disable automatic log collection on startup
  --auto-collect-age HOURS
                        Auto-collect if logs are older than this many hours (default: 24)
```

## Development

This project is in active development. The current milestone focuses on the log collection and basic querying functionality, with advanced analysis capabilities coming in future updates.

## License

[MIT License](LICENSE)
