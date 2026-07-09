# JejuNowHere - Windows Task Scheduler registration
# Run   : powershell -ExecutionPolicy Bypass -File register_tasks.ps1
# Remove: powershell -ExecutionPolicy Bypass -File register_tasks.ps1 -Remove

param([switch]$Remove)

$Dir = $PSScriptRoot
$Names = @("JejuNowHere-Hourly", "JejuNowHere-Village", "JejuNowHere-UV")

if ($Remove) {
    foreach ($n in $Names) {
        Unregister-ScheduledTask -TaskName $n -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "Removed: $n"
    }
    exit
}

$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

function Act($bat) {
    New-ScheduledTaskAction -Execute "cmd.exe" `
        -Argument ('/c ""{0}\{1}""' -f $Dir, $bat) -WorkingDirectory $Dir
}

# 1) Every hour at :50 -> nowcast + ultra + jeju_air
$t1 = New-ScheduledTaskTrigger -Once -At (Get-Date -Hour 0 -Minute 50 -Second 0) `
    -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
Register-ScheduledTask -TaskName $Names[0] -Action (Act "collect_hourly.bat") `
    -Trigger $t1 -Settings $Settings -Force | Out-Null
Write-Host "Registered: JejuNowHere-Hourly  - every hour at :50 (nowcast + ultra + jeju_air)"

# 2) Village forecast: 8 publish times +15min
$t2 = @(2, 5, 8, 11, 14, 17, 20, 23 | ForEach-Object {
    New-ScheduledTaskTrigger -Daily -At ("{0:d2}:15" -f $_)
})
Register-ScheduledTask -TaskName $Names[1] -Action (Act "collect_village.bat") `
    -Trigger $t2 -Settings $Settings -Force | Out-Null
Write-Host "Registered: JejuNowHere-Village - 02/05/08/11/14/17/20/23 at :15 (village)"

# 3) UV index: 2 publish times +40min
$t3 = @(
    New-ScheduledTaskTrigger -Daily -At "06:40"
    New-ScheduledTaskTrigger -Daily -At "18:40"
)
Register-ScheduledTask -TaskName $Names[2] -Action (Act "collect_uv.bat") `
    -Trigger $t3 -Settings $Settings -Force | Out-Null
Write-Host "Registered: JejuNowHere-UV      - 06:40 / 18:40 (uv)"

Write-Host ""
Write-Host "Done. Check: taskschd.msc > Task Scheduler Library"
Write-Host "Test now  : Start-ScheduledTask -TaskName JejuNowHere-Hourly"
Write-Host "Log file  : logs\collect.log"
