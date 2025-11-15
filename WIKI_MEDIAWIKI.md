# 🎮 SCUM Server Manager
## Professional GUI-Based Server Administration & Database Management

> **Note:** This page contains MediaWiki-formatted content for https://scum.wiki.gg/wiki/SCUM_Server_Manager  
> For GitHub-friendly documentation, see [README.md](README.md) and [GETTING_STARTED.md](GETTING_STARTED.md)

---

## 📋 Description

**SCUM Server Manager** is the ultimate **all-in-one administration suite** for SCUM dedicated servers, designed to give server owners complete control without the complexity. Built from the ground up with modern **Python and Qt6 technology**, this professional-grade tool transforms server management from a tedious chore into an effortless, streamlined experience.

### What Makes It Special

Gone are the days of manually editing configuration files, searching through endless logs, and juggling multiple tools. SCUM Server Manager consolidates **everything into a single, elegant GUI** that's powerful enough for veterans yet approachable for newcomers. Whether you're running a casual PvE server or a hardcore PvP community, this manager adapts to your needs.

### Complete Server Control

Take command of '''365+ server settings''' spanning every aspect of the SCUM experience:
* Time cycles and weather systems
* Combat mechanics and damage multipliers
* Loot spawns and respawn rates
* Base building and raiding
* Economy and trading systems
* AI behavior and zombie hordes
* Vehicle physics and fuel consumption
* Crafting speeds and blueprints
* And much more...

**Eight expertly crafted presets** let you instantly configure your server for different play styles, while advanced users can fine-tune every parameter for the perfect custom experience.

### Real-Time Intelligence

Monitor your server's heartbeat with:
- **Live player tracking** - Instant connection/disconnection alerts
- **Comprehensive session histories** - Play time, connection patterns, IP tracking
- **SQLite database integration** - Detailed player analytics and inventory data
- **Performance monitoring** - CPU, RAM, and disk usage tracking
- **Multi-category logging** - Separate logs for server, players, admin, and errors

### Professional Features

| Feature | Description |
|---------|-------------|
| **GUI Configuration Editor** | Modify all INI files through an intuitive graphical interface |
| **Database Management** | Built-in SQLiteStudio for advanced player data manipulation |
| **Admin Controls** | Kick, ban, and teleport players with one click (RCON support) |
| **Smart Automation** | Auto-detection of server paths, automatic backups, intelligent log parsing |
| **Modern Dark Theme** | Professional Qt6 interface with smooth animations and responsive design |

---

=== 📦 Technical Information ===

{| class="wikitable"
|-
! Property !! Value
|-
| '''Platform''' || Windows 10/11
|-
| '''Requirements''' || Python 3.8+ (or use standalone EXE)
|-
| '''License''' || [https://creativecommons.org/licenses/by-nc-sa/4.0/ CC BY-NC-SA 4.0]
|-
| '''Repository''' || [https://github.com/MrWhosHack/scum-server-manager GitHub Repository]
|-
| '''Status''' || ✅ Actively maintained and updated
|-
| '''Testing Status''' || ⚠️ Currently in testing phase
|}

---

## ✨ Features

=== 🖥️ Server Management ===

* '''One-Click Start/Stop/Restart''' - Simple server control with automatic admin elevation
* '''Real-Time Status Monitoring''' - Live server state tracking with ready detection
* '''Auto-Detection''' - Automatically finds SCUM server installation paths
* '''SteamCMD Integration''' - Built-in server installation and update capabilities
* '''Background Monitoring''' - Continuous log parsing and event tracking

=== ⚙️ Configuration Editor (365+ Settings) ===

'''Complete INI File Access''' - Edit all server configuration files from one interface:

{| class="wikitable"
|-
! Configuration File !! Settings Count !! Purpose
|-
| ServerSettings.ini || 80+ || Server, network, admin, chat, voice
|-
| Game.ini || 200+ || Gameplay, survival, loot, AI, vehicles, economy
|-
| Engine.ini || 30+ || Rendering, network, performance
|-
| Scalability.ini || 40+ || Quality presets, LOD, effects
|-
| Input.ini || 15+ || Mouse, keyboard, gamepad
|}

'''8 Ready-to-Use Server Presets:'''

{| class="wikitable"
|-
! Preset !! Difficulty !! Loot Rate !! Best For
|-
| '''PvE Casual''' || ⭐ Easy || 2x || New players, relaxed gameplay
|-
| '''PvP Hardcore''' || ⭐⭐⭐⭐⭐ Extreme || 0.5x || Veterans, brutal survival
|-
| '''RP Realism''' || ⭐⭐⭐ Medium || 1x || Immersive roleplay servers
|-
| '''High Action''' || ⭐⭐ Easy-Med || 3x || Fast-paced PvP combat
|-
| '''Performance Optimized''' || ⭐⭐ Medium || 1x || Low-end hardware
|-
| '''Balanced Default''' || ⭐⭐⭐ Medium || 1x || Standard SCUM experience
|-
| '''Survival Expert''' || ⭐⭐⭐⭐ Hard || 0.75x || Challenging PvE
|-
| '''Build & Creative''' || ⭐ Very Easy || 3x || Base building focus
|}

'''Additional Features:'''
* Visual Preset Switcher - Quick configuration switching with one click
* Configuration Backup/Restore - Automatic backup system with restore points
* Live Preview - See setting changes before applying

=== 👥 Player Management ===

* '''Real-Time Player Tracking''' - Live connection/disconnection monitoring
* '''Player Database''' - SQLite database storing player history and statistics
* '''Session Tracking''' - Play time, connection history, IP tracking
* '''Admin Actions''' - Kick, Ban, Teleport (RCON required)
* '''Ban Management''' - Persistent ban list with reasons and timestamps
* '''Player Search & Filtering''' - Filter by online/offline, admin, banned status
* '''Display Name Support''' - Captures real player names from BattlEye logs

=== 🗄️ Database Editor (SQLiteStudio Integration) ===

* '''Easy Database Editing''' - Built-in SQLiteStudio with modern dialogs
* '''Player Data Management''' - Edit player inventories, locations, stats
* '''Item Spawning''' - Add/modify items in player inventories
* '''Location Editing''' - Teleport players, edit coordinates
* '''Advanced SQL Console''' - Direct database queries for power users
* '''Backup System''' - Automatic database backups before modifications

=== 📊 Performance Monitoring ===

* '''System Metrics''' - Real-time CPU, RAM, Disk usage tracking
* '''Server Process Monitoring''' - SCUM server memory and CPU usage
* '''Uptime Tracking''' - Server session duration display
* '''Performance Graphs''' - Visual system resource monitoring
* '''Alert Thresholds''' - Warnings for high resource usage

=== 📝 Logging & Events ===

'''Multi-Category Logging System:'''

{| class="wikitable"
|-
! Log Category !! Contents
|-
| '''Server Logs''' || Startup, shutdown, errors, ready state
|-
| '''Player Logs''' || Connections, disconnections, authentications
|-
| '''Admin Logs''' || Commands, actions, RCON activity
|-
| '''Error Logs''' || Warnings, exceptions, critical errors
|-
| '''Event Logs''' || Airdrops, mechs, server events
|}

'''Features:'''
* Real-Time Log Tailing - Live log file monitoring with auto-scroll
* Log Parsing - Automatic extraction of player events from SCUM server logs
* Color-Coded Output - Easy identification of errors, warnings, info
* Search & Filter - Find specific events quickly

=== 🎨 User Interface ===

* '''Modern Dark Theme''' - Professional Qt6 interface with smooth animations
* '''Tabbed Navigation''' - Dashboard, Players, Player Stats, Server, Config Editor, Logs, Bans, Performance, Settings, Setup
* '''Lazy Loading''' - Fast startup with on-demand tab initialization
* '''Responsive Design''' - Optimized for 1920x1080 and higher resolutions
* '''Keyboard Shortcuts''' - Quick access to common functions
* '''Drag & Drop''' - Easy file and folder selection

---

## 🚀 Installation

=== Prerequisites ===

Before installing, ensure you have:

{| class="wikitable"
|-
! Requirement !! Details
|-
| '''Operating System''' || Windows 10 or Windows 11
|-
| '''Python''' || Version 3.8+ (3.10+ recommended)<br/>Download from [https://www.python.org/downloads/ python.org]<br/>✅ Check "Add Python to PATH" during installation
|-
| '''Administrator Privileges''' || Required for starting the SCUM server
|-
| '''SCUM Dedicated Server''' || Installed via SteamCMD or Steam
|-
| '''Network Ports''' || UDP 7777, UDP 7778, TCP 8881 (RCON)
|}

=== Method 1: Run From Source (Recommended) ===

'''Step 1: Download the project'''

<syntaxhighlight lang="powershell">
git clone https://github.com/MrWhosHack/scum-server-manager.git
cd scum-server-manager
</syntaxhighlight>

Or download ZIP from [https://github.com/MrWhosHack/scum-server-manager/releases GitHub Releases]

'''Step 2: Install Python dependencies'''

<syntaxhighlight lang="powershell">
python -m pip install -r requirements.txt
</syntaxhighlight>

'''Step 3: Launch the manager'''

<syntaxhighlight lang="powershell">
python scum_server_manager_pyside.py
</syntaxhighlight>

Or simply double-click '''run_scum_pyside.bat''' (auto-installs dependencies and requests admin)

=== Method 2: One-Click Executable (Portable) ===

'''Perfect for users who don't want to install Python'''

# Visit [https://github.com/MrWhosHack/scum-server-manager/releases GitHub Releases]
# Download '''SCUM-Server-Manager.exe'''
# Double-click the executable
# If Windows SmartScreen warns, click "More info" → "Run anyway"

'''Note:''' No installation required - the EXE is fully portable!

=== Method 3: Build Your Own Executable ===

'''For advanced users who want to customize the build'''

'''Step 1: Clone the repository'''

<syntaxhighlight lang="powershell">
git clone https://github.com/MrWhosHack/scum-server-manager.git
cd scum-server-manager
</syntaxhighlight>

'''Step 2: Run the build script'''

<syntaxhighlight lang="powershell">
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows_exe.ps1
</syntaxhighlight>

Or double-click '''scripts\build_exe.bat'''

'''Step 3: Find the output'''

Executable location: '''dist\SCUM-Server-Manager.exe'''

---

=== 🎯 First-Time Setup ===

==== Step 1: Launch the Application ====

Use any installation method above to start the manager.

==== Step 2: Configure Server Path ====

* Click '''"Auto Detect"''' to automatically find SCUMServer.exe
* Or manually browse to your server installation
** Typical path: <code>C:\SteamCMD\steamapps\common\SCUM Dedicated Server\SCUM\Binaries\Win64\SCUMServer.exe</code>

==== Step 3: Choose a Configuration Preset (Optional) ====

# Open the '''Config Editor''' tab
# Select one of 8 ready-made presets from the dropdown
# Click '''Apply Preset'''
# Click '''Save Config Files'''

==== Step 4: Start Your Server ====

# Click '''Start Server''' on the Dashboard or Server tab
# Grant administrator privileges when prompted
# Wait for the '''"Server is READY"''' message
# SCUM game client will launch automatically after a 10-second delay

---

=== 🔥 Firewall Configuration ===

'''Critical:''' Ensure these ports are open in Windows Firewall and your router:

{| class="wikitable"
|-
! Port !! Protocol !! Purpose
|-
| '''7777''' || UDP || Game port (required)
|-
| '''7778''' || UDP || Query port (required)
|-
| '''8881''' || TCP || RCON port (optional, for remote admin)
|}

'''Windows Firewall Quick Guide:'''
# Open Windows Defender Firewall
# Click "Advanced Settings"
# Create new Inbound Rules for ports 7777 (UDP), 7778 (UDP), 8881 (TCP)
# Allow the connection for all profiles (Domain, Private, Public)

---

=== 🛠️ Troubleshooting ===

==== "Python not found" ====

* Install Python from [https://www.python.org/downloads/ python.org]
* '''Important:''' Check "Add Python to PATH" during installation
* Restart PowerShell/Command Prompt after installation
* Verify installation: <code>python --version</code>

==== "Administrator privileges required" ====

* Right-click the executable or BAT file
* Select '''"Run as administrator"'''
* Grant permission when UAC prompt appears

==== "Server won't start" ====

* Verify SCUMServer.exe path is correct
* Check ports 7777/7778 are not already in use
* Review logs in the '''Logs''' tab for specific errors
* Ensure SCUM Dedicated Server is properly installed via SteamCMD
* Try running as administrator

==== "Dependencies missing" ====

<syntaxhighlight lang="powershell">
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
</syntaxhighlight>

==== "Clean rebuild needed" ====

# Delete these folders: <code>.venv-build/</code>, <code>build/</code>, <code>dist/</code>
# Re-run the build script

==== "Players not showing up" ====

* Wait 10-30 seconds after player joins for log parsing
* Check that server logs are being generated
* Verify '''Logs''' tab shows player connection events
* Database may need initial scan (automatic on first player)

---

== 📚 Documentation

'''Complete Guides Available:'''

{| class="wikitable"
|-
! Guide !! Description !! Link
|-
| '''Getting Started''' || Quick 5-minute setup guide || [https://github.com/MrWhosHack/scum-server-manager/blob/master/GETTING_STARTED.md Read Guide]
|-
| '''Quick Start''' || Fast setup walkthrough || [https://github.com/MrWhosHack/scum-server-manager/blob/master/QUICK_START_GUIDE.md Read Guide]
|-
| '''Configuration Reference''' || Complete 365+ settings documentation (1,500+ lines) || [https://github.com/MrWhosHack/scum-server-manager/blob/master/SCUM_CONFIG_GUIDE.md Read Guide]
|-
| '''Database Guide''' || SQLiteStudio usage and advanced editing || [https://github.com/MrWhosHack/scum-server-manager/blob/master/SQLITESTUDIO_PRO_GUIDE.md Read Guide]
|-
| '''Contributing''' || How to contribute to the project || [https://github.com/MrWhosHack/scum-server-manager/blob/master/CONTRIBUTING.md Read Guide]
|}

---

== 💬 Support & Community

=== Get Help ===

{| class="wikitable"
|-
! Platform !! Purpose !! Link
|-
| '''GitHub Issues''' || Report bugs or request features || [https://github.com/MrWhosHack/scum-server-manager/issues Submit Issue]
|-
| '''GitHub Discussions''' || Ask questions, share ideas, get help || [https://github.com/MrWhosHack/scum-server-manager/discussions Join Discussion]
|-
| '''Official SCUM Discord''' || Join the SCUM community || [https://discord.gg/scum Join Discord]
|}

=== Developer ===

* '''Author:''' MrWhosHack
* '''GitHub:''' [https://github.com/MrWhosHack MrWhosHack]
* '''Project:''' [https://github.com/MrWhosHack/scum-server-manager scum-server-manager]

---

== 🔗 Additional Links

* '''[https://github.com/MrWhosHack/scum-server-manager Source Code Repository]'''
* '''[https://github.com/MrWhosHack/scum-server-manager/releases Latest Release Downloads]'''
* '''[https://creativecommons.org/licenses/by-nc-sa/4.0/ License: CC BY-NC-SA 4.0]'''
* '''[https://scumgame.com/ Official SCUM Website]'''
* '''[https://store.steampowered.com/app/513710/SCUM/ SCUM on Steam]'''

---

== ⚠️ Development Status

{| class="wikitable"
|-
! Status !! Notes
|-
| '''Testing Phase''' || Currently in active testing - report issues on GitHub
|-
| '''Stability''' || Core features stable, advanced features being refined
|-
| '''Updates''' || Regular updates and bug fixes
|-
| '''Community Driven''' || Open to contributions and feature requests
|}

---

== 📝 License

This project is licensed under the '''Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International''' (CC BY-NC-SA 4.0).

'''What this means:'''
* ✅ Free to use for personal/non-commercial servers
* ✅ Free to modify and share
* ✅ Must give credit to original author
* ❌ Cannot be used commercially without permission
* 🔄 Derivatives must use the same license

Full license: [https://creativecommons.org/licenses/by-nc-sa/4.0/ CC BY-NC-SA 4.0]

---

== 🏆 Credits

* '''Created by:''' MrWhosHack
* '''Built with:''' Python 3, PySide6 (Qt6), psutil, SQLite
* '''Inspired by:''' The SCUM community's need for better server management tools
* '''Special Thanks:''' SCUM development team, Qt framework contributors, and all beta testers

---

[[Category:Modding]]
[[Category:Server Administration]]
[[Category:Third-Party Tools]]
