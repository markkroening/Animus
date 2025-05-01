# Animus CLI

Animus CLI is a powerful Windows Event Log analysis tool that uses AI to help technicians understand and troubleshoot system issues. It provides natural language interaction with your Windows Event Logs, powered by Google's Gemini AI.

## Features

- Collect and analyze Windows Event Logs (System and Application)
- Natural language queries about system events
- AI-powered log analysis using Google Gemini
- Interactive Q&A mode for detailed investigation
- Offline-first design - all analysis happens locally
- Clean, minimal command-line interface

## Requirements

- Windows 10/11
- Python 3.9+
- PowerShell 5.1 or later
- Google Gemini API key

## Installation

### Standard Installation
1. Download the latest installer from the releases page
2. Run `AnimusSetup.exe`
3. Set your Gemini API key using the provided script:
   ```batch
   set_api_key.bat your_api_key_here
   ```

### Silent Installation
For automated or unattended installations, you can use the following command-line switch:

```batch
AnimusSetup.exe /VERYSILENT
```

Note: A UAC prompt will still appear as this is required by Windows for security reasons.

## Usage

Start Animus in interactive mode:
```batch
animus
```

Optional flags:
```batch
animus --verbose  # Enable verbose output for debugging
```

Example questions:
- "Why did my system reboot last night?"
- "Show me any critical errors from the last 24 hours"
- "Have there been any disk-related warnings?"
- "What's the most common error in the application logs?"

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

3. Set your Gemini API key:
   ```batch
   set_api_key.bat your_api_key_here
   ```

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
