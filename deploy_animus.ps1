# Animus CLI Deployment Script
# This script can be used to deploy Animus to multiple machines using automation tools

param(
    [Parameter(Mandatory=$true)]
    [string]$InstallerPath,
    
    [Parameter(Mandatory=$false)]
    [string]$LogPath = "C:\Windows\Temp\AnimusDeployment.log",
    
    [Parameter(Mandatory=$false)]
    [switch]$Silent = $true,
    
    [Parameter(Mandatory=$false)]
    [switch]$Force = $false
)

# Function to write to log file
function Write-Log {
    param($Message)
    $logMessage = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'): $Message"
    Write-Host $logMessage
    Add-Content -Path $LogPath -Value $logMessage
}

# Start logging
Write-Log "Starting Animus deployment"

# Check if installer exists
if (-not (Test-Path $InstallerPath)) {
    Write-Log "Error: Installer not found at $InstallerPath"
    exit 1
}

# Check if Python is installed
try {
    $pythonVersion = python --version
    Write-Log "Python version: $pythonVersion"
} catch {
    Write-Log "Error: Python is not installed or not in PATH"
    exit 1
}

# Check if pip is available
try {
    $pipVersion = pip --version
    Write-Log "Pip version: $pipVersion"
} catch {
    Write-Log "Error: Pip is not installed or not in PATH"
    exit 1
}

# Check if Animus is already installed
$animusPath = "${env:ProgramFiles}\Animus"
if ((Test-Path $animusPath) -and (-not $Force)) {
    Write-Log "Animus is already installed at $animusPath. Use -Force to reinstall."
    exit 0
}

# Install Animus
Write-Log "Installing Animus from $InstallerPath"
$installArgs = "/i `"$InstallerPath`""
if ($Silent) {
    $installArgs += " /qn"
}

try {
    $process = Start-Process -FilePath "msiexec.exe" -ArgumentList $installArgs -Wait -PassThru -NoNewWindow
    if ($process.ExitCode -eq 0) {
        Write-Log "Animus installed successfully"
    } else {
        Write-Log "Error: Installation failed with exit code $($process.ExitCode)"
        exit $process.ExitCode
    }
} catch {
    Write-Log "Error: Failed to run installer: $_"
    exit 1
}

# Verify installation
if (Test-Path $animusPath) {
    Write-Log "Installation verified at $animusPath"
} else {
    Write-Log "Error: Installation verification failed"
    exit 1
}

# Check if Animus is in PATH
$path = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($path -notlike "*$animusPath*") {
    Write-Log "Warning: Animus directory not found in PATH"
} else {
    Write-Log "Animus directory found in PATH"
}

# Test Animus command
try {
    $animusVersion = animus --version
    Write-Log "Animus command test successful: $animusVersion"
} catch {
    Write-Log "Warning: Animus command test failed. You may need to restart the command prompt."
}

Write-Log "Deployment completed successfully"
exit 0 