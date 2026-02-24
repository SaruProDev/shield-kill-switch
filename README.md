# 🛡️ SHIELD — USB Emergency Kill Switch

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)
![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-blue?logo=windows)
![License](https://img.shields.io/badge/License-MIT-green)
![Type](https://img.shields.io/badge/Type-Defensive%20Security-cyan)
![Status](https://img.shields.io/badge/Status-Tested%20%26%20Working-brightgreen)
![Author](https://img.shields.io/badge/Author-SaruProDev-cyan)

> Plug in the SHIELD USB. Machine shuts down instantly. No prompts. No delay. No negotiation.

---

## ⚠️ Ethical Use Disclaimer

This tool is built for **defensive purposes only** — to protect your own devices from unauthorised physical access, data theft, or compromise by an external agent.

By using, distributing, or modifying this tool you agree that:

- You will only deploy this on devices **you own or have explicit written authorisation to protect**
- You will not use this tool to cause disruption, damage, or denial of service to systems you do not own
- You understand that misuse may violate the **Computer Misuse Act (UK)**, **CFAA (USA)**, or equivalent legislation in your jurisdiction
- This project is shared for **educational and portfolio purposes** in the spirit of white-hat security research

---

## What Is SHIELD?

SHIELD turns an ordinary USB stick into a physical kill switch for Windows machines. The moment the SHIELD-labelled USB is inserted into a protected machine it:

1. Silently elevates its own privileges — no UAC prompt
2. Wipes the clipboard
3. Terminates every non-critical running process (0.5s max)
4. Forces an instant shutdown via three simultaneous methods
5. Keeps the main thread alive to ensure shutdown completes

---

## How It Actually Works — The Real Setup

> This section documents the **manual PowerShell method** — the approach that was tested and confirmed working.

The automated `setup_shield.ps1` script has known issues with WMI event subscriptions on Windows 10/11 (the `Register-WmiEvent` approach results in `NotStarted` state). The manual method below bypasses this completely using a **polling loop** that checks for the USB every 500ms and is confirmed reliable.

---

## Prerequisites

- **Python 3.8+** — [python.org](https://python.org/downloads)
  - ⚠️ During install tick **"Add Python to PATH"**
- **Windows 10 or 11**
- A USB stick labelled **SHIELD** (all caps)

---

## Step-by-Step Setup Guide

### Step 1 — Build shield.exe

Double-click `build.bat`. It will verify Python, install PyInstaller if needed, and compile `killswitch.py` into `shield.exe`.

If `pyinstaller` isn't found on PATH, the bat uses `python -m PyInstaller` automatically.

Output: `SHIELD_USB\shield.exe`

---

### Step 2 — Label Your USB

1. Plug in your USB stick
2. Right-click it in File Explorer → **Properties**
3. Change the label to: `SHIELD` (all caps, no spaces)
4. Click OK

---

### Step 3 — Copy shield.exe to USB

Copy `shield.exe` from the `SHIELD_USB\` folder to the **root** of your USB drive — drop it directly on the drive, not inside any folder.

---

### Step 4 — Install the Listener (Manual PowerShell Method)

Open **PowerShell as Administrator** (right-click Start → Terminal (Admin) or Windows PowerShell (Admin)).

**4a — Set execution policy for this session:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
```

**4b — Navigate to your SHIELD folder:**
```powershell
cd "C:\PATH\TO\YOUR\SHIELD"
```
> Replace with your actual path. Use quotes — required if the path has spaces.

**4c — Confirm your files are there:**
```powershell
dir
```
You should see `killswitch.py`, `build.bat`, `setup_shield.ps1`, `shield.exe` etc.

**4d — Write the listener file:**
```powershell
@'
while ($true) {
    $drives = Get-WmiObject Win32_LogicalDisk | Where-Object { $_.VolumeName -eq "SHIELD" }
    foreach ($drive in $drives) {
        $exe = $drive.DeviceID + "\shield.exe"
        if (Test-Path $exe) {
            Start-Process $exe -Verb RunAs
            exit
        }
    }
    Start-Sleep -Milliseconds 500
}
'@ | Set-Content -Path "C:\Windows\Temp\shield_listener.ps1" -Encoding UTF8
```

**4e — Verify the listener wrote correctly:**
```powershell
Get-Content "C:\Windows\Temp\shield_listener.ps1"
```
Should start with `while ($true) {` and nothing above it.

**4f — Register the scheduled task:**
```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument '-WindowStyle Hidden -NonInteractive -ExecutionPolicy Bypass -File "C:\Windows\Temp\shield_listener.ps1"'
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -Hidden -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0
Register-ScheduledTask -TaskName "SHIELD_KillSwitch" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force
```

You should see `SHIELD_KillSwitch` with state `Ready` or `Running`.

> **Note:** `Get-ScheduledTask` may throw an XML error on retrieval — this is a known Windows bug and does not affect functionality. If the task showed `Ready` or `Running` during registration, it is installed correctly.

---

### Step 5 — Activate

**Option A — Log out and back in** (task starts automatically at login)

**Option B — Start immediately without logging out:**
```powershell
Start-ScheduledTask -TaskName "SHIELD_KillSwitch"
```

---

### Step 6 — Test

**Save all open work first.**

Plug in your SHIELD USB. The machine should shut down within 2–5 seconds.

---

## Troubleshooting

**WMI events not firing (NotStarted state)**

This is a known Windows 11 issue with `Register-WmiEvent`. Fix:
```powershell
Unregister-Event -SourceIdentifier "SHIELDWatch" -ErrorAction SilentlyContinue
Get-Job | Remove-Job -Force
```
Then use the polling loop method in Step 4d above instead.

**Antivirus blocking shield.exe**

Add `shield.exe` as a trusted application in your antivirus exclusions. SHIELD requires:
- Process elevation (SeShutdownPrivilege)
- Process termination (SeDebugPrivilege)
- System shutdown API access

These are flagged as suspicious by antivirus — add an exclusion for the exe path on your USB drive.

**PyInstaller not found during build**

The updated `build.bat` uses `python -m PyInstaller` which bypasses PATH issues. If you still get errors, run:
```powershell
pip install pyinstaller --break-system-packages
```

**Path has spaces**

Always wrap paths in quotes:
```powershell
cd "C:\Cybersecurity Projects\SHIELD"
```

---

## Removing SHIELD

```powershell
Unregister-ScheduledTask -TaskName "SHIELD_KillSwitch" -Confirm:$false
Remove-Item "C:\Windows\Temp\shield_listener.ps1" -ErrorAction SilentlyContinue
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   SHIELD ARCHITECTURE                   │
└─────────────────────────────────────────────────────────┘

  [SHIELD USB Inserted]
          │
          ▼
  Polling loop checks every 500ms
  VolumeName == "SHIELD" + shield.exe exists?
          │
          ├── NO  → wait 500ms, check again
          │
          └── YES ▼
                  shield.exe launches (RunAs)
                          │
                          ├── Privilege elevation (advapi32 token API)
                          │   └── Fallback: SYSTEM scheduled task
                          │
                          ├── Clipboard wiped (Win32 direct)
                          │
                          ├── All processes killed (parallel, 0.5s max)
                          │
                          ├── Triple forced shutdown:
                          │   ├── shutdown /s /f /t 0
                          │   ├── InitiateSystemShutdownExW
                          │   └── SYSTEM scheduled task
                          │
                          └── Main thread sleeps 10s (ensures shutdown completes)
```

---

## Technical Reference

| Feature | Implementation |
|---|---|
| UAC bypass | `advapi32` SeShutdownPrivilege + SeDebugPrivilege token manipulation |
| Fallback elevation | SYSTEM-level scheduled task |
| USB detection | PowerShell polling loop, 500ms interval |
| Clipboard wipe | Win32 `OpenClipboard()` / `EmptyClipboard()` direct API |
| Process kill | Parallel threads, `taskkill /F /PID`, 0.5s max wait |
| Shutdown method 1 | `shutdown /s /f /t 0` |
| Shutdown method 2 | `InitiateSystemShutdownExW` (Win32 advapi32) |
| Shutdown method 3 | SYSTEM scheduled task nuclear fallback |
| Persistence | Windows Task Scheduler, triggers at logon, RunLevel Highest |
| Audit log | `C:\Windows\Temp\shield_log.txt` |

---

## Licence

MIT — free to use, modify, and distribute with attribution. Use responsibly.

---

*Built by SaruProDev · Cybersecurity Portfolio Project*
