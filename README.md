# Animus CLI

Animus CLI is a powerful Windows Event Log analysis tool that uses AI to help technicians understand and troubleshoot system issues. It provides natural language interaction with your Windows Event Logs, powered by Google's Gemini AI.

## Features

- Collect and analyze Windows Event Logs (System, Application, Security)
- Natural language queries about system events
- AI-powered log analysis using Google Gemini
- Interactive Q&A mode for detailed investigation
- Offline-first design - all analysis happens locally
- Beautiful command-line interface with color support

## Requirements

- Windows 10/11
- Python 3.9+
- PowerShell 5.1 or later
- Google Gemini API key

## Installation

1. Download the latest installer from the releases page
2. Run `AnimusSetup.exe`
3. Create a `.env` file in the installation directory with your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

Basic commands:
```bash
# Collect logs
animus collect

# Start interactive Q&A mode
animus --qa

# Get help
animus --help
```

Example questions:
- "Why did my system reboot last night?"
- "Show me any critical errors from the last 24 hours"
- "Have there been any disk-related warnings?"

## Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/animus.git
   cd animus
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create `.env` file with your Gemini API key

4. Run in development mode:
   ```bash
   python -m animus_cli.main
   ```

## Building

See [BUILD.md](BUILD.md) for detailed build instructions.

## License

[MIT License](LICENSE)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
