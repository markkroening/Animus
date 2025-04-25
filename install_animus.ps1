# Requires -RunAsAdministrator

# Create a directory for Animus in Program Files if it doesn't exist
$installDir = "$env:ProgramFiles\Animus"
if (-not (Test-Path $installDir)) {
    New-Item -ItemType Directory -Path $installDir | Out-Null
}

# Copy the executable and batch file
Copy-Item "dist\animus.exe" -Destination "$installDir\animus.exe" -Force
Copy-Item "animus.bat" -Destination "$installDir\animus.bat" -Force

# Add to PATH if not already present
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($currentPath -notlike "*$installDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$installDir", "Machine")
}

Write-Host "Animus has been installed successfully!" -ForegroundColor Green
Write-Host "You can now use the 'animus' command from any command prompt or PowerShell window." -ForegroundColor Green
Write-Host "Please restart any open command prompts for the changes to take effect." -ForegroundColor Yellow 