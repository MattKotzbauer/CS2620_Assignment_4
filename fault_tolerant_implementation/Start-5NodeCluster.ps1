<#
.SYNOPSIS
  Start a 5-node Raft cluster (PowerShell version),
  using only -RedirectStandardError.
.DESCRIPTION
  1. Kills processes listening on ports 50051..50055
  2. Creates data & log directories
  3. Launches 5 nodes (node1..node5), only capturing stderr
  4. Waits for each node to show "Server started as node X" in its .err.log
  5. Writes out cluster_pids.txt
  6. Generates powershell scripts for monitoring logs, killing nodes, restarting nodes
#>

$ErrorActionPreference = "Stop"

function Wait-ForNode {
    param(
        [Parameter(Mandatory=$true)]
        [string] $NodeId,

        [Parameter(Mandatory=$true)]
        [string] $ErrorLogFile
    )

    $phrase = "Server started as node $NodeId"
    Write-Host "Waiting for $NodeId to be ready..."

    for ($i = 1; $i -le 30; $i++) {
        if (Test-Path $ErrorLogFile) {
            # If logs are written to stderr, we look for the phrase in the .err.log
            $found = Select-String -Path $ErrorLogFile -Pattern $phrase -SimpleMatch -Quiet
            if ($found) {
                Write-Host "$NodeId is ready!"
                return
            }
        }
        Start-Sleep -Seconds 1
    }

    Write-Host "ERROR: $NodeId not ready after 30 seconds."
    exit 1
}

function Kill-Ports([int[]] $Ports) {
    Write-Host "Killing processes on ports $($Ports -join ', ') if any..."

    foreach ($port in $Ports) {
        $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' }
        foreach ($conn in $conns) {
            if ($conn.OwningProcess) {
                Write-Host "Stopping process $($conn.OwningProcess) listening on port $port"
                Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
            }
        }
    }
}

Write-Host "=== Starting 5-node Raft cluster (stderr only) in PowerShell ==="

# 1) Kill existing processes on ports 50051..50055
Kill-Ports -Ports 50051,50052,50053,50054,50055

# 2) Create data/log dirs
New-Item -ItemType Directory -Force -Path "data\node1" | Out-Null
New-Item -ItemType Directory -Force -Path "data\node2" | Out-Null
New-Item -ItemType Directory -Force -Path "data\node3" | Out-Null
New-Item -ItemType Directory -Force -Path "data\node4" | Out-Null
New-Item -ItemType Directory -Force -Path "data\node5" | Out-Null
New-Item -ItemType Directory -Force -Path "logs"      | Out-Null

Write-Host "Starting 5-node Raft cluster for 2-fault tolerance..."

$pids = @()

# Node 1
Write-Host "Starting node1 (port 50051)..."
Start-Process -FilePath "python" -ArgumentList "raft_server.py --node-id node1 --config cluster_config.json --data-dir data\node1 --port 50051" `
    -RedirectStandardError  "logs\node1.err.log" `
    -WindowStyle Hidden
Start-Sleep 1
Wait-ForNode -NodeId "node1" -ErrorLogFile "logs\node1.err.log"
$pids += (Get-Process python | Where-Object { $_.Path -match "python" -and $_.StartTime -gt (Get-Date).AddMinutes(-1) } | Sort-Object StartTime | Select-Object -Last 1).Id

# Node 2
Write-Host "Starting node2 (port 50052)..."
Start-Process -FilePath "python" -ArgumentList "raft_server.py --node-id node2 --config cluster_config.json --data-dir data\node2 --port 50052" `
    -RedirectStandardError  "logs\node2.err.log" `
    -WindowStyle Hidden
Start-Sleep 1
Wait-ForNode -NodeId "node2" -ErrorLogFile "logs\node2.err.log"
$pids += (Get-Process python | Where-Object { $_.Path -match "python" -and $_.StartTime -gt (Get-Date).AddMinutes(-1) } | Sort-Object StartTime | Select-Object -Last 1).Id

# Node 3
Write-Host "Starting node3 (port 50053)..."
Start-Process -FilePath "python" -ArgumentList "raft_server.py --node-id node3 --config cluster_config.json --data-dir data\node3 --port 50053" `
    -RedirectStandardError  "logs\node3.err.log" `
    -WindowStyle Hidden
Start-Sleep 1
Wait-ForNode -NodeId "node3" -ErrorLogFile "logs\node3.err.log"
$pids += (Get-Process python | Where-Object { $_.Path -match "python" -and $_.StartTime -gt (Get-Date).AddMinutes(-1) } | Sort-Object StartTime | Select-Object -Last 1).Id

# Node 4
Write-Host "Starting node4 (port 50054)..."
Start-Process -FilePath "python" -ArgumentList "raft_server.py --node-id node4 --config cluster_config.json --data-dir data\node4 --port 50054" `
    -RedirectStandardError  "logs\node4.err.log" `
    -WindowStyle Hidden
Start-Sleep 1
Wait-ForNode -NodeId "node4" -ErrorLogFile "logs\node4.err.log"
$pids += (Get-Process python | Where-Object { $_.Path -match "python" -and $_.StartTime -gt (Get-Date).AddMinutes(-1) } | Sort-Object StartTime | Select-Object -Last 1).Id

# Node 5
Write-Host "Starting node5 (port 50055)..."
Start-Process -FilePath "python" -ArgumentList "raft_server.py --node-id node5 --config cluster_config.json --data-dir data\node5 --port 50055" `
    -RedirectStandardError  "logs\node5.err.log" `
    -WindowStyle Hidden
Start-Sleep 1
Wait-ForNode -NodeId "node5" -ErrorLogFile "logs\node5.err.log"
$pids += (Get-Process python | Where-Object { $_.Path -match "python" -and $_.StartTime -gt (Get-Date).AddMinutes(-1) } | Sort-Object StartTime | Select-Object -Last 1).Id

# Write pids
Set-Content -Path "cluster_pids.txt" -Value ($pids -join ' ')

Write-Host "All 5 nodes started. PIDs: $($pids -join ' ')"
Write-Host "To stop the cluster, run: Stop-Process -Id (Get-Content .\cluster_pids.txt)"

Write-Host "`nCreating helper scripts..."

# Equivalent of "monitor_logs.sh" -> "monitor_logs.ps1"
$monitorLogs = @'
#!/usr/bin/env pwsh
# monitor_logs.ps1 - watch .err.log files in real-time

if (!(Test-Path "logs")) {
  Write-Host "Error: logs directory not found."
  exit 1
}

Write-Host "=== Following all node .err.log files (Ctrl+C to stop) ==="
Get-Content .\logs\node*.err.log -Wait
'@
Set-Content -Path "monitor_logs.ps1" -Value $monitorLogs
Write-Host "  -> Created monitor_logs.ps1 (for watching nodeX.err.log files)."

# kill_node.ps1
$killNode = @'
#!/usr/bin/env pwsh
param(
    [Parameter(Mandatory=$true)]
    [string]$NodeNumber
)
$proc = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -match "python" -and
    ($_.CommandLine -match "--node-id node$NodeNumber")
}
if (-not $proc) {
    Write-Host "Node $NodeNumber is not running"
    exit 1
}
foreach ($p in $proc) {
    Write-Host "Killing node $NodeNumber (PID: $($p.Id))..."
    Stop-Process -Id $p.Id -Force
    Write-Host "Node $NodeNumber killed."
}
'@
Set-Content -Path "kill_node.ps1" -Value $killNode
Write-Host "  -> Created kill_node.ps1"

# restart_node.ps1
$restartNode = @'
#!/usr/bin/env pwsh
param(
    [Parameter(Mandatory=$true)]
    [string]$NodeNumber
)
$port = 50050 + [int]$NodeNumber

# Check if already running
$proc = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -match "python" -and
    ($_.CommandLine -match "--node-id node$NodeNumber")
}
if ($proc) {
    Write-Host "Node $NodeNumber is already running (PID: $($proc.Id)). Kill it first with .\kill_node.ps1 $NodeNumber"
    exit 1
}
Write-Host "Starting node $NodeNumber on port $port..."
Start-Process -FilePath "python" -ArgumentList "raft_server.py --node-id node$NodeNumber --config cluster_config.json --data-dir data\node$NodeNumber --port $port" `
    -RedirectStandardError "logs\node$NodeNumber.err.log" `
    -WindowStyle Hidden
Write-Host "Node $NodeNumber restarted."
'@
Set-Content -Path "restart_node.ps1" -Value $restartNode
Write-Host "  -> Created restart_node.ps1"

Write-Host "`nCluster startup complete!"
Write-Host "Use .\monitor_logs.ps1 to view *.err.log, or .\kill_node.ps1 / .\restart_node.ps1 to test failures."
