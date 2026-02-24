# ─────────────────────────────────────────────────────────────
#  setup_shield.ps1 — SHIELD USB Kill Switch
#  Run once as Administrator to install the USB listener.
# ─────────────────────────────────────────────────────────────

$USB_LABEL      = "SHIELD"
$EXE_NAME       = "shield.exe"
$TASK_NAME      = "SHIELD_KillSwitch"
$LISTENER_PATH  = "C:\Windows\Temp\shield_listener.ps1"

Write-Host ""
Write-Host "  SHIELD — USB Kill Switch Setup" -ForegroundColor Cyan
Write-Host "  ================================" -ForegroundColor Cyan
Write-Host "  Listening for USB label: $USB_LABEL" -ForegroundColor Yellow
Write-Host ""

# ── Admin check ───────────────────────────────────────────────
$isAdmin = ([Security.Principal.WindowsPrincipal] `
    [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(`
    [Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "  [!] Please run as Administrator." -ForegroundColor Red
    pause
    exit 1
}

# ── Remove broken/old task if it exists ───────────────────────
Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false -ErrorAction SilentlyContinue
Write-Host "  [*] Cleaned up any previous installation." -ForegroundColor Gray

# ── Write the listener script to disk ────────────────────────
$listenerScript = @'
$USB_LABEL = "SHIELD"
$EXE_NAME  = "shield.exe"

$query = "SELECT * FROM Win32_VolumeChangeEvent WHERE EventType = 2"

Register-WmiEvent -Query $query -SourceIdentifier "SHIELDWatch" -Action {
    Start-Sleep -Seconds 2
    $drives = Get-WmiObject Win32_LogicalDisk | Where-Object { $_.VolumeName -eq "SHIELD" }
    foreach ($drive in $drives) {
        $exe = $drive.DeviceID + "\shield.exe"
        if (Test-Path $exe) {
            Start-Process $exe -Verb RunAs
        }
    }
}

while ($true) {
    Start-Sleep -Seconds 60
}
'@

Set-Content -Path $LISTENER_PATH -Value $listenerScript -Encoding UTF8
Write-Host "  [*] Listener script written to $LISTENER_PATH" -ForegroundColor Gray

# ── Register the scheduled task ───────────────────────────────
$action = New-ScheduledTaskAction `
    -Execute    "powershell.exe" `
    -Argument   "-WindowStyle Hidden -NonInteractive -ExecutionPolicy Bypass -File `"$LISTENER_PATH`""

$trigger = New-ScheduledTaskTrigger -AtLogOn

$settings = New-ScheduledTaskSettingsSet `
    -Hidden `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit 0

$principal = New-ScheduledTaskPrincipal `
    -UserId    "$env:USERDOMAIN\$env:USERNAME" `
    -RunLevel  Highest `
    -LogonType Interactive

Register-ScheduledTask `
    -TaskName   $TASK_NAME `
    -Action     $action `
    -Trigger    $trigger `
    -Settings   $settings `
    -Principal  $principal `
    -Force | Out-Null

# ── Verify ────────────────────────────────────────────────────
$task = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue

if ($task) {
    Write-Host ""
    Write-Host "  [OK] SHIELD listener installed successfully!" -ForegroundColor Green
    Write-Host "  [OK] Task state: $($task.State)" -ForegroundColor Green
    Write-Host ""
    Write-Host "  NEXT STEPS:" -ForegroundColor Yellow
    Write-Host "  1. Make sure your USB label is: SHIELD"
    Write-Host "  2. Copy shield.exe to the ROOT of the USB"
    Write-Host "  3. Log out and back in to activate the listener"
    Write-Host "  4. Plug in SHIELD USB = instant shutdown"
    Write-Host ""
    Write-Host "  Log: C:\Windows\Temp\shield_log.txt" -ForegroundColor Gray
    Write-Host "  Uninstall: Unregister-ScheduledTask -TaskName '$TASK_NAME' -Confirm:`$false" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "  [FAILED] Task could not be verified." -ForegroundColor Red
}

Write-Host ""
pause
