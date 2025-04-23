# Animus Log Collector Script
# This script collects Windows Event Logs (System, Application, Security) and system metadata,
# then outputs them to a JSON file for analysis by the Animus CLI.

# Parameters
param (
    [string]$OutputFile = "animus_logs.json", # Default output file path
    [int]$HoursBack = 48,                    # Default to collect logs from the last 48 hours
    [int]$MaxEvents = 500,                   # Maximum events per log type
    [switch]$IncludeSecurity = $true         # Flag to include Security logs (which can be large)
)

# Ensure output directory exists
$OutputDir = Split-Path -Parent $OutputFile
if ($OutputDir -and -not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Function to get formatted date/time for filtering
function Get-FormattedTimeBack {
    param ([int]$Hours)
    return (Get-Date).AddHours(-$Hours).ToString("o")
}

# Set error action preference
$ErrorActionPreference = "SilentlyContinue"

# Create timestamp for the collection
$CollectionTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$TimeFilter = Get-FormattedTimeBack -Hours $HoursBack

Write-Host "Animus Log Collector starting at $CollectionTime"
Write-Host "Collecting events from the past $HoursBack hours (since $TimeFilter)"

# Check for administrator privileges
$IsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $IsAdmin) {
    Write-Host "WARNING: Not running with administrator privileges. Security logs may be inaccessible." -ForegroundColor Yellow
}

# -----------------------------------------
# 1. Collect System Metadata
# -----------------------------------------
Write-Host "Collecting system metadata..."

# OS Information
$OSInfo = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, OSArchitecture, 
                                                   @{Name="InstallDate"; Expression={$_.InstallDate.ToString("yyyy-MM-dd")}},
                                                   @{Name="LastBootUpTime"; Expression={$_.LastBootUpTime.ToString("yyyy-MM-dd HH:mm:ss")}},
                                                   @{Name="UpTime"; Expression={
                                                       $Timespan = (Get-Date) - $_.LastBootUpTime
                                                       "{0:D2}d:{1:D2}h:{2:D2}m:{3:D2}s" -f $Timespan.Days, $Timespan.Hours, $Timespan.Minutes, $Timespan.Seconds
                                                   }}

# Computer System Information
$ComputerInfo = Get-CimInstance Win32_ComputerSystem | Select-Object Name, Manufacturer, Model, 
                                                        SystemType, NumberOfProcessors, 
                                                        @{Name="TotalPhysicalMemory"; Expression={[math]::Round($_.TotalPhysicalMemory / 1GB, 2).ToString() + " GB"}}

# CPU Information
$ProcessorInfo = Get-CimInstance Win32_Processor | Select-Object Name, Description, NumberOfCores, NumberOfLogicalProcessors, 
                                                   MaxClockSpeed, @{Name="MaxClockSpeedGHz"; Expression={($_.MaxClockSpeed / 1000).ToString("0.00") + " GHz"}}

# Disk Information
$DiskInfo = Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | Select-Object DeviceID, 
                                                  @{Name="Size"; Expression={[math]::Round($_.Size / 1GB, 2).ToString() + " GB"}}, 
                                                  @{Name="FreeSpace"; Expression={[math]::Round($_.FreeSpace / 1GB, 2).ToString() + " GB"}},
                                                  @{Name="PercentFree"; Expression={[math]::Round(($_.FreeSpace / $_.Size) * 100, 2).ToString() + "%"}}

# -----------------------------------------
# 2. Collect Windows Event Logs
# -----------------------------------------
Write-Host "Collecting event logs..."

# Common filter for date range
$DateFilter = @{StartTime = (Get-Date).AddHours(-$HoursBack); EndTime = (Get-Date)}

# Function to gather logs with error handling
function Get-FilteredEvents {
    param (
        [string]$LogName,
        [int]$MaxEvents
    )
    
    try {
        Write-Host "  Collecting $LogName logs..."
        $Events = Get-WinEvent -FilterHashtable @{
            LogName = $LogName
            StartTime = $DateFilter.StartTime
            EndTime = $DateFilter.EndTime
        } -MaxEvents $MaxEvents -ErrorAction SilentlyContinue
        
        # Transform to custom objects with relevant properties
        $Events | ForEach-Object {
            # Create clean objects with proper string encoding for JSON compatibility
            [PSCustomObject]@{
                TimeCreated = $_.TimeCreated.ToString("yyyy-MM-dd HH:mm:ss")
                LogName = $_.LogName
                Level = [string](Get-EventLevelName -LevelNumber $_.Level)
                EventID = $_.Id
                ProviderName = $_.ProviderName
                Message = $_.Message -replace "`r`n", "\n" -replace "`r", "\n" -replace "[^\u0020-\u007E\u000A]", " " # Clean message for better JSON compatibility
                MachineName = $_.MachineName
                UserId = $_.UserId
                TaskDisplayName = $_.TaskDisplayName
                ProcessId = $_.ProcessId
                ThreadId = $_.ThreadId
            }
        }
    }
    catch {
        Write-Host "  Error collecting $LogName logs: $_" -ForegroundColor Red
        @() # Return empty array on error
    }
}

# Helper function to convert numeric level to name
function Get-EventLevelName {
    param ([int]$LevelNumber)
    
    switch ($LevelNumber) {
        1 { "Critical" }
        2 { "Error" }
        3 { "Warning" }
        4 { "Information" }
        5 { "Verbose" }
        default { "Unknown ($LevelNumber)" }
    }
}

# Collect events from different logs
$SystemEvents = Get-FilteredEvents -LogName "System" -MaxEvents $MaxEvents
$ApplicationEvents = Get-FilteredEvents -LogName "Application" -MaxEvents $MaxEvents
$SecurityEvents = @()
if ($IncludeSecurity) {
    # Special handling for Security logs
    if ($IsAdmin) {
        $SecurityEvents = Get-FilteredEvents -LogName "Security" -MaxEvents $MaxEvents
        if ($SecurityEvents.Count -eq 0) {
            Write-Host "  No Security events found in the specified time range." -ForegroundColor Yellow
        }
    } else {
        Write-Host "  Security logs require administrator privileges. Skipping." -ForegroundColor Yellow
    }
}

# Calculate event counts 
$EventCounts = [PSCustomObject]@{
    SystemEvents = $SystemEvents.Count
    ApplicationEvents = $ApplicationEvents.Count
    SecurityEvents = $SecurityEvents.Count
    TotalEvents = $SystemEvents.Count + $ApplicationEvents.Count + $SecurityEvents.Count
}

# -----------------------------------------
# 3. Compile results and export to JSON
# -----------------------------------------
Write-Host "Compiling and exporting data..."

# Create the full result object
$Result = [PSCustomObject]@{
    CollectionInfo = [PSCustomObject]@{
        CollectionTime = $CollectionTime
        TimeRange = @{
            StartTime = $DateFilter.StartTime.ToString("yyyy-MM-dd HH:mm:ss")
            EndTime = $DateFilter.EndTime.ToString("yyyy-MM-dd HH:mm:ss")
            HoursBack = $HoursBack
        }
        EventCounts = $EventCounts
    }
    SystemInfo = [PSCustomObject]@{
        OS = $OSInfo
        Computer = $ComputerInfo
        Processor = $ProcessorInfo
        Disks = $DiskInfo
    }
    Events = @{
        System = $SystemEvents
        Application = $ApplicationEvents
        Security = $SecurityEvents
    }
}

# Export to JSON with proper encoding
try {
    # Use UTF-8 without BOM for better compatibility
    $JsonResult = $Result | ConvertTo-Json -Depth 10 -Compress
    
    # Validate JSON before saving
    $null = $JsonResult | ConvertFrom-Json
    
    # Use System.IO.File.WriteAllText with UTF8NoBOM encoding
    $Utf8NoBomEncoding = New-Object System.Text.UTF8Encoding $False
    [System.IO.File]::WriteAllText($OutputFile, $JsonResult, $Utf8NoBomEncoding)
    
    Write-Host "Log collection complete. Total events: $($EventCounts.TotalEvents)"
    Write-Host "System: $($EventCounts.SystemEvents) | Application: $($EventCounts.ApplicationEvents) | Security: $($EventCounts.SecurityEvents)"
    Write-Host "Results exported to: $OutputFile"
} catch {
    Write-Host "ERROR: Failed to create valid JSON output: $_" -ForegroundColor Red
    Write-Host "Attempting to write a simplified version..." -ForegroundColor Yellow
    
    # Try to write a simplified version without potentially problematic fields
    try {
        $SimpleResult = [PSCustomObject]@{
            CollectionInfo = [PSCustomObject]@{
                CollectionTime = $CollectionTime
                TimeRange = @{
                    StartTime = $DateFilter.StartTime.ToString("yyyy-MM-dd HH:mm:ss")
                    EndTime = $DateFilter.EndTime.ToString("yyyy-MM-dd HH:mm:ss")
                    HoursBack = $HoursBack
                }
                EventCounts = $EventCounts
            }
            Events = @{
                System = @()
                Application = @()
                Security = @()
            }
        }
        $Utf8NoBomEncoding = New-Object System.Text.UTF8Encoding $False
        $SimpleJsonResult = $SimpleResult | ConvertTo-Json -Depth 3
        [System.IO.File]::WriteAllText($OutputFile, $SimpleJsonResult, $Utf8NoBomEncoding)
        Write-Host "Simplified log file created at: $OutputFile" -ForegroundColor Yellow
    } catch {
        Write-Host "FATAL ERROR: Could not create any valid JSON output." -ForegroundColor Red
    }
}
