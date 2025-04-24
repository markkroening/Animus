# Install Animus CLI to make it globally accessible
# Run this script as Administrator

# Get the current directory (where this script is located)
$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Define the target directory for the Animus executable
$targetDir = "$env:ProgramFiles\Animus"

# Create the target directory if it doesn't exist
if (-not (Test-Path $targetDir)) {
    Write-Host "Creating Animus directory at $targetDir..."
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
}

# Copy the necessary files
Write-Host "Copying Animus files..."
Copy-Item "$currentDir\animus.bat" "$targetDir\animus.bat" -Force
Copy-Item "$currentDir\run_animus.bat" "$targetDir\run_animus.bat" -Force
Copy-Item "$currentDir\animus_cli.py" "$targetDir\animus_cli.py" -Force
Copy-Item "$currentDir\requirements.txt" "$targetDir\requirements.txt" -Force

# Create a directory for the animus_cli module
if (-not (Test-Path "$targetDir\animus_cli")) {
    New-Item -ItemType Directory -Path "$targetDir\animus_cli" -Force | Out-Null
}

# Copy the animus_cli module
Copy-Item "$currentDir\animus_cli\*" "$targetDir\animus_cli\" -Recurse -Force

# Copy the powershell directory
if (-not (Test-Path "$targetDir\powershell")) {
    New-Item -ItemType Directory -Path "$targetDir\powershell" -Force | Out-Null
}
Copy-Item "$currentDir\powershell\*" "$targetDir\powershell\" -Recurse -Force

# Create logs directory
if (-not (Test-Path "$targetDir\logs")) {
    New-Item -ItemType Directory -Path "$targetDir\logs" -Force | Out-Null
}

# Add to PATH if not already there
$path = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($path -notlike "*$targetDir*") {
    Write-Host "Adding Animus to system PATH..."
    [Environment]::SetEnvironmentVariable("Path", "$path;$targetDir", "Machine")
}

Write-Host "Animus CLI has been installed successfully!"
Write-Host "You can now run 'animus' from any command prompt."
Write-Host "Note: You may need to restart your command prompt for the changes to take effect." 