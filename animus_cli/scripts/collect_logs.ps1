param(
    [Parameter(Mandatory=$true)]
    [string]$OutputPath,
    
    [Parameter(Mandatory=$false)]
    [int]$HoursBack = 48,
    
    [Parameter(Mandatory=$false)]
    [int]$MaxEventsPerLog = 500
)

# --- Script Start ---
Write-Verbose "Starting log collection script..."

try {
    # Calculate start time
    $startTime = (Get-Date).AddHours(-$HoursBack)
    $currentTime = Get-Date
    Write-Verbose "Collecting events generated after: $($startTime.ToString('o'))"
    
    # --- System Information ---
    Write-Verbose "Gathering system information..."
    $compInfo = Get-ComputerInfo -ErrorAction SilentlyContinue
    $osInfo = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue

    $systemInfo = @{
        ComputerName = $env:COMPUTERNAME
        OSVersion = $compInfo.OsName
        OSDisplayVersion = $compInfo.OsDisplayVersion
        OSBuildNumber = $compInfo.OsBuildNumber
        CsModel = $compInfo.CsModel
        CsManufacturer = $compInfo.CsManufacturer
        TotalPhysicalMemory = "$([math]::Round($compInfo.CsTotalPhysicalMemory / 1GB)) GB"
        InstallDate = if ($osInfo.InstallDate) { $osInfo.InstallDate.ToString("o") } else { $null }
        LastBootTime = if ($osInfo.LastBootUpTime) { $osInfo.LastBootUpTime.ToString("o") } else { $null }
        UptimeHours = if ($osInfo.LastBootUpTime) { [math]::Round(($currentTime - $osInfo.LastBootUpTime).TotalHours) } else { $null }
    }
    
    # --- Network Information ---
    Write-Verbose "Gathering network information..."
    $networkAdaptersInfo = @()
    $activeIpConfigs = Get-NetIPConfiguration -ErrorAction SilentlyContinue | Where-Object { $_.NetAdapter.Status -eq 'Up' -and $_.IPv4Address.IPAddress -ne $null }
    
    foreach ($ipConfig in $activeIpConfigs) {
        $adapter = $ipConfig.NetAdapter
        $adapterInfo = @{
            Name = $adapter.Name
            Description = $adapter.InterfaceDescription
            MACAddress = $adapter.MacAddress
            Status = $adapter.Status
            IPv4Address = ($ipConfig.IPv4Address | Select-Object -ExpandProperty IPAddress -First 1)
            IPv6Address = ($ipConfig.IPv6Address | Select-Object -ExpandProperty IPAddress -First 1)
            DNSServers = ($ipConfig.DNSServer.ServerAddresses | Where-Object { $_ -match '^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$' })
            Gateway = ($ipConfig.IPv4DefaultGateway | Select-Object -ExpandProperty NextHop -First 1)
        }
        $networkAdaptersInfo += $adapterInfo
    }
    $networkInfo = @{ Adapters = $networkAdaptersInfo }

    # --- Event Log Collection ---
    Write-Verbose "Collecting event logs (System, Application, Security)..."
    $allEvents = @()
    $logNames = 'System', 'Application', 'Security'
    
    foreach ($logName in $logNames) {
        Write-Verbose "Processing '$logName' log..."
        try {
            # Use Get-WinEvent -FilterHashtable for better performance and filtering
            $events = Get-WinEvent -FilterHashtable @{
                LogName = $logName
                StartTime = $startTime
            } -MaxEvents $MaxEventsPerLog -ErrorAction Stop

            # Select and format desired properties
            $formattedEvents = $events | Select-Object @{N='LogName'; E={$_.LogName}},
                                                    @{N='TimeCreated'; E={$_.TimeCreated.ToUniversalTime().ToString("o")}},
                                                    @{N='Level'; E={$_.LevelDisplayName}},
                                                    @{N='ProviderName'; E={$_.ProviderName}},
                                                    @{N='EventID'; E={$_.Id}},
                                                    Message
            
            $allEvents += $formattedEvents
            Write-Verbose "Collected $($formattedEvents.Count) events from '$logName'."

        } catch {
            Write-Warning "Could not retrieve events from '$logName' log. Error: $($_.Exception.Message)"
            # Continue to next log even if one fails
        }
    }
    
    # --- Compile Final Output ---
    Write-Verbose "Compiling final output..."
    $outputData = @{
        CollectionTime = $currentTime.ToString("o")
        TimeRange = @{
            StartTime = $startTime.ToString("o")
            EndTime = $currentTime.ToString("o")
        }
        SystemInfo = $systemInfo
        NetworkInfo = $networkInfo
        Events = $allEvents
    }
    
    # --- Export to JSON ---
    Write-Verbose "Exporting data to JSON file: $OutputPath"
    # Use Out-File for potentially large files, ensure parent directory exists
    $null = New-Item -ItemType Directory -Path (Split-Path $OutputPath -Parent) -Force
    $outputData | ConvertTo-Json -Depth 5 -Compress | Out-File -FilePath $OutputPath -Encoding UTF8
    
    Write-Verbose "Script completed successfully. Collected $($allEvents.Count) total events."
    exit 0

} catch {
    # Log the specific error that caused the script to fail
    $errorMessage = "Script failed with error: $($_.Exception.Message) at line $($_.InvocationInfo.ScriptLineNumber)"
    Write-Error $errorMessage 
    # Optionally write to a log file or event log here
    exit 1 # Exit with a non-zero code to indicate failure
}