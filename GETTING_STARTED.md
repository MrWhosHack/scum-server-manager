# Getting Started: SCUM Server Manager

A short, copy-paste friendly guide to run the manager either from source (fastest) or as a single EXE (shareable). Windows only.

---

## Prerequisites

- Windows 10/11
- Python 3.8+ (3.10+ recommended)
- Administrator privileges when starting the actual SCUM server

Check Python:

```pwsh
python --version
```

If missing, install from https://www.python.org/downloads/ and check "Add Python to PATH".

---

## Option A: Run From Source (Recommended for first run)

1) Install dependencies

```pwsh
python -m pip install -r requirements.txt
```

2) Launch the manager

```pwsh
python .\scum_server_manager_pyside.py
```

Or double‑click `run_scum_pyside.bat` (auto‑installs missing packages and requests admin when needed).

---

## Option B: Build a One‑Click EXE

This produces a single `SCUM-Server-Manager.exe` you can share with friends or teammates.

Run the PowerShell builder (will create a temporary `.venv-build`, install PyInstaller, and build to `dist/`):

```pwsh
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1
```

Or double‑click: `scripts\build_exe.bat`.

Output:
- `dist\SCUM-Server-Manager.exe`

If SmartScreen warns, click “More info” → “Run anyway”.

---

## First‑Time App Setup

Inside the app:
- Click "Auto Detect" or browse to your `SCUMServer.exe`.
- Open the "Config Editor" tab and pick a preset, or customize.
- Click "Save Config Files".
- Start your server from the app.

Where configs are written (typical):
```
SCUM_Server/SCUM/Saved/Config/WindowsServer/
  ServerSettings.ini
  Game.ini
  Engine.ini
  Scalability.ini
  Input.ini
```

---

## Tips & Troubleshooting

- Run as Admin: The game server may require elevation. If start fails, right‑click the EXE or run the BAT and grant admin.
- Ports: Ensure UDP/TCP ports (e.g., 7777/7778) are open in Windows Firewall and your router.
- Python path issues: Reopen a new PowerShell window after installing Python to refresh PATH.
- Clean rebuild: Delete `.venv-build`, `build/`, and `dist/` if you hit a PyInstaller error, then re‑run the builder.
- Logs: See the `Logs/` folder; in‑app logs show errors, warnings, and player events.

---

## Uninstall / Cleanup

- Remove build artifacts: delete `.venv-build/`, `build/`, and `dist/`.
- The app itself is portable. Delete the folder if you no longer need it.

---

## Next Steps

- Read `QUICK_START_GUIDE.md` for a 5‑minute setup.
- Explore `SCUM_CONFIG_GUIDE.md` for the full list of settings (365+).
- Edit presets in `config_presets.json` to fit your server style.
