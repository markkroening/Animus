# Animus CLI

## Overview
Animus CLI is a local Windows Event Log analysis tool that uses natural language processing to help technicians quickly analyze and understand system events. This tool runs on a local Windows machine and uses Google's Gemini API for intelligent analysis.

## Powered by Google Gemini
This application uses Google's Gemini API, a state-of-the-art language model for AI-assisted analysis. For more information about Gemini, visit [Google's Gemini page](https://ai.google.dev/).

## Features

- **Log Collection**: Automatically gathers Windows Event Logs (System, Application, Security) and system metadata.
- **System Information**: Collects detailed information about the OS, hardware, and system configuration.
- **AI-Powered Insights**: Uses Google Gemini to analyze logs and answer questions.
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
- Internet connection for Gemini API access
- Google Gemini API key

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

3. Set up your Google Gemini API key:
   - Get your API key from [Google AI Studio](https://ai.google.dev/)
   - Create a `.env` file in the project root with your API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
   - Alternatively, you can set it as an environment variable

4. Run the tool:
   ```
   python animus_cli.py
   ```
   
   Or for Windows users, simply run:
   ```
   run_animus.bat
   ```

## AI-Powered Analysis

Animus CLI uses Google's Gemini API to provide intelligent analysis of your Windows Event Logs.

### How It Works

When you ask a question, Animus:
1. Loads your Windows Event Logs 
2. Intelligently filters relevant events based on your query
3. Creates a prompt containing system info and filtered events
4. Sends this prompt to the Google Gemini API
5. Returns the AI-generated response with insights about your logs

### Example Questions

With the AI capabilities, you can ask natural questions like:
- "Why did my system crash yesterday?"
- "Are there any security concerns I should know about?"
- "What's causing the application errors I'm seeing?"
- "Has anyone tried to access my system unauthorized?"
- "Why is my system running slow?"
- "Explain the USB device errors in simple terms"

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

The Animus CLI provides an interactive question-and-answer mode that allows you to ask natural language questions about your Windows event logs and system information.

### Using the Interactive Q&A Mode

To start the interactive Q&A mode, run the standalone script:

```
run_animus.bat
```

This will:
1. Collect Windows event logs if they don't already exist
2. Initialize the connection to Gemini for AI-powered analysis
3. Start an interactive session where you can ask questions

### Example Questions

Once in Q&A mode, you can ask questions like:
- "What errors have occurred recently?"
- "Show me system information"
- "Did the system restart unexpectedly?"
- "Are there any security concerns?"
- "What happened at 2:00 PM yesterday?"

To exit Q&A mode, type `exit`, `quit`, or press Ctrl+C.

### Troubleshooting Interactive Mode

If you experience issues with the interactive mode:
- Make sure your Gemini API key is correctly set in the `.env` file or as an environment variable
- Check that all required Python packages are installed
- Ensure you have an active internet connection
- Try running with the `--verbose` flag for more detailed error messages

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

## Command Line Arguments

The Animus CLI supports the following command-line arguments:

```
options:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Path to write/read the log JSON file (default: ./animus_logs.json)
  --hours HOURS, -H HOURS
                        Hours of logs to collect (default: 48)
  --max-events MAX_EVENTS, -m MAX_EVENTS
                        Maximum events per log type to collect (default: 500)
  --collect, -c         Force collection of logs even if recent logs exist
  --no-auto-collect     Disable automatic log collection
  --no-security         Skip collection of security logs
  --interactive, -i     Start in interactive mode
  --qa, -Q              Start directly in Q&A mode
  --query QUERY, -q QUERY
                        Process a single query and exit
  --verbose, -v         Enable verbose output
  --model-name MODEL_NAME
                        Name of the Gemini model to use (default: gemini-1.5-flash-latest)
```

## Development

This project is in active development. The current milestone focuses on the AI-powered analysis capabilities, with future updates planned for enhanced reporting and deeper analysis.

## License

[MIT License](LICENSE)
