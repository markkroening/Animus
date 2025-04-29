param(
    [Parameter(Mandatory=$true)]
    [string]$OutputPath,
    
    [Parameter(Mandatory=$false)]
    [int]$HoursBack = 48,
    
    [Parameter(Mandatory=$false)]
    [int]$MaxEvents = 500
)

# Suppress all output
$ProgressPreference = 'SilentlyContinue'
$VerbosePreference = 'SilentlyContinue'
$InformationPreference = 'SilentlyContinue'
$WarningPreference = 'SilentlyContinue'
$DebugPreference = 'SilentlyContinue'
$ErrorActionPreference = 'SilentlyContinue'

# Redirect all output streams to null
$null = $PSDefaultParameterValues['*:Verbose'] = $false
$null = $PSDefaultParameterValues['*:Debug'] = $false
$null = $PSDefaultParameterValues['*:Information'] = $false
$null = $PSDefaultParameterValues['*:Warning'] = $false
$null = $PSDefaultParameterValues['*:ErrorAction'] = 'SilentlyContinue'

try {
    # Calculate start time
    $startTime = (Get-Date).AddHours(-$HoursBack)
    
    # Get system metadata silently
    $osInfo = Get-WmiObject Win32_OperatingSystem -ErrorAction SilentlyContinue
    $lastBootTime = [System.Management.ManagementDateTimeConverter]::ToDateTime($osInfo.LastBootUpTime)
    $currentTime = Get-Date
    $uptimeHours = [math]::Round(($currentTime - $lastBootTime).TotalHours)
    
    $systemInfo = @{
        ComputerName = $env:COMPUTERNAME
        OSVersion = $osInfo.Caption
        LastBootTime = $lastBootTime.ToString("o")
        Uptime = $uptimeHours
    }
    
    # Collect System and Application logs silently
    $logs = @{
        System = Get-EventLog -LogName System -After $startTime -Newest $MaxEvents -ErrorAction SilentlyContinue |
            Select-Object TimeGenerated, EntryType, Source, EventID, Message
        Application = Get-EventLog -LogName Application -After $startTime -Newest $MaxEvents -ErrorAction SilentlyContinue |
            Select-Object TimeGenerated, EntryType, Source, EventID, Message
    }
    
    # Compile data
    $output = @{
        CollectionTime = $currentTime.ToString("yyyy-MM-dd HH:mm:ss")
        TimeRange = @{
            StartTime = $startTime.ToString("o")
            EndTime = $currentTime.ToString("o")
        }
        SystemInfo = $systemInfo
        Logs = $logs
    }
    
    # Export to JSON silently
    $output | ConvertTo-Json -Depth 10 | Set-Content -Path $OutputPath -Encoding UTF8 -NoNewline
    
    exit 0
} catch {
    Write-Error $_.Exception.Message -ErrorAction SilentlyContinue
    exit 1
} 