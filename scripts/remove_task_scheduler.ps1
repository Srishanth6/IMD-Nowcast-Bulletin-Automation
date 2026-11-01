$TaskName = "IMD Nowcast Bulletin - 3 Hourly"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "Removed '$TaskName' (if it existed)."
