# Animus CLI

## Overview
Animus CLI is a local Windows Event Log analysis tool that uses natural language processing to help technicians quickly analyze and understand system events. This tool runs entirely on the local Windows machine with no cloud dependencies.

## Built with Llama
This application uses Llama 3.2, a large language model developed by Meta. For more information about Llama, visit [Meta AI's Llama page](https://ai.meta.com/llama/).

## Features

- **Log Collection**: Automatically gathers Windows Event Logs (System, Application, Security) and system metadata.
- **System Information**: Collects detailed information about the OS, hardware, and system configuration.
- **Local Analysis**: Processes logs locally with no data leaving the machine.
- **AI-Powered Insights**: Uses a local Llama 3.2 3B model to analyze logs and answer questions.
- **Natural Language Interface**: Ask questions about your system in plain English.
- **Interactive CLI**: User-friendly command-line interface with command history and colorful output.
- **Automatic Log Collection**: Automatically collects fresh logs on startup if existing logs are outdated.
- **Structured Data**: Parses logs into structured data objects for easy querying and analysis.
- **Smart Queries**: Built-in support for querying logs by event ID, error type, or keywords.
- **Conversational Q&A Mode**: Dedicated interactive mode for asking multiple questions about your logs.
- **Offline Operation**: Performs all analysis locally without internet connectivity.

## Requirements

- Windows 10 or 11
- PowerShell 5.1 or higher
- Python 3.9+
- 6GB+ RAM (8GB recommended for optimal LLM performance)
- 2GB of free disk space for the model file

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

3. Download the Llama model file:
   - Download the [llama-3.2-3b-instruct.Q4_0.gguf](https://huggingface.co/TheBloke/Llama-3.2-3B-Instruct-GGUF/resolve/main/llama-3.2-3b-instruct.Q4_0.gguf) model (about 2GB)
   - Place it in the `models` directory

   > **Note**: The AI features are optional. If the model file is not found, Animus will fall back to basic analysis capabilities.

4. Run the tool:
   ```
   python animus_cli.py
   ```
   
   Or for Windows users, simply run:
   ```
   run_animus.bat
   ```

## AI-Powered Analysis

Animus CLI uses the Llama 3.2 3B language model to provide intelligent analysis of your Windows Event Logs. The model runs entirely on your local machine with no data sent to the cloud.

### Model Setup

The application will automatically look for the Llama model file in the following locations:
- `./models/llama-3.2-3b-instruct.Q4_0.gguf` (recommended)
- `./llama-3.2-3b-instruct.Q4_0.gguf`
- Other standard locations (see `models/README.md` for details)

You can also specify a custom model path with the `--model-path` option.

### How It Works

When you ask a question, Animus:
1. Loads your Windows Event Logs 
2. Intelligently filters relevant events based on your query
3. Creates a prompt containing system info and filtered events
4. Passes this prompt to the local Llama model
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
run_standalone_qa.bat
```

This will:
1. Collect Windows event logs if they don't already exist
2. Initialize the LLM for AI-powered analysis
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
- Make sure the Llama model file is properly downloaded and placed in the `models` directory
- Check that all required Python packages are installed
- Try running the standalone script to bypass any issues with the CLI

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
usage: animus_cli.py [-h] [--output OUTPUT] [--hours HOURS] [--max-events MAX_EVENTS]
                     [--collect] [--no-auto-collect] [--no-security] [--interactive]
                     [--qa] [--query QUERY] [--model-path MODEL_PATH]
                     [--context-size CONTEXT_SIZE] [--verbose]

Animus - Windows Event Log Analysis CLI

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
  --model-path MODEL_PATH
                        Path to Llama model file (llama-3.2-3b-instruct.Q4_0.gguf)
  --context-size CONTEXT_SIZE
                        Token context size for the LLM (default: 2048)
  --verbose, -v         Enable verbose output
```

## LLM Performance Considerations

The Llama 3.2 3B model requires significant system resources:

- **Memory Usage**: Approximately 4-6GB of RAM while running
- **Disk Space**: ~2GB for the model file
- **Processing Time**: Responses may take 5-30 seconds depending on your CPU

For better performance:
- Use a system with 8GB+ RAM
- Run on a machine with a modern multi-core CPU
- Consider reducing the context size with `--context-size 1024` on lower-end systems
- If needed, you can use smaller model variants (see `models/README.md`)

## Development

This project is in active development. The current milestone focuses on the AI-powered analysis capabilities, with future updates planned for enhanced reporting and deeper analysis.

## License

[MIT License](LICENSE)

## Quick Start Guide

### Windows:
1. Make sure you have [Python 3.9+](https://www.python.org/downloads/) installed
2. Download and install [Ollama](https://ollama.ai/download) for Windows
3. Run the `run_animus_with_ollama.bat` script
   - This will use Ollama to download the Llama 3.2 3B model
   - The script will find and copy the model file to the correct location
   - If you encounter issues, see the [installation guide](INSTALL_WITH_OLLAMA.md)

### Linux/Mac:
1. Make sure you have Python 3.9+ installed
2. Make the script executable and run it:
   ```bash
   chmod +x run_animus_with_ollama.sh
   ./run_animus_with_ollama.sh
   ```
   - The script will install Ollama if needed and download the model automatically
   - If you encounter issues, see the [installation guide](INSTALL_WITH_OLLAMA.md)
