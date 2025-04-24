# Uninstall Animus CLI
# Run this script as Administrator

# Define the Animus installation directory
$targetDir = "$env:ProgramFiles\Animus"

# Check if Animus is installed
if (-not (Test-Path $targetDir)) {
    Write-Host "Animus is not installed at $targetDir."
    exit
}

# Remove from PATH
$path = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($path -like "*$targetDir*") {
    Write-Host "Removing Animus from system PATH..."
    $newPath = ($path.Split(';') | Where-Object { $_ -ne $targetDir }) -join ';'
    [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
}

# Remove the Animus directory
Write-Host "Removing Animus files..."
Remove-Item -Path $targetDir -Recurse -Force

Write-Host "Animus has been uninstalled successfully!"
Write-Host "Note: You may need to restart your command prompt for the changes to take effect." 