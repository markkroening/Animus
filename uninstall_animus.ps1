# Requires -RunAsAdministrator

$installDir = "$env:ProgramFiles\Animus"

# Remove from PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
$newPath = ($currentPath -split ';' | Where-Object { $_ -ne $installDir }) -join ';'
[Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")

# Remove installation directory
if (Test-Path $installDir) {
    Remove-Item -Path $installDir -Recurse -Force
}

Write-Host "Animus has been uninstalled successfully!" -ForegroundColor Green
Write-Host "Please restart any open command prompts for the changes to take effect." -ForegroundColor Yellow 