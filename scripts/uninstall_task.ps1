# Removes the scheduled task installed by install_task.ps1.
$TaskName = "MorningBriefingPipeline"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "Scheduled task '$TaskName' removed (if it existed)."
