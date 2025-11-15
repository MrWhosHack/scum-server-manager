# SCUM Server Manager - Wiki Content

Copy-paste content for https://scum.wiki.gg/wiki/SCUM_Server_Manager

---

## Description

**SCUM Server Manager** is the ultimate all-in-one administration suite for SCUM dedicated servers, designed to give server owners complete control without the complexity. Built from the ground up with modern Python and Qt6 technology, this professional-grade tool transforms server management from a tedious chore into an effortless, streamlined experience.

### What Makes It Special

Gone are the days of manually editing configuration files, searching through endless logs, and juggling multiple tools. SCUM Server Manager consolidates everything into a single, elegant interface that's powerful enough for veterans yet approachable for newcomers. Whether you're running a casual PvE server or a hardcore PvP community, this manager adapts to your needs.

### Complete Server Control

Take command of **365+ server settings** spanning every aspect of the SCUM experience—from time cycles and weather systems to combat mechanics, loot spawns, base building, economy, and AI behavior. Eight expertly crafted presets let you instantly configure your server for different play styles (PvE Casual, PvP Hardcore, RP Realism, High Action, and more), while advanced users can fine-tune every parameter for the perfect custom experience.

### Real-Time Intelligence

Monitor your server's heartbeat with live player tracking, instant connection/disconnection alerts, and comprehensive session histories. The integrated SQLite database stores detailed player analytics—play time, connection patterns, inventory data—giving you unprecedented insight into your community. Built-in performance monitoring keeps tabs on CPU, RAM, and disk usage, ensuring your server stays healthy under any load.

### Power Tools Included

- **Visual Configuration Editor**: Modify all INI files (ServerSettings, Game, Engine, Scalability, Input) through an intuitive GUI
- **Database Editor**: Direct SQLiteStudio integration for advanced player data manipulation, item spawning, and coordinate editing
- **Admin Controls**: Kick, ban, and teleport players with one click (RCON support)
- **Smart Automation**: Auto-detection of server paths, automatic backups, and intelligent log parsing
- **Multi-Category Logging**: Separate, color-coded logs for server events, player activity, admin actions, and errors

### Open Source & Community-Driven

Released under Creative Commons BY-NC-SA 4.0, SCUM Server Manager is free, transparent, and actively maintained by the community. Contributions are welcomed, and the entire codebase is available for review, modification, and improvement.

---

**Platform:** Windows 10/11  
**Requirements:** Python 3.8+ (or use the standalone EXE)  
**License:** [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)  
**Repository:** [GitHub - MrWhosHack/scum-server-manager](https://github.com/MrWhosHack/scum-server-manager)  
**Status:** Actively maintained and updated

---

## Features

### Server Management
- **One-Click Start/Stop/Restart** - Simple server control with automatic admin elevation
- **Real-Time Status Monitoring** - Live server state tracking with ready detection
- **Auto-Detection** - Automatically finds SCUM server installation paths
- **SteamCMD Integration** - Built-in server installation and update capabilities
- **Background Server Monitoring** - Continuous log parsing and event tracking

### Configuration Editor (365+ Settings)
- **Complete INI Access** - Edit all server configuration files from one interface
  - ServerSettings.ini (80+ settings)
  - Game.ini (200+ gameplay settings)
  - Engine.ini (30+ engine settings)
  - Scalability.ini (40+ performance settings)
  - Input.ini (15+ input settings)
- **8 Ready-to-Use Presets**:
  - PvE Casual (easy mode, 2x loot)
  - PvP Hardcore (brutal survival, 0.5x loot)
  - RP Realism (immersive roleplay)
  - High Action (3x loot, fast combat)
  - Performance Optimized (low-end hardware)
  - Balanced Default (standard SCUM)
  - Survival Expert (challenging PvE)
  - Build & Creative (3x resources, minimal threats)
- **Visual Preset Switcher** - Quick configuration switching with one click
- **Configuration Backup/Restore** - Automatic backup system with restore points

### Player Management
- **Real-Time Player Tracking** - Live connection/disconnection monitoring
- **Player Database** - SQLite database storing player history and statistics
- **Session Tracking** - Play time, connection history, IP tracking
- **Admin Actions**: Kick, Ban, Teleport (RCON required)
- **Ban Management** - Persistent ban list with reasons and timestamps
- **Player Search & Filtering** - Filter by online/offline, admin, banned status

### Database Editor (SQLiteStudio Integration)
- **Easy Database Editing** - Built-in SQLiteStudio with modern dialogs
- **Player Data Management** - Edit player inventories, locations, stats
- **Item Spawning** - Add/modify items in player inventories
- **Location Editing** - Teleport players, edit coordinates
- **Advanced SQL Console** - Direct database queries for power users

### Performance Monitoring
- **System Metrics** - Real-time CPU, RAM, Disk usage tracking
- **Server Process Monitoring** - SCUM server memory and CPU usage
- **Uptime Tracking** - Server session duration display
- **Performance Graphs** - Visual system resource monitoring

### Logging & Events
- **Multi-Category Logging**:
  - Server logs (startup, shutdown, errors)
  - Player logs (connections, disconnections)
  - Admin logs (commands, actions)
  - Error logs (warnings, exceptions)
  - Event logs (airdrops, mechs, server events)
- **Real-Time Log Tailing** - Live log file monitoring with auto-scroll
- **Log Parsing** - Automatic extraction of player events from SCUM server logs
- **Color-Coded Output** - Easy identification of errors, warnings, info

### User Interface
- **Modern Dark Theme** - Professional Qt6 interface with smooth animations
- **Tabbed Navigation** - Dashboard, Players, Server, Config Editor, Logs, Performance
- **Lazy Loading** - Fast startup with on-demand tab initialization
- **Responsive Design** - Optimized for 1920x1080 and higher resolutions
- **Keyboard Shortcuts** - Quick access to common functions

---

## Installation

### Prerequisites
- **Operating System**: Windows 10 or Windows 11
- **Python**: Version 3.8 or higher (3.10+ recommended)
  - Download from [python.org/downloads](https://www.python.org/downloads/)
  - During installation, check "Add Python to PATH"
- **Administrator Privileges**: Required for starting the SCUM server
- **SCUM Dedicated Server**: Installed via SteamCMD or Steam

### Method 1: Run From Source (Recommended)

1. **Download the project**
   ```powershell
   git clone https://github.com/MrWhosHack/scum-server-manager.git
   cd scum-server-manager
   ```
   
   Or download ZIP from [GitHub Releases](https://github.com/MrWhosHack/scum-server-manager/releases)

2. **Install Python dependencies**
   ```powershell
   python -m pip install -r requirements.txt
   ```

3. **Launch the manager**
   ```powershell
   python scum_server_manager_pyside.py
   ```
   
   Or double-click `run_scum_pyside.bat` (auto-installs dependencies and requests admin)

### Method 2: One-Click Executable (Portable)

1. **Download the latest release**
   - Visit [GitHub Releases](https://github.com/MrWhosHack/scum-server-manager/releases)
   - Download `SCUM-Server-Manager.exe`

2. **Run the executable**
   - Double-click `SCUM-Server-Manager.exe`
   - If Windows SmartScreen warns, click "More info" → "Run anyway"

### Method 3: Build Your Own Executable

1. **Clone the repository**
   ```powershell
   git clone https://github.com/MrWhosHack/scum-server-manager.git
   cd scum-server-manager
   ```

2. **Run the build script**
   ```powershell
   pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1
   ```
   
   Or double-click `scripts\build_exe.bat`

3. **Find the output**
   - Executable: `dist\SCUM-Server-Manager.exe`

### First-Time Setup

1. **Launch the application** using any method above

2. **Configure server path**:
   - Click "Auto Detect" to automatically find SCUMServer.exe
   - Or manually browse to your server installation (typically in `C:\SteamCMD\steamapps\common\SCUM Dedicated Server\SCUM\Binaries\Win64\SCUMServer.exe`)

3. **Choose a configuration preset** (optional):
   - Open the "Config Editor" tab
   - Select one of 8 ready-made presets from the dropdown
   - Click "Apply Preset"
   - Click "Save Config Files"

4. **Start your server**:
   - Click "Start Server" on the Dashboard or Server tab
   - Grant administrator privileges when prompted
   - Wait for "Server is READY" message

### Firewall Configuration

Ensure these ports are open in Windows Firewall and your router:
- **UDP 7777** - Game port
- **UDP 7778** - Query port
- **TCP 8881** - RCON port (optional, for remote admin)

### Troubleshooting

**"Python not found"**
- Install Python from [python.org](https://www.python.org/downloads/)
- Ensure "Add Python to PATH" is checked during installation
- Restart PowerShell after installation

**"Administrator privileges required"**
- Right-click the executable or BAT file
- Select "Run as administrator"

**"Server won't start"**
- Check that SCUMServer.exe path is correct
- Ensure ports 7777/7778 are not in use
- Review logs in the Logs tab for errors
- Verify SCUM Dedicated Server is properly installed

**"Dependencies missing"**
- Run: `python -m pip install --upgrade pip`
- Run: `python -m pip install -r requirements.txt`

**"Clean rebuild needed"**
- Delete `.venv-build/`, `build/`, and `dist/` folders
- Re-run the build script

### Documentation

- **Getting Started**: [GETTING_STARTED.md](https://github.com/MrWhosHack/scum-server-manager/blob/master/GETTING_STARTED.md)
- **Quick Start Guide**: [QUICK_START_GUIDE.md](https://github.com/MrWhosHack/scum-server-manager/blob/master/QUICK_START_GUIDE.md)
- **Configuration Reference**: [SCUM_CONFIG_GUIDE.md](https://github.com/MrWhosHack/scum-server-manager/blob/master/SCUM_CONFIG_GUIDE.md) (365+ settings)
- **Database Guide**: [SQLITESTUDIO_PRO_GUIDE.md](https://github.com/MrWhosHack/scum-server-manager/blob/master/SQLITESTUDIO_PRO_GUIDE.md)
- **Contributing**: [CONTRIBUTING.md](https://github.com/MrWhosHack/scum-server-manager/blob/master/CONTRIBUTING.md)

### Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/MrWhosHack/scum-server-manager/issues)
- **GitHub Discussions**: [Ask questions or share ideas](https://github.com/MrWhosHack/scum-server-manager/discussions)
- **Official SCUM Discord**: [Join the SCUM community](https://discord.gg/scum)

---

## Additional Links

- **Source Code**: https://github.com/MrWhosHack/scum-server-manager
- **Latest Release**: https://github.com/MrWhosHack/scum-server-manager/releases
- **License**: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)
- **Official SCUM Website**: https://scumgame.com/
- **SCUM on Steam**: https://store.steampowered.com/app/513710/SCUM/
