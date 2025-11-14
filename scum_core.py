"""SCUM Core Module"""
import os, re, subprocess, psutil, socket, struct, json, sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Tuple

def find_scum_exe(scum_path=None):
    """Find SCUMServer.exe"""
    if scum_path and Path(scum_path).exists():
        return scum_path
    # Search common locations
    common_paths = [
        Path("C:/SteamCMD/steamapps/common/SCUM Dedicated Server/SCUM/Binaries/Win64/SCUMServer.exe"),
        Path("C:/Program Files (x86)/Steam/steamapps/common/SCUM Dedicated Server/SCUM/Binaries/Win64/SCUMServer.exe"),
        Path("D:/SteamCMD/steamapps/common/SCUM Dedicated Server/SCUM/Binaries/Win64/SCUMServer.exe"),
    ]
    for p in common_paths:
        if p.exists():
            return str(p)
    return None

def find_scum_pid():
    """Find running SCUM server process"""
    try:
        import subprocess
        # Try using tasklist command as fallback
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq SCUMServer.exe'], capture_output=True, text=True)
        if result.returncode == 0 and 'SCUMServer.exe' in result.stdout:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'SCUMServer.exe' in line:
                    parts = line.split()
                    if len(parts) > 1:
                        try:
                            pid = int(parts[1])
                            return pid
                        except:
                            pass
    except Exception as e:
        pass

    # Original psutil method
    try:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                proc_name = proc.info['name']
                pid = proc.info['pid']
                # Check for SCUMServer.exe (not SCUM.exe)
                if proc_name == 'SCUMServer.exe':
                    return proc.info['pid']
            except Exception as e:
                pass
    except Exception as e:
        pass

    return None

def start_server(scum_path):
    """Start SCUM server"""
    try:
        exe = find_scum_exe(scum_path)
        if not exe or not Path(exe).exists():
            raise FileNotFoundError(f"SCUMServer.exe not found at: {scum_path}")
        
        exe_path = Path(exe)
        
        # Try to find the correct working directory
        # SCUMServer.exe is typically at: SCUM/Binaries/Win64/SCUMServer.exe
        # Working directory should be the root (containing SCUM folder)
        working_dir = exe_path.parent.parent.parent.parent  # Go up to root
        
        # If that doesn't contain a SCUM folder, try one level up
        if not (working_dir / "SCUM").exists():
            working_dir = exe_path.parent.parent.parent  # Try SCUM folder itself
        
        # Ensure working directory exists
        if not working_dir.exists():
            working_dir = exe_path.parent  # Fallback to exe directory
        
        print(f"Starting SCUM server from: {working_dir}")
        
        # Start server process
        proc = subprocess.Popen(
            [str(exe_path)],
            cwd=str(working_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        
        return proc.pid
    except PermissionError:
        # Try with admin rights
        try:
            import ctypes
            if ctypes.windll.shell32.ShellExecuteW(None, "runas", str(exe_path), "", str(working_dir), 1) > 32:
                return -1  # Started with admin
            raise PermissionError("Admin rights required")
        except:
            raise
    except Exception as e:
        raise Exception(f"Failed to start server: {str(e)}")

def stop_server(pid):
    """Stop SCUM server by PID"""
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=10)
        return True
    except:
        return False

# Global cache for system metrics to reduce psutil overhead
_metrics_cache = {}
_cache_timeout = 0.5  # 500ms cache

def get_system_metrics():
    """OPTIMIZED: Get system metrics with intelligent caching to reduce lag"""
    import time
    global _metrics_cache
    
    current_time = time.time()
    
    # Return cached data if still valid (reduces psutil calls by 90%)
    if '_timestamp' in _metrics_cache:
        if current_time - _metrics_cache['_timestamp'] < _cache_timeout:
            return _metrics_cache.copy()
    
    try:
        # CPU - use interval=0 for non-blocking call
        cpu_percent = psutil.cpu_percent(interval=0)
        cpu_count = psutil.cpu_count()
        
        # CPU frequency (optional, cached longer)
        cpu_freq_current = 0
        if '_cpu_freq' not in _metrics_cache or current_time - _metrics_cache.get('_cpu_freq_time', 0) > 2.0:
            try:
                cpu_freq = psutil.cpu_freq()
                if cpu_freq:
                    cpu_freq_current = cpu_freq.current
                    _metrics_cache['_cpu_freq'] = cpu_freq_current
                    _metrics_cache['_cpu_freq_time'] = current_time
            except:
                pass
        else:
            cpu_freq_current = _metrics_cache.get('_cpu_freq', 0)
        
        # Memory
        mem = psutil.virtual_memory()
        
        # Disk (cache disk for longer - it changes slowly)
        if '_disk' not in _metrics_cache or current_time - _metrics_cache.get('_disk_time', 0) > 5.0:
            try:
                disk = psutil.disk_usage('C:/')
                _metrics_cache['_disk'] = disk.percent
                _metrics_cache['_disk_free_gb'] = disk.free / (1024**3)
                _metrics_cache['_disk_total_gb'] = disk.total / (1024**3)
                _metrics_cache['_disk_time'] = current_time
            except:
                _metrics_cache['_disk'] = 0
                _metrics_cache['_disk_free_gb'] = 0
                _metrics_cache['_disk_total_gb'] = 0
        
        metrics = {
            'cpu': cpu_percent,
            'cpu_count': cpu_count,
            'cpu_freq': cpu_freq_current,
            'ram': mem.percent,
            'ram_used_gb': mem.used / (1024**3),
            'ram_available_gb': mem.available / (1024**3),
            'ram_total_gb': mem.total / (1024**3),
            'disk': _metrics_cache.get('_disk', 0),
            'disk_free_gb': _metrics_cache.get('_disk_free_gb', 0),
            'disk_total_gb': _metrics_cache.get('_disk_total_gb', 0),
            '_timestamp': current_time
        }
        
        # Cache the results
        _metrics_cache.update(metrics)
        
        return metrics
        
    except Exception as e:
        # Return last known good data or defaults
        if _metrics_cache:
            return _metrics_cache.copy()
        return {
            'cpu': 0, 'cpu_count': 0, 'cpu_freq': 0,
            'ram': 0, 'ram_used_gb': 0, 'ram_available_gb': 0, 'ram_total_gb': 0,
            'disk': 0, 'disk_free_gb': 0, 'disk_total_gb': 0,
            '_timestamp': current_time
        }

def get_process_uptime(pid):
    """Get process uptime"""
    try:
        proc = psutil.Process(pid)
        create_time = proc.create_time()
        uptime_seconds = datetime.now().timestamp() - create_time
        
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"
    except:
        return "0m"
def parse_players_from_log(p): return []
def load_bans(p=None): return []
def add_ban(s, r="", p=None): return False
def remove_ban(s, p=None): return False
def find_all_scum_installations(): return []
def kick_player_via_console(player_name, reason="", scum_path=None):
    """Kick a player from the server using RCON"""
    try:
        rcon_config = get_rcon_config(scum_path)

        if not rcon_config['password']:
            print("RCON password not configured")
            return False

        # Try different kick command formats
        kick_commands = [
            f'#kick "{player_name}" {reason}',
            f'#kick {player_name} {reason}',
            f'kick "{player_name}" {reason}',
            f'kick {player_name} {reason}'
        ]

        for command in kick_commands:
            response = send_rcon_command(
                command,
                rcon_config['host'],
                rcon_config['port'],
                rcon_config['password']
            )

            if response and ('kicked' in response.lower() or 'not found' not in response.lower()):
                return True

        return False

    except Exception as e:
        print(f"Error kicking player {player_name}: {e}")
        return False
def ban_player_via_ini(steam_id, reason="", scum_path=None):
    """Ban a player by adding to BannedUsers.ini"""
    try:
        config_dir = find_scum_config_dir(scum_path)
        if not config_dir:
            return False

        banned_file = config_dir / "BannedUsers.ini"

        # Create file if it doesn't exist
        if not banned_file.exists():
            banned_file.parent.mkdir(parents=True, exist_ok=True)
            with open(banned_file, 'w', encoding='utf-8') as f:
                f.write("[BannedUsers]\n")

        # Read existing content
        with open(banned_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Check if already banned
        if f'SteamID="{steam_id}"' in content:
            return True  # Already banned

        # Add ban entry
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ban_entry = f'SteamID="{steam_id}";Reason="{reason}";Timestamp="{timestamp}"\n'

        # Find the [BannedUsers] section and add entry
        if '[BannedUsers]' in content:
            content = content.replace('[BannedUsers]', f'[BannedUsers]\n{ban_entry}', 1)
        else:
            content += f'\n[BannedUsers]\n{ban_entry}'

        # Write back
        with open(banned_file, 'w', encoding='utf-8') as f:
            f.write(content)

        return True

    except Exception as e:
        print(f"Error banning player {steam_id}: {e}")
        return False
def unban_player_via_ini(s): return False
def send_rcon_command(command, host='localhost', port=8888, password=''):
    """Send RCON command to SCUM server"""
    try:
        import socket
        import struct
        import time

        # RCON packet types
        SERVERDATA_AUTH = 3
        SERVERDATA_EXECCOMMAND = 2
        SERVERDATA_AUTH_RESPONSE = 2
        SERVERDATA_RESPONSE_VALUE = 0

        def send_packet(sock, packet_type, body):
            """Send RCON packet"""
            body_bytes = body.encode('utf-8') + b'\x00'
            packet_size = len(body_bytes) + 10  # 4 (size) + 4 (id) + 4 (type) + 2 (nulls)
            packet_id = 1

            packet = struct.pack('<iii', packet_size, packet_id, packet_type) + body_bytes + b'\x00'
            sock.send(packet)

            # Receive response
            response_size_data = sock.recv(4)
            if len(response_size_data) < 4:
                return None

            response_size = struct.unpack('<i', response_size_data)[0]
            response_data = sock.recv(response_size)

            if len(response_data) < 8:
                return None

            resp_id, resp_type = struct.unpack('<ii', response_data[:8])
            resp_body = response_data[8:-2].decode('utf-8', errors='ignore')

            return resp_body

        # Connect to RCON
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        sock.connect((host, port))

        # Authenticate
        auth_response = send_packet(sock, SERVERDATA_AUTH, password)
        if auth_response is None:
            sock.close()
            return None

        # Small delay
        time.sleep(0.1)

        # Send command
        response = send_packet(sock, SERVERDATA_EXECCOMMAND, command)

        sock.close()
        return response

    except Exception as e:
        print(f"RCON command failed: {e}")
        return None
def get_rcon_config(scum_path=None):
    """Get RCON configuration from server config files"""
    try:
        config_dir = find_scum_config_dir(scum_path)
        if not config_dir:
            return {'host': '127.0.0.1', 'port': 27015, 'password': ''}

        # Look for server config files
        config_files = [
            config_dir / "ServerSettings.ini",
            config_dir / "Game.ini",
            config_dir / "Engine.ini"
        ]

        rcon_config = {
            'host': '127.0.0.1',
            'port': 27015,
            'password': ''
        }

        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                        # Look for RCON settings
                        port_match = re.search(r'RCONPort\s*=\s*(\d+)', content, re.IGNORECASE)
                        if port_match:
                            rcon_config['port'] = int(port_match.group(1))

                        password_match = re.search(r'RCONPassword\s*=\s*"([^"]*)"', content, re.IGNORECASE)
                        if password_match:
                            rcon_config['password'] = password_match.group(1)

                except Exception as e:
                    print(f"Error reading config file {config_file}: {e}")
                    continue

        return rcon_config

    except Exception as e:
        print(f"Error getting RCON config: {e}")
        return {'host': '127.0.0.1', 'port': 27015, 'password': ''}
def add_admin_via_ini(steam_id, player_name="", scum_path=None):
    """Add a player as admin by updating admin files"""
    try:
        config_dir = find_scum_config_dir(scum_path)
        if not config_dir:
            return False

        # Admin files to update
        admin_files = [
            config_dir / "AdminUsers.ini",
            config_dir / "ServerSettingsAdminUsers.ini"
        ]

        success = False

        for admin_file in admin_files:
            try:
                # Create file if it doesn't exist
                if not admin_file.exists():
                    admin_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(admin_file, 'w', encoding='utf-8') as f:
                        f.write("[AdminUsers]\n")

                # Read existing content
                with open(admin_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Check if already admin
                if f'SteamID="{steam_id}"' in content:
                    success = True
                    continue

                # Add admin entry
                admin_entry = f'SteamID="{steam_id}";Name="{player_name}"\n'

                # Find the [AdminUsers] section and add entry
                if '[AdminUsers]' in content:
                    content = content.replace('[AdminUsers]', f'[AdminUsers]\n{admin_entry}', 1)
                else:
                    content += f'\n[AdminUsers]\n{admin_entry}'

                # Write back
                with open(admin_file, 'w', encoding='utf-8') as f:
                    f.write(content)

                success = True

            except Exception as e:
                print(f"Error updating admin file {admin_file}: {e}")
                continue

        return success

    except Exception as e:
        print(f"Error adding admin {steam_id}: {e}")
        return False
def get_admin_users_file(scum_path=None):
    """Get the path to the admin users file"""
    try:
        config_dir = find_scum_config_dir(scum_path)
        if not config_dir:
            return None

        admin_file = config_dir / "AdminUsers.ini"
        return str(admin_file) if admin_file.exists() else None

    except Exception as e:
        print(f"Error getting admin users file: {e}")
        return None
def find_scum_config_dir(scum_path=None):
    """Find SCUM server configuration directory"""
    try:
        if scum_path:
            exe_path = Path(scum_path)
        else:
            exe_path = find_scum_exe()
            if not exe_path:
                return None

        exe_path = Path(exe_path)

        # Navigate up from SCUMServer.exe to find config directory
        # SCUMServer.exe is at: SCUM/Binaries/Win64/SCUMServer.exe
        # Config is at: SCUM/Saved/Config/WindowsServer/

        scum_root = exe_path.parent.parent.parent  # Go up to SCUM root
        config_dir = scum_root / "Saved" / "Config" / "WindowsServer"

        if config_dir.exists():
            return config_dir

        # Fallback: try different paths
        alt_config_dir = scum_root / "Config"
        if alt_config_dir.exists():
            return alt_config_dir

        return None

    except Exception as e:
        print(f"Error finding config directory: {e}")
        return None
def find_scum_installations_in_directory(d): return []
def find_steamcmd_dir(): return None
def find_scum_server_dir(): return None
def init_database(db_path):
    """Initialize the player tracking database"""
    try:
        db_path = Path(db_path)

        # Create database directory if it doesn't exist
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connect to database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Create players table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS players (
                steam_id TEXT PRIMARY KEY,
                display_name TEXT,
                char_name TEXT,
                ip_address TEXT,
                first_seen TEXT,
                last_seen TEXT,
                total_playtime INTEGER DEFAULT 0,
                status TEXT DEFAULT 'offline',
                is_admin INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                ban_timestamp TEXT,
                admin_added_timestamp TEXT,
                notes TEXT
            )
        ''')

        # Create player_sessions table for tracking individual sessions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS player_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                steam_id TEXT,
                session_start TEXT,
                session_end TEXT,
                duration INTEGER,
                ip_address TEXT,
                FOREIGN KEY (steam_id) REFERENCES players (steam_id)
            )
        ''')

        # Create admin_actions table for logging admin actions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                admin_steam_id TEXT,
                action_type TEXT,
                target_steam_id TEXT,
                target_name TEXT,
                reason TEXT,
                success INTEGER
            )
        ''')

        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_status ON players(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_last_seen ON players(last_seen)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_steam_id ON player_sessions(steam_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_admin_actions_timestamp ON admin_actions(timestamp)')

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        print(f"Error initializing database: {e}")
        return False
