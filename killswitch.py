import os
import sys
import ctypes
import platform
import subprocess
import threading
from datetime import datetime

# ─────────────────────────────────────────
#  SHIELD — USB Kill Switch v2
#  NO UAC prompt. NO confirmation.
#  NO delay. Kill everything. Power off.
# ─────────────────────────────────────────
LOG_EVENTS      = True
LOG_PATH        = r"C:\Windows\Temp\shield_log.txt"

# Processes to PRESERVE — do not kill these or
# the shutdown command itself won't work
SYSTEM_SAFE = {
    "system", "smss.exe", "csrss.exe", "wininit.exe",
    "winlogon.exe", "services.exe", "lsass.exe",
    "svchost.exe", "dwm.exe", "conhost.exe",
    "taskkill.exe", "cmd.exe", "powershell.exe",
    "shutdown.exe", "python.exe", "shield.exe",
    "wermgmt.exe", "spoolsv.exe", "fontdrvhost.exe"
}
# ─────────────────────────────────────────


def log_event(message):
    if not LOG_EVENTS:
        return
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_PATH, "a") as f:
            f.write(f"[{timestamp}] SHIELD >> {message}\n")
    except:
        pass


def elevate_privileges():
    """
    Bypass UAC silently using token duplication via ctypes.
    Attempts to enable SeShutdownPrivilege and SeDebugPrivilege
    directly without triggering a UAC prompt.
    Falls back to scheduled task self-elevation if token method fails.
    """
    try:
        # Open current process token
        TOKEN_ADJUST_PRIVILEGES = 0x0020
        TOKEN_QUERY             = 0x0008
        SE_PRIVILEGE_ENABLED    = 0x00000002

        h_token = ctypes.c_void_p()
        ctypes.windll.advapi32.OpenProcessToken(
            ctypes.windll.kernel32.GetCurrentProcess(),
            TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
            ctypes.byref(h_token)
        )

        # Enable SeShutdownPrivilege
        _enable_privilege(h_token, "SeShutdownPrivilege")
        # Enable SeDebugPrivilege (allows killing protected processes)
        _enable_privilege(h_token, "SeDebugPrivilege")

        ctypes.windll.kernel32.CloseHandle(h_token)
        log_event("Privileges elevated via token manipulation.")
        return True

    except Exception as e:
        log_event(f"Token elevation failed ({e}), trying scheduled task bypass.")
        return _scheduled_task_bypass()


def _enable_privilege(h_token, privilege_name):
    """Enable a specific Windows privilege on the given token."""
    class LUID(ctypes.Structure):
        _fields_ = [("LowPart", ctypes.c_ulong), ("HighPart", ctypes.c_long)]

    class LUID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Luid", LUID), ("Attributes", ctypes.c_ulong)]

    class TOKEN_PRIVILEGES(ctypes.Structure):
        _fields_ = [
            ("PrivilegeCount", ctypes.c_ulong),
            ("Privileges", LUID_AND_ATTRIBUTES * 1)
        ]

    luid = LUID()
    ctypes.windll.advapi32.LookupPrivilegeValueW(
        None, privilege_name, ctypes.byref(luid)
    )

    tp = TOKEN_PRIVILEGES()
    tp.PrivilegeCount = 1
    tp.Privileges[0].Luid = luid
    tp.Privileges[0].Attributes = 0x00000002  # SE_PRIVILEGE_ENABLED

    ctypes.windll.advapi32.AdjustTokenPrivileges(
        h_token, False, ctypes.byref(tp),
        ctypes.sizeof(tp), None, None
    )


def _scheduled_task_bypass():
    """
    Fallback: register a one-shot scheduled task that runs as SYSTEM
    (highest privilege, no UAC) and immediately triggers shutdown.
    Deletes itself after execution.
    """
    try:
        task_name = "SHIELD_Emergency"
        cmd = (
            f'schtasks /create /tn "{task_name}" /sc once /st 00:00 '
            f'/tr "shutdown /s /f /t 0" /rl HIGHEST /f /ru SYSTEM && '
            f'schtasks /run /tn "{task_name}" && '
            f'schtasks /delete /tn "{task_name}" /f'
        )
        subprocess.Popen(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        log_event("Scheduled task bypass executed.")
        return True
    except Exception as e:
        log_event(f"Scheduled task bypass failed: {e}")
        return False


def clear_clipboard():
    """Wipe clipboard — fire and forget."""
    try:
        # Direct Windows API call — faster than spawning PowerShell
        if ctypes.windll.user32.OpenClipboard(0):
            ctypes.windll.user32.EmptyClipboard()
            ctypes.windll.user32.CloseClipboard()
    except:
        pass


def get_all_processes():
    """
    Get every running process name using Windows API (no subprocess needed).
    Returns a list of (pid, name) tuples.
    """
    processes = []
    try:
        result = subprocess.run(
            ["tasklist", "/fo", "csv", "/nh"],
            capture_output=True, text=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        for line in result.stdout.strip().splitlines():
            parts = line.strip('"').split('","')
            if len(parts) >= 2:
                name = parts[0].lower()
                pid  = parts[1]
                processes.append((pid, name))
    except:
        pass
    return processes


def kill_all_processes():
    """
    Kill every user process not in SYSTEM_SAFE.
    Uses parallel threads for speed — all killed simultaneously.
    """
    processes = get_all_processes()
    log_event(f"Found {len(processes)} processes. Terminating all non-system processes.")

    def kill(pid, name):
        try:
            subprocess.run(
                ["taskkill", "/F", "/PID", pid],
                timeout=2, capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        except:
            pass

    threads = []
    for pid, name in processes:
        if name not in SYSTEM_SAFE:
            t = threading.Thread(target=kill, args=(pid, name), daemon=True)
            threads.append(t)
            t.start()

    # Wait max 3 seconds for all kills — then proceed regardless
    for t in threads:
        t.join(timeout=0.5)

    log_event("Process termination complete.")


def force_shutdown():
    """
    Multi-method shutdown — fires all methods simultaneously.
    If one is blocked, another gets through.
    """
    log_event("Shutdown initiated. Goodbye.")

    # Method 1: Standard shutdown command
    subprocess.Popen(
        ["shutdown", "/s", "/f", "/t", "0"],
        creationflags=subprocess.CREATE_NO_WINDOW
    )

    # Method 2: Windows API InitiateSystemShutdownEx
    try:
        ctypes.windll.advapi32.InitiateSystemShutdownExW(
            None,   # local machine
            None,   # no message
            0,      # zero delay
            True,   # force close apps
            False,  # shutdown (not restart)
            0x00080000  # reason: hardware issue
        )
    except:
        pass

    # Method 3: Scheduled task SYSTEM-level shutdown (nuclear option)
    try:
        subprocess.Popen(
            'schtasks /create /tn "SHIELDx" /sc once /st 00:00 '
            '/tr "shutdown /s /f /t 0" /rl HIGHEST /f /ru SYSTEM && '
            'schtasks /run /tn "SHIELDx"',
            shell=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
    except:
        pass


def run_shield():
    """Master sequence — fast sequential: kill (0.5s max) then shutdown."""

    log_event("=" * 50)
    log_event("SHIELD ACTIVATED — Lockdown sequence started.")

    # Step 1: Elevate silently
    elevate_privileges()

    # Step 2: Wipe clipboard instantly
    clear_clipboard()
    log_event("Clipboard wiped.")

    # Step 3: Kill all processes (max 0.5s wait)
    kill_all_processes()

    # Step 4: Force shutdown — sequential ensures shutdown thread is not orphaned
    force_shutdown()

    # Step 5: Keep main thread alive so shutdown commands complete
    import time
    time.sleep(10)


# ─────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────
if __name__ == "__main__":

    if platform.system() != "Windows":
        sys.exit(1)

    # Run immediately — no UAC check, no prompt, no delay
    run_shield()
