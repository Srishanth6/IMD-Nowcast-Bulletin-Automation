# Registers a Windows scheduled task that generates the IMD nowcast
# bulletin every 3 hours (00, 03, 06, 09, 12, 15, 18, 21 IST).
# Run from the project folder:  powershell -ExecutionPolicy Bypass -File scripts\setup_task_scheduler.ps1
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$TaskName = "IMD Nowcast Bulletin - 3 Hourly"
$Runner = Join-Path $Root "run_bulletin.py"
$Python = Join-Path $Root "venv\Scripts\pythonw.exe"
if (-not (Test-Path $Python)) { $Python = Join-Path $Root "venv\Scripts\python.exe" }
if (-not (Test-Path $Python)) { throw "Create the venv first: py -m venv venv; venv\Scripts\pip install -r requirements.txt" }
if (-not (Test-Path (Join-Path $Root "config.local.json"))) { throw "config.local.json is missing. Copy config.example.json and fill in the server URL." }

$Times = "00:00", "03:00", "06:00", "09:00", "12:00", "15:00", "18:00", "21:00"
$action = New-ScheduledTaskAction -Execute $Python -Argument "`"$Runner`"" -WorkingDirectory $Root
$triggers = foreach ($t in $Times) { New-ScheduledTaskTrigger -Daily -At $t }
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -WakeToRun `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 10) `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $triggers `
    -Settings $settings -Principal $principal -Force `
    -Description "Generates the IMD Telangana district nowcast bulletin every 3 hours." | Out-Null

Write-Host "Registered '$TaskName' at $($Times -join ', ')"
Write-Host "Test now:   schtasks /Run /TN `"$TaskName`""
Write-Host "Logs:       $Root\logs\imd_nowcast.log"
