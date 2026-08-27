# Registers a Windows scheduled task that runs the briefing pipeline every
# 30 minutes, but only while the PC is on and you're logged in (no wake-from-
# sleep, no run-on-battery-drain surprises). Run this once, as yourself,
# from an ordinary (non-admin) PowerShell prompt:
#
#   powershell -ExecutionPolicy Bypass -File scripts\install_task.ps1
#
# Re-run it any time to update the task (e.g. after moving the repo).

$ErrorActionPreference = "Stop"

$TaskName = "MorningBriefingPipeline"
$RepoRoot = (Resolve-Path "$PSScriptRoot\..").Path
$PythonExe = (Get-Command py -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) { $PythonExe = (Get-Command python -ErrorAction Stop).Source }

$Action = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "scripts\run_pipeline.py" `
    -WorkingDirectory $RepoRoot

# Fire once at logon, then every 30 minutes, indefinitely, only while the
# session is active — this is the standard pattern for "keep repeating for
# as long as the PC is on" in Task Scheduler.
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -MultipleInstances IgnoreNew

$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName `
    -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal `
    -Description "Rebuilds and publishes the morning-briefing site every 30 min while the PC is on." `
    -Force | Out-Null

Write-Host "Scheduled task '$TaskName' installed: runs scripts\run_pipeline.py every 30 min."
Write-Host "Working directory: $RepoRoot"
Write-Host "Python: $PythonExe"
Write-Host ""
Write-Host "Check it in Task Scheduler (taskschd.msc), or run it once now with:"
Write-Host "  Start-ScheduledTask -TaskName $TaskName"
