# Setting Up Google Gemini API for Animus CLI

This guide walks you through setting up the Google Gemini API for use with Animus CLI.

## Getting a Google Gemini API Key

1. Visit [Google AI Studio](https://ai.google.dev/)
2. Sign in with your Google account
3. Click on "Get API key" in the top navigation
4. Create a new API key or use an existing one
5. Copy the API key (it should look like a long string of characters)

## Setting Up the API Key in Animus CLI

There are two ways to provide your API key to Animus CLI:

### Option 1: Using a .env File (Recommended)

1. Create a file named `.env` in the root directory of Animus CLI
2. Add the following line to the file:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
   Replace `your_api_key_here` with the API key you copied from Google AI Studio

3. Save the file

The `.env` file is included in the `.gitignore` file, so it won't be accidentally committed to version control.

### Option 2: Using Environment Variables

Alternatively, you can set the API key as an environment variable before running Animus CLI:

**Windows (Command Prompt):**
```
set GEMINI_API_KEY=your_api_key_here
run_animus.bat
```

**Windows (PowerShell):**
```
$env:GEMINI_API_KEY="your_api_key_here"
.\run_animus.bat
```

**Linux/macOS:**
```
export GEMINI_API_KEY=your_api_key_here
python animus_cli.py
```

## Selecting a Different Gemini Model

By default, Animus CLI uses the `gemini-1.5-flash-latest` model, which provides a good balance of speed and quality.

If you want to use a different model, you can specify it using the `--model-name` parameter:

```
python animus_cli.py --qa --model-name gemini-1.5-pro-latest
```

Available models include:
- `gemini-1.5-flash-latest` (default, faster responses)
- `gemini-1.5-pro-latest` (higher quality, slower)
- `gemini-pro` (older model, but still good)

## Troubleshooting

If you encounter an error about the API key not being found, check that:

1. The `.env` file is in the correct location (root directory of Animus CLI)
2. The API key is correctly formatted in the `.env` file
3. There are no extra spaces or quotes around the API key
4. The environment variable is set correctly if you're using that method

If you see an error about API quota being exceeded, you may need to:
1. Wait a bit before trying again
2. Check your quota limits in the Google AI Studio dashboard
3. Consider upgrading your API usage tier if you're using the API heavily

## Ensuring Privacy

When using the Google Gemini API:

1. Your Windows Event Logs are sent to Google's servers for processing
2. The data is processed according to Google's [privacy policy](https://ai.google.dev/docs/privacy) for AI services
3. If you have highly sensitive logs, consider using the basic analysis mode which keeps all data local

To use only the basic analysis without sending data to Google:

```
python animus_cli.py --interactive
```

This will let you use all the local log analysis features without using the Q&A mode that requires the API. 