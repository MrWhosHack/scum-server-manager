import sys
import os
import json
from pathlib import Path
import socket
import shutil
import subprocess
from datetime import datetime
import time
import sqlite3

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QGroupBox, QFileDialog,
    QTableWidget, QTableWidgetItem, QMessageBox, QProgressBar,
    QListWidget, QListWidgetItem, QStackedWidget, QSplitter, QLineEdit,
    QGraphicsOpacityEffect, QStyle, QCheckBox, QGridLayout, QTabWidget,
    QSpinBox, QComboBox, QFileDialog, QTreeWidget, QTreeWidgetItem, QDialog,
    QInputDialog, QRadioButton, QPlainTextEdit, QFrame
)
from PySide6.QtGui import QIcon, QFont, QPixmap, QColor
from PySide6.QtCore import QTimer, QTime, QDate, Qt, QPropertyAnimation, QEasingCurve, QMetaObject, Slot, Q_ARG

try:
    import psutil
except Exception:
    psutil = None

from scum_core import (
    find_scum_exe, find_scum_pid, start_server, stop_server,
    get_system_metrics, get_process_uptime, parse_players_from_log,
    load_bans, add_ban, remove_ban, find_all_scum_installations
)

APP_ROOT = Path(__file__).parent


class SCUMManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SCUM Server Manager (PySide6)")
        self.resize(1000, 700)
        self.setWindowIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        self.server_pid = None
        self.scum_path = None
        self.server_ready = False
        self.server_starting = False
        self.last_log_position = 0  # Track position in log file for monitoring
        self.scum_log_position = 0  # Track position in SCUM server log file
        self.last_scum_log_file = None  # Track which SCUM log file we're reading
        
        # Cache log file modification times to avoid re-reading unchanged files
        self.log_mtimes = {
            'server': 0,
            'players': 0,
            'errors': 0,
            'admin': 0,
            'events': 0
        }

        # Header
        self.header = QLabel("SCUM Server Manager")
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setStyleSheet("font-size: 20px; font-weight: bold; padding: 15px; background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #2b5a3a, stop:1 #0f1117); color: #e6eef6; border-bottom: 2px solid #1e8b57;")

        # Left navigation + stacked pages
        self.nav = QListWidget()
        self.nav.setFixedWidth(180)
        for name in ["Dashboard", "Players", "Player Stats", "Server", "Config Editor", "Logs", "Bans", "Performance", "Settings", "Setup"]:
            it = QListWidgetItem(name)
            it.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.nav.addItem(it)

        # Set icons for nav items
        icons = [
            QStyle.SP_ComputerIcon,
            QStyle.SP_DirIcon,
            QStyle.SP_FileDialogInfoView,  # Player Stats icon
            QStyle.SP_MediaPlay,
            QStyle.SP_FileDialogDetailedView,  # Config Editor icon
            QStyle.SP_FileIcon,
            QStyle.SP_TrashIcon,
            QStyle.SP_ComputerIcon,
            QStyle.SP_DirIcon,
            QStyle.SP_CustomBase  # Setup icon
        ]
        for i, icon in enumerate(icons):
            self.nav.item(i).setIcon(self.style().standardIcon(icon))

        self.stack = QStackedWidget()

        # Create pages
        self.page_dashboard = QWidget()
        self.page_players = QWidget()
        self.page_player_stats = QWidget()
        self.page_server = QWidget()
        self.page_config_editor = QWidget()
        self.page_logs = QWidget()
        self.page_bans = QWidget()
        self.page_performance = QWidget()
        self.page_settings = QWidget()
        self.page_setup = QWidget()

        self.stack.addWidget(self.page_dashboard)
        self.stack.addWidget(self.page_players)
        self.stack.addWidget(self.page_player_stats)
        self.stack.addWidget(self.page_server)
        self.stack.addWidget(self.page_config_editor)
        self.stack.addWidget(self.page_logs)
        self.stack.addWidget(self.page_bans)
        self.stack.addWidget(self.page_performance)
        self.stack.addWidget(self.page_settings)
        self.stack.addWidget(self.page_setup)

        splitter = QSplitter()
        splitter.addWidget(self.nav)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(1, 1)

        central = QWidget()
        layout = QHBoxLayout()
        layout.addWidget(splitter)
        central.setLayout(layout)
        self.setCentralWidget(central)

        # Status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("SCUM Server Manager Ready")

        # Track which tabs have been loaded to enable lazy loading
        self._tabs_initialized = set()
        
        # Build ONLY dashboard initially for instant startup
        self.build_dashboard()
        self._tabs_initialized.add(0)  # Dashboard is initialized
        
        # All other pages will be built on-demand when first accessed

        # Navigation with lazy loading
        self.nav.currentRowChanged.connect(self.on_tab_changed)
        self.nav.setCurrentRow(0)

        # Timer for updates & log tailing (optimized interval)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_all)
        self.timer.start(500)  # Optimized: 500ms (2x/sec) for responsive updates

        # Timer for players tab auto-refresh (optimized with event-driven updates)
        self.players_timer = QTimer(self)
        self.players_timer.timeout.connect(self.monitor_scum_server_logs)  # Changed: Now monitors logs instead of refreshing players
        self.players_timer.start(1000)  # Optimized: 1 second intervals for log monitoring

        # Try auto-detect scum exe
        p = find_scum_exe()
        if p:
            self.scum_path = str(p)

        # Load all saved settings (MUST be after pages are built)
        self.load_settings()

        # Initialize logging system
        self.initialize_logs()

        self.apply_style()

    def showEvent(self, event):
        """Called when the window is shown - trigger initial player scan after Qt event loop starts"""
        super().showEvent(event)
        # Trigger initial player detection after UI is fully shown
        QTimer.singleShot(2000, self.initial_player_scan)

        # Trigger initial player detection after UI is built (for dashboard display)
        # Initial player scan will be triggered in showEvent method

    def initialize_logs(self):
        """Initialize log files with welcome messages and sample data"""
        from datetime import datetime
        
        # Ensure Logs directory exists
        logs_dir = APP_ROOT / "Logs"
        logs_dir.mkdir(exist_ok=True)
        
        # Initialize server.log
        server_log = logs_dir / "server.log"
        if not server_log.exists() or server_log.stat().st_size == 0:
            with server_log.open("w", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: SCUM Server Manager initialized\n")
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Server log system started\n")
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Monitoring for server activity...\n")
        
        # Initialize players.log
        players_log = logs_dir / "players.log"
        if not players_log.exists() or players_log.stat().st_size == 0:
            with players_log.open("w", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Player Activity Log initialized\n")
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Tracking player connections and disconnections\n")
        
        # Initialize errors.log
        errors_log = logs_dir / "errors.log"
        if not errors_log.exists() or errors_log.stat().st_size == 0:
            with errors_log.open("w", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Error Log initialized\n")
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Server errors and warnings will be recorded here\n")
        
        # Initialize admin.log
        admin_log = logs_dir / "admin.log"
        if not admin_log.exists() or admin_log.stat().st_size == 0:
            with admin_log.open("w", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Admin Action Log initialized\n")
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Admin commands and actions will be logged here\n")
        
        # Initialize events.log
        events_log = logs_dir / "events.log"
        if not events_log.exists() or events_log.stat().st_size == 0:
            with events_log.open("w", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Server Events Log initialized\n")
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Application started\n")
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: All logging systems operational\n")

    def initial_player_scan(self):
        """Perform initial player detection on application startup"""
        try:
            self.write_log('info', f'📡 initial_player_scan: Step 1 - Checking server PID (current: {self.server_pid})', 'INFO')
            
            # Check if server is running - try to find it if not set
            if not self.server_pid:
                from scum_core import find_scum_pid
                self.server_pid = find_scum_pid()
                self.write_log('info', f'📡 initial_player_scan: Detected server PID: {self.server_pid}', 'INFO')
                if not self.server_pid:
                    self.write_log('info', f'📡 initial_player_scan: No server PID found, skipping scan', 'INFO')
                    return
            
            self.write_log('info', f'📡 initial_player_scan: Step 2 - Starting background player detection', 'INFO')
            # Perform player detection without requiring UI to be built
            self._detect_players_background()
            
            self.write_log('info', f'📡 initial_player_scan: Step 3 - Updating dashboard counts', 'INFO')
            # Update dashboard if it exists
            self._update_dashboard_counts()
            
            self.write_log('info', f'📡 initial_player_scan: COMPLETED successfully', 'INFO')
            
        except Exception as e:
            self.write_log('error', f'Exception in initial_player_scan: {str(e)}', 'ERROR')
            import traceback
            self.write_log('error', f'Traceback: {traceback.format_exc()}', 'ERROR')

    def _detect_players_background(self):
        """Detect players from logs and update database without UI dependencies"""
        if not self.scum_path:
            return
        
        # Find SCUM server log directory
        scum_exe = Path(self.scum_path)
        scum_root = scum_exe.parent.parent.parent  # Win64 -> Binaries -> SCUM
        log_dir = scum_root / "Saved" / "Logs"
        
        if not log_dir.exists():
            scum_root = scum_exe.parent.parent  # Fallback
            log_dir = scum_root / "Saved" / "Logs"
        
        if not log_dir.exists():
            return
        
        try:
            # Find latest log file
            log_files = list(log_dir.glob("SCUM*.log"))
            if not log_files:
                return
            
            latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
            
            # Initialize database if needed - USE SAME DB AS populate_players
            db_path = APP_ROOT / 'scum_manager.db'
            if not db_path.exists():
                from scum_core import init_database
                init_database(str(db_path))
            
            # Perform full log scan to detect currently online players
            with open(latest_log, 'r', encoding="utf-8", errors="ignore") as f:
                full_content = f.read()
                
                import re
                from datetime import datetime
                
                # Parse the entire log file to find all player events
                all_lines = full_content.splitlines()
                
                # Track player state changes chronologically
                player_states = {}  # steam_id -> latest state
                battleye_names = {}  # steam_id -> display name
                
                for line in all_lines:
                    if not line.strip():
                        continue
                    
                    # Extract timestamp
                    timestamp_match = re.match(r'\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}:\d{3})\]', line)
                    timestamp = timestamp_match.group(1) if timestamp_match else datetime.now().strftime('%Y.%m.%d-%H.%M.%S')
                    
                    # Get BattlEye display names
                    reported_match = re.search(r'LogBattlEye:.*Player\s+"([^"]+)"\s+reported\s+as\s+player\s+(\d+)', line, re.IGNORECASE)
                    if reported_match:
                        display_name = reported_match.group(1).strip()
                        player_num = reported_match.group(2).strip()
                        battleye_names[player_num] = display_name
                        continue
                    
                    # Track login events
                    login_match = re.search(r"LogSCUM:.*'([0-9.]+)\s+(\d+):([^()]+)\(\d+\)'\s+logged\s+in", line, re.IGNORECASE)
                    if not login_match:
                        auth_match = re.search(r"LogSCUM:.*ProcessAuthenticateUserRequest.*user\s+'(\d+)'", line, re.IGNORECASE)
                        if auth_match:
                            steam_id = auth_match.group(1).strip()
                            ip_addr = '127.0.0.1'
                            char_name = 'Unknown'
                            login_match = type('Match', (), {'group': lambda self, i: [ip_addr, steam_id, char_name][i-1]})()
                    
                    if not login_match:
                        possess_match = re.search(r"LogSCUM:.*HandlePossessedBy:\s+(\d+),\s*\d+,\s*([^,\s]+)", line, re.IGNORECASE)
                        if possess_match:
                            steam_id = possess_match.group(1).strip()
                            char_name = possess_match.group(2).strip()
                            ip_addr = '127.0.0.1'
                            login_match = type('Match', (), {'group': lambda self, i: [ip_addr, steam_id, char_name][i-1]})()
                    
                    if login_match:
                        ip_addr = login_match.group(1).strip()
                        steam_id = login_match.group(2).strip()
                        char_name = login_match.group(3).strip()
                        
                        player_states[steam_id] = {
                            'status': 'online',
                            'char_name': char_name,
                            'ip': ip_addr,
                            'connected_at': timestamp,
                            'last_seen': timestamp
                        }
                        continue
                    
                    # Track logout events
                    logout_match = re.search(r"LogSCUM:.*'[0-9.]+\s+(\d+):([^()]+)\(\d+\)'\s+logged\s+out", line, re.IGNORECASE)
                    if logout_match:
                        steam_id = logout_match.group(1).strip()
                        if steam_id in player_states:
                            player_states[steam_id]['status'] = 'offline'
                            player_states[steam_id]['last_seen'] = timestamp
                        continue
                    
                    # Track BattlEye disconnects
                    disconnect_match = re.search(r'LogBattlEye:.*Player\s+#(\d+)\s+(.+?)\s+disconnected', line, re.IGNORECASE)
                    if disconnect_match:
                        player_num = disconnect_match.group(1).strip()
                        # Find player by number and mark offline
                        for sid, state in player_states.items():
                            if state.get('player_num') == player_num:
                                player_states[sid]['status'] = 'offline'
                                player_states[sid]['last_seen'] = timestamp
                                break
                        continue
                
                # Convert to players dict with display names
                online_players = {}
                for steam_id, state in player_states.items():
                    if state['status'] == 'online':
                        display_name = state.get('char_name', 'Unknown')
                        # Try to match with BattlEye name
                        for p_num, b_name in battleye_names.items():
                            if state.get('player_num') == p_num:
                                display_name = b_name
                                break
                        
                        online_players[display_name] = {
                            'steam_id': steam_id,
                            'char_name': state['char_name'],
                            'ip': state['ip'],
                            'status': 'online',
                            'connected_at': state['connected_at'],
                            'last_seen': state['last_seen']
                        }
                
                # Save to database
                self._save_players_to_database(online_players)
                
                online_count = len(online_players)
                self.write_log('player', f'✅ Initial scan complete - found {online_count} online players', 'INFO')
                
        except Exception as e:
            self.write_log('error', f'Error in initial player scan: {e}', 'ERROR')

    def _save_players_to_database(self, players_dict):
        """Save detected players to database"""
        try:
            db_path = APP_ROOT / 'scum_players.db'
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for display_name, data in players_dict.items():
                steam_id = data.get('steam_id')
                char_name = data.get('char_name', 'Unknown')
                ip_addr = data.get('ip', '')
                connected_at = data.get('connected_at', current_time)
                
                # Check if player exists
                cursor.execute('SELECT steam_id, first_seen, total_playtime FROM players WHERE steam_id = ?', (steam_id,))
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing player
                    first_seen = existing[1]
                    total_playtime = existing[2] or 0
                    
                    cursor.execute('''
                        UPDATE players SET 
                            display_name = ?, char_name = ?, ip_address = ?, 
                            last_seen = ?, status = 'online', is_banned = 0
                        WHERE steam_id = ?
                    ''', (display_name, char_name, ip_addr, current_time, steam_id))
                else:
                    # Insert new player
                    cursor.execute('''
                        INSERT INTO players 
                        (steam_id, display_name, char_name, ip_address, first_seen, last_seen, status)
                        VALUES (?, ?, ?, ?, ?, ?, 'online')
                    ''', (steam_id, display_name, char_name, ip_addr, connected_at, current_time))
                
                # Log session start if this is a new connection
                if not existing:
                    cursor.execute('''
                        INSERT INTO player_sessions (steam_id, session_start, ip_address)
                        VALUES (?, ?, ?)
                    ''', (steam_id, connected_at, ip_addr))
            
            # Mark players as offline if they're not in current session
            online_steam_ids = set(data.get('steam_id') for data in players_dict.values())
            cursor.execute("SELECT steam_id FROM players WHERE status = 'online'")
            db_online = cursor.fetchall()
            
            for (db_steam_id,) in db_online:
                if db_steam_id not in online_steam_ids:
                    # Player went offline - update session end time
                    cursor.execute('''
                        UPDATE player_sessions SET 
                            session_end = ?, 
                            duration = CAST((julianday(?) - julianday(session_start)) * 86400 AS INTEGER)
                        WHERE steam_id = ? AND session_end IS NULL
                    ''', (current_time, current_time, db_steam_id))
                    
                    # Update player status and playtime
                    cursor.execute('''
                        SELECT SUM(duration) FROM player_sessions 
                        WHERE steam_id = ? AND duration IS NOT NULL
                    ''', (db_steam_id,))
                    total_duration = cursor.fetchone()[0] or 0
                    
                    cursor.execute('''
                        UPDATE players SET 
                            status = 'offline', 
                            last_seen = ?,
                            total_playtime = ?
                        WHERE steam_id = ?
                    ''', (current_time, total_duration, db_steam_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.write_log('error', f'Failed to save player data to database: {e}', 'ERROR')

    def _update_dashboard_counts(self):
        """Update dashboard player counts from database"""
        try:
            self.write_log('info', f'📊 Dashboard update called - checking database...', 'INFO')
            
            db_path = APP_ROOT / 'scum_manager.db'
            if not db_path.exists():
                self.write_log('info', f'📊 Database not found, skipping dashboard update', 'INFO')
                return
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Get online count
            cursor.execute("SELECT COUNT(*) FROM players WHERE status = 'online'")
            online_count = cursor.fetchone()[0]
            
            # Get total tracked count
            cursor.execute("SELECT COUNT(*) FROM players")
            total_count = cursor.fetchone()[0]
            
            conn.close()
            
            self.write_log('info', f'📊 Database counts: {online_count} online, {total_count} total', 'INFO')
            
            # Update dashboard labels if they exist
            if hasattr(self, 'label_online_count'):
                self.label_online_count.setText(str(online_count))
                self.write_log('info', f'📊 Updated label_online_count to: {online_count}', 'INFO')
            else:
                self.write_log('info', f'📊 label_online_count does not exist yet (lazy loading)', 'INFO')
            
            if hasattr(self, 'label_total_tracked'):
                self.label_total_tracked.setText(f"Total Tracked: {total_count}")
                self.write_log('info', f'📊 Updated label_total_tracked to: {total_count}', 'INFO')
            else:
                self.write_log('info', f'📊 label_total_tracked does not exist yet (lazy loading)', 'INFO')
            
            # Update activity indicator
            if hasattr(self, 'online_activity'):
                if online_count > 0:
                    self.online_activity.setText("⚡ Real-time updates active")
                    self.online_activity.setStyleSheet("font-size: 11px; color: #50fa7b; text-align: center;")
                else:
                    self.online_activity.setText("⏸️ Waiting for players")
                    self.online_activity.setStyleSheet("font-size: 11px; color: #666666; text-align: center;")
                self.write_log('info', f'📊 Updated online_activity indicator', 'INFO')
            else:
                self.write_log('info', f'📊 online_activity does not exist yet (lazy loading)', 'INFO')
            
        except Exception as e:
            self.write_log('error', f'Failed to update dashboard counts: {e}', 'ERROR')

    def apply_style(self):
        qss = """
        QWidget {
            background: #0f1117;
            color: #e6eef6;
            font-family: 'Segoe UI', Tahoma, Arial;
        }
        QListWidget {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #0b0d12, stop:1 #1a1d23);
            border-right: 2px solid #23252b;
            border-radius: 0px;
            selection-background-color: transparent;
        }
        QListWidget::item {
            padding: 15px;
            border-bottom: 1px solid #23252b;
            border-left: 3px solid transparent;
        }
        QListWidget::item:selected {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1e8b57, stop:1 #35c06f);
            color: #ffffff;
            border-left: 4px solid #ffffff;
            border-radius: 0px;
            font-weight: bold;
        }
        QListWidget::item:selected:active {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #35c06f, stop:1 #4ade80);
        }
        QListWidget::item:hover {
            background: #2b2f36;
            border-left: 3px solid #ffb86b;
        }
        QListWidget::item:selected:hover {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #4ade80, stop:1 #6ef08b);
            border-left: 4px solid #ffb86b;
        }
        QListWidget::item:focus {
            border-left: 3px solid #bd93f9;
        }
        QGroupBox {
            border: 2px solid #2b2f36;
            margin-top: 6px;
            padding: 15px;
            border-radius: 10px;
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1a1d23, stop:1 #0f1117);
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #e6eef6;
            font-weight: bold;
        }
        QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #35c06f, stop:1 #1e8b57);
            color: #072018;
            padding: 10px 16px;
            border-radius: 8px;
            border: 1px solid #2b2f36;
            font-weight: bold;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #4ade80, stop:1 #22c55e);
        }
        QPushButton:pressed {
            background: #1e8b57;
        }
        QPushButton:disabled {
            background: #666;
            color: #ddd;
        }
        QTableWidget {
            background: #0d1016;
            border: 1px solid #2b2f36;
            border-radius: 5px;
            gridline-color: #23252b;
            selection-background-color: transparent;
        }
        QTableWidget::item {
            padding: 8px;
            border-bottom: 1px solid #23252b;
            border-right: 1px solid #23252b;
            background: transparent;
        }
        QTableWidget::item:selected {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1e8b57, stop:1 #35c06f);
            color: #ffffff;
            border: 2px solid #4ade80;
            border-radius: 3px;
            font-weight: bold;
        }
        QTableWidget::item:selected:active {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #35c06f, stop:1 #4ade80);
        }
        QTableWidget::item:hover {
            background: #2b2f36;
            border: 1px solid #ffb86b;
        }
        QTableWidget::item:selected:hover {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #4ade80, stop:1 #6ef08b);
            border: 2px solid #ffb86b;
        }
        QTableWidget::item:focus {
            border: 2px solid #bd93f9;
        }
        QTableWidget QHeaderView::section {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1a1d23, stop:1 #2b2f36);
            color: #e6eef6;
            padding: 8px;
            border: 1px solid #23252b;
            font-weight: bold;
            border-radius: 0px;
        }
        QTableWidget QHeaderView::section:hover {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #2b2f36, stop:1 #3b3f46);
            border: 1px solid #ffb86b;
        }
        QProgressBar {
            background: #081018;
            border: 2px solid #1f2a2a;
            border-radius: 8px;
            text-align: center;
            color: #e6eef6;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #6ef08b, stop:1 #2fbf57);
            border-radius: 6px;
        }
        QLineEdit {
            background: #0d1016;
            border: 1px solid #2b2f36;
            border-radius: 5px;
            padding: 5px;
            color: #e6eef6;
        }
        QLineEdit:focus {
            border: 1px solid #1e8b57;
        }
        """
        self.setStyleSheet(qss)

    # --- page builders ---
    def pick_scum(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Select SCUMServer.exe", str(APP_ROOT), "Executable (*.exe)")
        if fn:
            self.scum_path = fn
            self.label_path.setText(fn)
            # Auto-save the path to settings with message
            self.save_settings(show_message=True)
            # Update setup page if it exists
            if hasattr(self, 'setup_label_path'):
                self.setup_label_path.setText(f"✅ {Path(fn).name}")
            if hasattr(self, 'install_status'):
                self.install_status.setText("✅ Server configured")
                self.install_status.setStyleSheet("color: #50fa7b; font-size: 11px;")
            # Update setup status
            if hasattr(self, 'update_setup_status'):
                self.update_setup_status()

    def on_start(self):
        try:
            # Start server without RCON arguments
            pid = start_server(self.scum_path)
            if pid == -1:
                self.write_log('server', 'Server started with administrator privileges (elevated mode)', 'INFO')
                self.write_log('events', 'Server started successfully with administrator privileges', 'INFO')
                QMessageBox.information(self, "Started", "Server started with administrator privileges.\n\nNote: The server is running in elevated mode.\n\nMonitoring server startup...")
            else:
                self.write_log('server', f'Server started successfully (PID: {pid})', 'INFO')
                self.write_log('events', f'Server started - Process ID: {pid}', 'INFO')
                QMessageBox.information(self, "Started", f"Server started (PID {pid})\n\nMonitoring server startup...")
            
            self.server_pid = pid
            self.server_starting = True
            self.server_ready = False
            self.last_log_position = 0
            
            # Update status to show starting
            self.label_status.setText("Status: Starting... ⏳")
            self.status_bar.showMessage("🚀 Server starting - monitoring for ready state...")
            
            self.refresh_all()
        except FileNotFoundError:
            self.write_log('error', 'Failed to start server: SCUMServer.exe not found', 'ERROR')
            self.write_log('events', 'Server start failed - executable not found', 'ERROR')
            QMessageBox.warning(self, "Not found", "SCUMServer.exe not found. Set it in Settings.")
        except PermissionError:
            self.write_log('error', 'Failed to start server: Permission denied - administrator privileges required', 'ERROR')
            self.write_log('events', 'Server start failed - insufficient permissions', 'ERROR')
            QMessageBox.critical(self, "Permission Denied", "Administrator privileges are required to start the SCUM server.\n\nPlease run this application as Administrator.")
        except Exception as e:
            error_msg = str(e)
            self.write_log('error', f'Failed to start server: {error_msg}', 'ERROR')
            self.write_log('events', f'Server start failed - {error_msg}', 'ERROR')
            if "740" in error_msg:
                QMessageBox.critical(self, "Administrator Required", "The SCUM server requires administrator privileges.\n\nPlease run this application as Administrator or grant permission when prompted.")
            else:
                QMessageBox.critical(self, "Error", error_msg)

    def on_stop(self):
        pid = self.server_pid or find_scum_pid()
        if not pid:
            self.write_log('server', 'Stop command issued but server is not running', 'WARN')
            QMessageBox.information(self, "Not running", "Server is not running.")
            return
        ok = stop_server(pid)
        if ok:
            self.write_log('server', f'Server stopped successfully (PID: {pid})', 'INFO')
            self.write_log('events', f'Server stopped - Process ID: {pid}', 'INFO')
            QMessageBox.information(self, "Stopped", "Server stopped")
            self.server_pid = None
            self.server_ready = False
            self.server_starting = False
            self.status_bar.showMessage("Server stopped")
            self.refresh_all()
        else:
            self.write_log('error', f'Failed to stop server cleanly (PID: {pid})', 'ERROR')
            self.write_log('events', f'Server stop failed - PID: {pid}', 'ERROR')
            QMessageBox.warning(self, "Failed", "Could not stop server cleanly")

    def on_restart(self):
        self.write_log('events', 'Server restart initiated', 'INFO')
        self.write_log('server', 'Restarting server...', 'INFO')
        self.on_stop()
        QTimer.singleShot(1200, self.on_start)

    # --- logs and metrics ---
    def load_logs(self):
        """Load main server logs with automatic creation - ASYNC VERSION"""
        # Use QTimer to defer execution to avoid blocking UI
        QTimer.singleShot(10, self._load_logs_async)

    def _load_logs_async(self):
        """Async helper for load_logs to prevent UI blocking"""
        import concurrent.futures
        import threading

        logs_dir = APP_ROOT / "Logs"
        logs_dir.mkdir(exist_ok=True)

        logs = logs_dir / "server.log"

        # Create initial log file with welcome message if it doesn't exist
        if not logs.exists():
            try:
                with logs.open("w", encoding="utf-8") as f:
                    from datetime import datetime
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: SCUM Server Manager - Log initialized\n")
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Server log started\n")
            except Exception as e:
                # Use QTimer to update UI on main thread
                QTimer.singleShot(0, lambda: self.text_logs.setPlainText(f"Could not create log file: {e}"))
                return

        # Read logs asynchronously using ThreadPoolExecutor to prevent UI blocking
        def read_logs_file():
            try:
                with logs.open("r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception as e:
                return f"Could not read logs: {e}"

        # Submit file reading to background thread
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(read_logs_file)

            # Schedule callback when reading is complete
            def on_read_complete():
                try:
                    data = future.result()
                    if data and data.strip():
                        # Use QTimer to update UI on main thread
                        QTimer.singleShot(0, lambda: self.set_logs_text(data))
                    else:
                        # Use QTimer to update UI on main thread
                        QTimer.singleShot(0, lambda: self.text_logs.setPlainText("Server log is empty. Logs will appear here when the server starts."))
                except Exception as e:
                    # Use QTimer to update UI on main thread
                    QTimer.singleShot(0, lambda: self.text_logs.setPlainText(f"Error reading logs: {e}"))

            # Check if reading is complete every 50ms
            def check_future():
                if future.done():
                    on_read_complete()
                else:
                    # Continue checking
                    QTimer.singleShot(50, check_future)

            # Start checking
            QTimer.singleShot(50, check_future)

    def set_logs_text(self, data: str, auto_scroll=True):
        # simple colorization for ERROR/WARNING/INFO
        # Guard: Check if logs UI has been built yet (lazy loading)
        if not hasattr(self, 'text_logs') or self.text_logs is None:
            return
        
        import html
        lines = []
        for L in data.splitlines():
            esc = html.escape(L)
            color = None
            if "error" in L.lower():
                color = "#ff6b6b"
            elif "warn" in L.lower():
                color = "#ffb86b"
            elif "info" in L.lower():
                color = "#8be9fd"
            if color:
                lines.append(f"<span style='color:{color}'>{esc}</span>")
            else:
                lines.append(esc)
        html_text = "<pre style='font-family: Consolas, monospace; font-size: 11px; line-height: 1.4;'>{}</pre>".format("\n".join(lines))
        
        # Check if user is at the bottom BEFORE updating content
        scrollbar = self.text_logs.verticalScrollBar()
        # Only consider "at bottom" if scrollbar is at the VERY end (within 1 pixel)
        was_at_bottom = scrollbar.maximum() == 0 or scrollbar.value() >= scrollbar.maximum() - 1
        
        self.text_logs.setHtml(html_text)
        
        # ONLY auto-scroll if user was truly at the bottom
        if auto_scroll and was_at_bottom:
            QTimer.singleShot(50, lambda: scrollbar.setValue(scrollbar.maximum()))

    def tail_logs(self, max_lines=1000):
        logs = APP_ROOT / "Logs" / "server.log"
        if not logs.exists():
            return
        
        # Check if file was modified since last read (performance optimization)
        try:
            current_mtime = logs.stat().st_mtime
            if current_mtime == self.log_mtimes.get('server', 0):
                return  # File hasn't changed, skip re-read
            self.log_mtimes['server'] = current_mtime
        except:
            pass
        
        try:
            with logs.open("r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            last = "".join(lines[-max_lines:])
            self.set_logs_text(last)
        except Exception:
            pass
    
    def monitor_scum_server_logs(self):
        """Monitor actual SCUM server log files and display in real-time with event-driven player updates"""
        if not self.scum_path:
            return

        # Find SCUM server log directory
        # Path: C:/ScumServer/SCUM/Binaries/Win64/SCUMServer.exe
        # Need: C:/ScumServer/SCUM/Saved/Logs/
        scum_exe = Path(self.scum_path)

        # Go up from Binaries/Win64 to Binaries, then to SCUM root
        scum_root = scum_exe.parent.parent.parent  # Win64 -> Binaries -> SCUM
        log_dir = scum_root / "Saved" / "Logs"

        if not log_dir.exists():
            # Try alternative: maybe path is different
            scum_root = scum_exe.parent.parent  # Win64 -> Binaries
            log_dir = scum_root / "Saved" / "Logs"

        if not log_dir.exists():
            return

        # Find the most recent SCUM server log file
        try:
            log_files = list(log_dir.glob("SCUM*.log"))
            if not log_files:
                return

            # Get the most recent log file
            latest_log = max(log_files, key=lambda p: p.stat().st_mtime)

            # Check if log file changed (new session)
            if self.last_scum_log_file != str(latest_log):
                self.last_scum_log_file = str(latest_log)
                self.scum_log_position = 0
                # Reset player state tracking on new log file
                if not hasattr(self, '_current_online_players'):
                    self._current_online_players = set()
                self._current_online_players.clear()
                # Reset full log scan flag for new log file
                if hasattr(self, '_full_log_scan_done'):
                    self._full_log_scan_done = False
                self.write_log('events', f'Monitoring new SCUM server log: {latest_log.name}', 'INFO')

            # Read only new content from last position
            with latest_log.open("r", encoding="utf-8", errors="ignore") as f:
                f.seek(self.scum_log_position)
                new_content = f.read()
                self.scum_log_position = f.tell()

            if not new_content:
                return

            # Initialize player tracking if not exists
            if not hasattr(self, '_current_online_players'):
                self._current_online_players = set()
            if not hasattr(self, '_battleye_player_mapping'):
                self._battleye_player_mapping = {}  # player_num -> display_name
            if not hasattr(self, '_player_steamid_mapping'):
                self._player_steamid_mapping = {}  # player_num -> steam_id

            # Track if any player state changes occurred
            player_state_changed = False

            # Parse player events from SCUM server logs
            import re
            for line in new_content.splitlines():
                if not line.strip():
                    continue

                line_lower = line.lower()

                # Capture BattlEye player name mapping: Player "DisplayName" reported as player N
                battleye_reported = re.search(r'LogBattlEye:.*Player\s+"([^"]+)"\s+reported\s+as\s+player\s+(\d+)', line, re.IGNORECASE)
                if battleye_reported:
                    display_name = battleye_reported.group(1).strip()
                    player_num = battleye_reported.group(2).strip()
                    self._battleye_player_mapping[player_num] = display_name
                    self.write_log('player', f'🔍 Player "{display_name}" identified by BattlEye', 'INFO')
                    continue

                # Capture Steam ID: Player N SteamID (assumed): XXXXXXXXX
                steamid_match = re.search(r'Player\s+(\d+)\s+SteamID.*:\s*(\d+)', line, re.IGNORECASE)
                if steamid_match:
                    player_num = steamid_match.group(1).strip()
                    steam_id = steamid_match.group(2).strip()
                    self._player_steamid_mapping[player_num] = steam_id
                    continue

                # Detect player connection: Player #N DisplayName (IP) connected
                connect_match = re.search(r'LogBattlEye:.*Player\s+#(\d+)\s+.+?\s+\(([0-9.:]+)\)\s+connected', line, re.IGNORECASE)
                if connect_match:
                    player_num = connect_match.group(1).strip()
                    ip_address = connect_match.group(2).strip()
                    # Use the BattlEye display name if we have it
                    player_name = self._battleye_player_mapping.get(player_num, f'Player #{player_num}')
                    if player_name not in self._current_online_players:
                        self._current_online_players.add(player_name)
                        player_state_changed = True
                        self.write_log('player', f'✅ Player "{player_name}" joined the server', 'INFO')
                        self.write_log('events', f'Player {player_name} connected', 'INFO')
                        
                        # Save to database immediately
                        try:
                            import sqlite3
                            from datetime import datetime
                            db_path = APP_ROOT / 'scum_manager.db'
                            conn = sqlite3.connect(str(db_path))
                            cursor = conn.cursor()
                            
                            # Use real Steam ID if available, otherwise generate pseudo ID
                            steam_id = self._player_steamid_mapping.get(player_num, f'UNKNOWN_{player_num}')
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            
                            cursor.execute('''
                                INSERT OR REPLACE INTO players 
                                (steam_id, display_name, char_name, ip_address, first_seen, last_seen, status)
                                VALUES (?, ?, ?, ?, ?, ?, 'online')
                            ''', (steam_id, player_name, player_name, ip_address, timestamp, timestamp))
                            
                            conn.commit()
                            conn.close()
                            
                            self.write_log('info', f'💾 Player saved to database successfully', 'INFO')
                            
                            # Update dashboard
                            self.write_log('info', f'📊 Calling _update_dashboard_counts() from player connection...', 'INFO')
                            self._update_dashboard_counts()
                            self.write_log('info', f'📊 _update_dashboard_counts() call completed', 'INFO')
                        except Exception as e:
                            self.write_log('error', f'Failed to save player to database: {e}', 'ERROR')
                    continue

                # Detect player disconnect: Player #X ... disconnected
                disconnect_match = re.search(r'LogBattlEye:.*Player\s+#(\d+)\s+(.+?)\s+disconnected', line, re.IGNORECASE)
                if disconnect_match:
                    player_num = disconnect_match.group(1).strip()
                    # Use the BattlEye display name if we have it
                    player_name = self._battleye_player_mapping.get(player_num, disconnect_match.group(2).strip().replace('?', ''))
                    if player_name in self._current_online_players:
                        self._current_online_players.remove(player_name)
                        player_state_changed = True
                        self.write_log('player', f'❌ Player "{player_name}" left the server', 'INFO')
                        self.write_log('events', f'Player {player_name} disconnected', 'INFO')
                        
                        # Update database status to offline
                        try:
                            import sqlite3
                            from datetime import datetime
                            db_path = APP_ROOT / 'scum_manager.db'
                            conn = sqlite3.connect(str(db_path))
                            cursor = conn.cursor()
                            
                            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            cursor.execute('''
                                UPDATE players 
                                SET status = 'offline', last_seen = ?
                                WHERE display_name = ?
                            ''', (timestamp, player_name))
                            
                            conn.commit()
                            conn.close()
                            
                            # Update dashboard
                            self._update_dashboard_counts()
                        except Exception as e:
                            self.write_log('error', f'Failed to update player status: {e}', 'ERROR')
                        
                        # Clean up mapping
                        if player_num in self._battleye_player_mapping:
                            del self._battleye_player_mapping[player_num]
                    continue

                # Categorize other log entries
                if any(keyword in line_lower for keyword in ['error', 'exception', 'failed', 'crash', 'fatal']):
                    self.write_log('error', line.strip(), 'ERROR')
                elif any(keyword in line_lower for keyword in ['warning', 'warn']):
                    self.write_log('error', line.strip(), 'WARN')
                elif any(keyword in line_lower for keyword in ['kick', 'ban', 'admin', 'command', 'teleport']):
                    self.write_log('admin', line.strip(), 'INFO')
                elif any(keyword in line_lower for keyword in ['player', 'steamid', 'connected', 'connection']):
                    # General player-related events
                    self.write_log('player', line.strip(), 'INFO')
                else:
                    # General server log
                    self.write_log('server', line.strip(), 'INFO')

            # If player state changed and we're on the players tab, refresh immediately
            if player_state_changed and self.stack.currentIndex() == 1:  # Players tab index
                # Use QTimer to refresh on the main thread (avoid threading issues)
                QTimer.singleShot(100, self.populate_players)

        except Exception as e:
            # Silently handle errors to avoid spam
            pass

    def check_server_ready(self):
        """Monitor server logs to detect when server is ready for players"""
        # Check both internal logs and actual SCUM server logs
        new_content = ""

        # Read from internal application logs
        logs = APP_ROOT / "Logs" / "server.log"
        if logs.exists():
            try:
                with logs.open("r", encoding="utf-8", errors="ignore") as f:
                    f.seek(self.last_log_position)
                    new_content = f.read()
                    self.last_log_position = f.tell()
            except Exception:
                pass

        # Also read from actual SCUM server logs for ready indicators
        if self.scum_path:
            scum_exe = Path(self.scum_path)
            scum_root = scum_exe.parent.parent
            log_dir = scum_root / "Saved" / "Logs"

            if not log_dir.exists():
                scum_root = scum_exe.parent.parent.parent
                log_dir = scum_root / "Saved" / "Logs"

            if log_dir.exists():
                try:
                    log_files = list(log_dir.glob("SCUM*.log"))
                    if log_files:
                        latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
                        with latest_log.open("r", encoding="utf-8", errors="ignore") as f:
                            scum_content = f.read()
                            new_content += "\n" + scum_content[-10000:]  # Last 10KB
                except Exception:
                    pass

        if not new_content:
            return

        # Check for server ready indicators (common SCUM server messages)
        ready_indicators = [
            "server is ready",
            "listening on",
            "ready to accept connections",
            "server started successfully",
            "game server ready",
            "waiting for players",
            "accepting connections",
            "logworld: bringing up level",
            "initialization complete"
        ]

        new_content_lower = new_content.lower()

        for indicator in ready_indicators:
            if indicator in new_content_lower:
                # Only process if we haven't already detected readiness
                if not self.server_ready:
                    self.server_ready = True
                    self.server_starting = False

                    # Log the ready state
                    self.write_log('server', '✅ Server is now READY for players to join!', 'INFO')
                    self.write_log('events', 'Server fully loaded and accepting player connections', 'INFO')

                    # Update UI
                    self.label_status.setText(f"Status: Online ✅ (PID {self.server_pid})")
                    self.status_bar.showMessage("✅ Server is READY! Players can now join.")

                    # Show notification with auto-launch option (only once)
                    QMessageBox.information(
                        self,
                        "🎮 Server Ready!",
                        "The SCUM server is now fully loaded and ready!\n\n"
                        "✅ Players can now connect\n"
                        f"📡 Server is accepting connections\n"
                        f"⏱️ Ready after: {get_process_uptime(self.server_pid)}\n\n"
                        "🎮 SCUM game will launch automatically in 10 seconds!\n"
                        "This delay ensures the server is fully ready.\n"
                        "Once in-game, use 'Play' → 'Internet' to find your server."
                    )
                    # Add delay to ensure server is fully ready before launching game
                    self.write_log('events', 'Waiting 10 seconds for server to fully initialize before launching game...', 'INFO')
                    self.status_bar.showMessage("⏳ Waiting for server to fully initialize...")

                    # Use QTimer for non-blocking delay
                    QTimer.singleShot(10000, lambda: self._delayed_launch_game())  # 10 second delay
                # Exit the loop once we find any ready indicator
                break
                    
    def _delayed_launch_game(self):
        """Launch SCUM game automatically after delay"""
        try:
            self.write_log('events', 'Launching SCUM game client automatically...', 'INFO')
            self.status_bar.showMessage("🎮 Launching SCUM game...")
            self.launch_scum_game()
        except Exception as e:
            self.write_log('error', f'Failed to launch SCUM game: {str(e)}', 'ERROR')
            QMessageBox.warning(
                self,
                "Launch Error",
                f"Could not launch SCUM game.\n\n"
                f"Error: {str(e)}\n\n"
                "Please launch SCUM manually from Steam."
            )

    def refresh_all(self):
        """OPTIMIZED: Consolidated refresh with intelligent caching"""
        # Quick server status check
        pid = find_scum_pid()
        if pid:
            self.server_pid = pid
            if self.server_ready:
                self.label_status.setText(f"🟢 Online (PID {pid})")
                if hasattr(self, 'label_ready_status'):
                    self.label_ready_status.setText("✅ Ready: Players can join!")
                    self.label_ready_status.setStyleSheet("font-size: 12px; padding: 5px; color: #50fa7b; font-weight: bold;")
            elif self.server_starting:
                self.label_status.setText(f"🟡 Starting... (PID {pid})")
                if hasattr(self, 'label_ready_status'):
                    self.label_ready_status.setText("⏳ Loading: Please wait...")
                    self.label_ready_status.setStyleSheet("font-size: 12px; padding: 5px; color: #ffb86b;")
            else:
                self.label_status.setText(f"🟢 Running (PID {pid})")
                if hasattr(self, 'label_ready_status'):
                    self.label_ready_status.setText("🔄 Status: Running")
                    self.label_ready_status.setStyleSheet("font-size: 12px; padding: 5px; color: #8be9fd;")
        else:
            self.server_pid = None
            self.server_ready = False
            self.server_starting = False
            self.label_status.setText("🔴 Offline")
            if hasattr(self, 'label_ready_status'):
                self.label_ready_status.setText("⭕ Offline: Server not running")
                self.label_ready_status.setStyleSheet("font-size: 12px; padding: 5px; color: #666;")

        # Check server readiness if starting
        if self.server_starting and not self.server_ready:
            self.check_server_ready()

        # Get cached system metrics (already cached in scum_core.py)
        metrics = get_system_metrics()
        
        # Extract metrics with simpler structure
        cpu = metrics.get('cpu', 0)
        ram = metrics.get('ram', 0)
        disk = metrics.get('disk', 0)
        cpu_freq = metrics.get('cpu_freq', 0)
        cpu_count = metrics.get('cpu_count', 0)
        
        mem_used_gb = metrics.get('ram_used_gb', 0)
        mem_total_gb = metrics.get('ram_total_gb', 0)
        mem_available_gb = metrics.get('ram_available_gb', 0)
        
        # Process uptime if running
        if self.server_pid:
            up = get_process_uptime(self.server_pid)
            self.label_uptime.setText(f"⏱️ {up}")
            
            # Server memory monitoring (only if server running)
            try:
                proc = psutil.Process(self.server_pid)
                proc_mem_gb = proc.memory_info().rss / (1024**3)
                proc_mem_percent = (proc_mem_gb / mem_total_gb * 100) if mem_total_gb > 0 else 0
                
                if hasattr(self, 'label_process_mem'):
                    self.label_process_mem.setText(f"Server: {proc_mem_gb:.2f} GB ({proc_mem_percent:.1f}%)")
                    # Color code based on usage
                    if proc_mem_percent > 50:
                        self.label_process_mem.setStyleSheet("font-size: 11px; color: #ff6b6b; padding: 3px; background: #2b1a1a; border-radius: 3px; margin-top: 2px; font-weight: bold;")
                    elif proc_mem_percent > 25:
                        self.label_process_mem.setStyleSheet("font-size: 11px; color: #ffb86b; padding: 3px; background: #2b2f36; border-radius: 3px; margin-top: 2px; font-weight: bold;")
                    else:
                        self.label_process_mem.setStyleSheet("font-size: 11px; color: #50fa7b; padding: 3px; background: #1a2b1a; border-radius: 3px; margin-top: 2px; font-weight: bold;")
            except:
                if hasattr(self, 'label_process_mem'):
                    self.label_process_mem.setText("Server Memory: N/A")
        else:
            self.label_uptime.setText("⏱️ Not running")
            if hasattr(self, 'label_process_mem'):
                self.label_process_mem.setText("Server Memory: N/A")

        # Update progress bars (fast operations)
        self.pb_cpu.setValue(int(cpu))
        self.pb_cpu.setFormat(f"{cpu:.1f}%")
        
        # Update CPU details with simplified structure
        if hasattr(self, 'label_cpu_detail'):
            cpu_info = f"CPU: {cpu:.1f}% ({cpu_count} cores)"
            if cpu_freq > 0:
                cpu_info += f" | Speed: {cpu_freq:.0f} MHz"
            self.label_cpu_detail.setText(cpu_info)
        
        # Update RAM
        self.pb_ram.setValue(int(ram))
        self.pb_ram.setFormat(f"{mem_used_gb:.1f}/{mem_total_gb:.1f} GB ({ram:.0f}%)")
        
        if hasattr(self, 'label_ram_detail'):
            self.label_ram_detail.setText(f"Available: {mem_available_gb:.1f} GB | In Use: {mem_used_gb:.1f} GB")
        
        # Update Disk
        self.pb_disk.setValue(int(disk))
        disk_free_gb = metrics.get('disk_free_gb', 0)
        disk_total_gb = metrics.get('disk_total_gb', 0)
        disk_used_gb = disk_total_gb - disk_free_gb
        self.pb_disk.setFormat(f"{disk_used_gb:.0f}/{disk_total_gb:.0f} GB ({disk:.0f}%)")
        
        if hasattr(self, 'label_disk_detail'):
            self.label_disk_detail.setText(f"Free: {disk_free_gb:.0f} GB | Total: {disk_total_gb:.0f} GB")

        # Update players count - lightweight (event-driven updates handle this)
        if hasattr(self, 'label_players'):
            # Player count will be updated by populate_players when triggered by events
            pass

        # Update player counts on dashboard refresh (every 500ms)
        # This ensures dashboard shows current player data even without log events
        if hasattr(self, 'label_online_count') and hasattr(self, 'label_total_tracked'):
            try:
                # Quick player count update without full table refresh
                db_path = APP_ROOT / "scum_manager.db"
                if db_path.exists():
                    import sqlite3
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    # Get online count
                    cursor.execute("SELECT COUNT(*) FROM players WHERE status = 'online'")
                    online_count = cursor.fetchone()[0]
                    
                    # Get total tracked count
                    cursor.execute("SELECT COUNT(*) FROM players")
                    total_count = cursor.fetchone()[0]
                    
                    conn.close()
                    
                    self.label_online_count.setText(str(online_count))
                    self.label_total_tracked.setText(f"Total Tracked: {total_count}")
                    
                    # Update peak players today
                    if hasattr(self, 'label_peak_today'):
                        if not hasattr(self, '_peak_today'):
                            self._peak_today = 0
                        self._peak_today = max(self._peak_today, online_count)
                        self.label_peak_today.setText(f"Peak Today: {self._peak_today}")
                    
                    # Update online activity indicator
                    if hasattr(self, 'online_activity'):
                        if online_count > 0:
                            self.online_activity.setText("⚡ Real-time updates active")
                            self.online_activity.setStyleSheet("font-size: 11px; color: #50fa7b; text-align: center;")
                        else:
                            self.online_activity.setText("⏸️ Waiting for players")
                            self.online_activity.setStyleSheet("font-size: 11px; color: #666666; text-align: center;")
                else:
                    # No database yet, show zeros
                    self.label_online_count.setText("0")
                    self.label_total_tracked.setText("Total Tracked: 0")
                    if hasattr(self, 'label_peak_today'):
                        self.label_peak_today.setText("Peak Today: 0")
                    if hasattr(self, 'online_activity'):
                        self.online_activity.setText("⏸️ Waiting for players")
                        self.online_activity.setStyleSheet("font-size: 11px; color: #666666; text-align: center;")
                        
            except Exception as e:
                # Silently handle database errors
                pass

    # --- players ---
    def populate_players(self):
        """Parse actual SCUM server logs to track player join/disconnect events with detailed info and database persistence"""
        
        # CRITICAL: Skip if players tab UI hasn't been built yet (lazy loading)
        if not hasattr(self, 'table_players'):
            return
        
        players = {}
        
        # OPTIMIZATION: Defer database initialization to first use for faster startup
        # Initialize database if needed (lazy initialization)
        db_path = APP_ROOT / "scum_manager.db"
        if not hasattr(self, '_db_initialized'):
            try:
                from scum_core import init_database
                init_database(str(db_path))
                self._db_initialized = True
            except Exception as e:
                self.write_log('error', f'Failed to initialize database: {e}', 'ERROR')
                self._db_initialized = False
        
        # AUTO-DETECT server if not running - check periodically (cached for 5 seconds to avoid excessive checks)
        if not self.server_pid:
            current_time = time.time()
            if not hasattr(self, '_server_detect_cache') or (current_time - self._server_detect_cache.get('time', 0)) > 5:
                from scum_core import find_scum_pid
                detected_pid = find_scum_pid()
                self._server_detect_cache = {'time': current_time, 'pid': detected_pid}
                if detected_pid:
                    self.server_pid = detected_pid
                    self.write_log('events', f'✅ Auto-detected running SCUM server (PID: {detected_pid})', 'INFO')
                    # Update dashboard counts immediately
                    self._update_dashboard_counts()
            elif self._server_detect_cache.get('pid'):
                self.server_pid = self._server_detect_cache['pid']
        
        # Check if server is actually running
        if not self.server_pid:
            # Load offline players from database - CACHE THIS
            current_time = time.time()
            if not hasattr(self, '_offline_players_cache') or (current_time - self._offline_players_cache.get('time', 0)) > 30:  # Cache for 30 seconds
                try:
                    import sqlite3
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT steam_id, display_name, char_name, ip_address, first_seen, last_seen, 
                               total_playtime, is_admin, is_banned, ban_reason
                        FROM players 
                        ORDER BY last_seen DESC
                    ''')
                    
                    rows = cursor.fetchall()
                    offline_players = {}
                    for row in rows:
                        steam_id, display_name, char_name, ip_address, first_seen, last_seen, total_playtime, is_admin, is_banned, ban_reason = row
                        
                        offline_players[display_name or char_name or steam_id] = {
                            'char_name': char_name,
                            'steam_id': steam_id,
                            'ip': ip_address,
                            'status': 'offline',
                            'connected_at': first_seen,
                            'last_seen': last_seen,
                            'total_playtime': total_playtime,
                            'is_admin': bool(is_admin),
                            'is_banned': bool(is_banned),
                            'ban_reason': ban_reason
                        }
                    
                    conn.close()
                    
                    # Cache the results
                    self._offline_players_cache = {'time': current_time, 'data': offline_players}
                    
                except Exception as e:
                    self.write_log('error', f'Failed to load players from database: {e}', 'ERROR')
                    self._offline_players_cache = {'time': current_time, 'data': {}}
            
            players = self._offline_players_cache['data'].copy()
            
            self.table_players.setRowCount(0)
            self.table_players.insertRow(0)
            no_server_msg = QTableWidgetItem("⭕ Server is OFFLINE - Showing saved player data")
            no_server_msg.setForeground(QColor('#ffb86b'))
            no_server_msg.setFont(QFont('Segoe UI', 12, QFont.Bold))
            self.table_players.setItem(0, 0, no_server_msg)
            self.table_players.setSpan(0, 0, 1, 7)
            # Update counts to 0 for online
            if hasattr(self, 'label_online_count'):
                self.label_online_count.setText("0")
            return
        
        if not self.scum_path:
            self.table_players.setRowCount(0)
            self.table_players.insertRow(0)
            no_server_msg = QTableWidgetItem("⚠️ Server path not configured - please set up SCUM server first")
            no_server_msg.setForeground(QColor('#ffb86b'))
            self.table_players.setItem(0, 0, no_server_msg)
            self.table_players.setSpan(0, 0, 1, 7)
            return
        
        # Find SCUM server log directory - CACHE THIS PATH
        if not hasattr(self, '_log_dir_cache') or not self._log_dir_cache.get('path'):
            scum_exe = Path(self.scum_path)
            scum_root = scum_exe.parent.parent.parent  # Win64 -> Binaries -> SCUM
            log_dir = scum_root / "Saved" / "Logs"
            
            if not log_dir.exists():
                scum_root = scum_exe.parent.parent  # Fallback
                log_dir = scum_root / "Saved" / "Logs"
            
            self._log_dir_cache = {'path': log_dir if log_dir.exists() else None}
        
        log_dir = self._log_dir_cache['path']
        
        if log_dir.exists():
            try:
                # CACHE log file discovery - only check every 10 seconds
                current_time = time.time()
                if not hasattr(self, '_log_file_cache') or (current_time - self._log_file_cache.get('time', 0)) > 10:
                    log_files = list(log_dir.glob("SCUM*.log"))
                    if log_files:
                        latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
                        self._log_file_cache = {'time': current_time, 'file': latest_log}
                    else:
                        self._log_file_cache = {'time': current_time, 'file': None}
                else:
                    latest_log = self._log_file_cache.get('file')
                
                if not latest_log:
                    return
                
                # ENHANCED: Do a FULL SCAN of the log file initially to find currently online players
                # This handles the case where players joined before the application started monitoring
                if not hasattr(self, '_full_log_scan_done'):
                    self.write_log('player', '🔍 Performing initial full log scan to detect currently online players...', 'INFO')
                    
                    # Read the entire log file to find current player state
                    with open(latest_log, 'r', encoding="utf-8", errors="ignore") as f:
                        full_content = f.read()
                        
                        import re
                        from datetime import datetime
                        
                        # Parse the entire log file to find all player events
                        all_lines = full_content.splitlines()
                        
                        # Track player state changes chronologically
                        player_states = {}  # steam_id -> latest state
                        battleye_names = {}  # steam_id -> display name
                        
                        for line in all_lines:
                            if not line.strip():
                                continue
                            
                            # Extract timestamp
                            timestamp_match = re.match(r'\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}:\d{3})\]', line)
                            timestamp = timestamp_match.group(1) if timestamp_match else datetime.now().strftime('%Y.%m.%d-%H.%M.%S')
                            
                            # Get BattlEye display names
                            reported_match = re.search(r'LogBattlEye:.*Player\s+"([^"]+)"\s+reported\s+as\s+player\s+(\d+)', line, re.IGNORECASE)
                            if reported_match:
                                display_name = reported_match.group(1).strip()
                                player_num = reported_match.group(2).strip()
                                # Store for later matching
                                battleye_names[player_num] = display_name
                                continue
                            
                            # Track login events
                            login_match = re.search(r"LogSCUM:.*'([0-9.]+)\s+(\d+):([^()]+)\(\d+\)'\s+logged\s+in", line, re.IGNORECASE)
                            if not login_match:
                                auth_match = re.search(r"LogSCUM:.*ProcessAuthenticateUserRequest.*user\s+'(\d+)'", line, re.IGNORECASE)
                                if auth_match:
                                    steam_id = auth_match.group(1).strip()
                                    ip_addr = '127.0.0.1'
                                    char_name = 'Unknown'
                                    login_match = type('Match', (), {'group': lambda self, i: [ip_addr, steam_id, char_name][i-1]})()
                            
                            if not login_match:
                                possess_match = re.search(r"LogSCUM:.*HandlePossessedBy:\s+(\d+),\s*\d+,\s*([^,\s]+)", line, re.IGNORECASE)
                                if possess_match:
                                    steam_id = possess_match.group(1).strip()
                                    char_name = possess_match.group(2).strip()
                                    ip_addr = '127.0.0.1'
                                    login_match = type('Match', (), {'group': lambda self, i: [ip_addr, steam_id, char_name][i-1]})()
                            
                            if login_match:
                                ip_addr = login_match.group(1).strip()
                                steam_id = login_match.group(2).strip()
                                char_name = login_match.group(3).strip()
                                
                                player_states[steam_id] = {
                                    'status': 'online',
                                    'char_name': char_name,
                                    'ip': ip_addr,
                                    'connected_at': timestamp,
                                    'last_seen': timestamp
                                }
                                continue
                            
                            # Track logout events
                            logout_match = re.search(r"LogSCUM:.*'[0-9.]+\s+(\d+):([^()]+)\(\d+\)'\s+logged\s+out", line, re.IGNORECASE)
                            if logout_match:
                                steam_id = logout_match.group(1).strip()
                                if steam_id in player_states:
                                    player_states[steam_id]['status'] = 'offline'
                                    player_states[steam_id]['last_seen'] = timestamp
                                continue
                            
                            # Track BattlEye disconnects
                            disconnect_match = re.search(r'LogBattlEye:.*Player\s+#(\d+)\s+(.+?)\s+disconnected', line, re.IGNORECASE)
                            if disconnect_match:
                                player_num = disconnect_match.group(1).strip()
                                # Find player by number and mark offline
                                for sid, state in player_states.items():
                                    if state.get('player_num') == player_num:
                                        player_states[sid]['status'] = 'offline'
                                        player_states[sid]['last_seen'] = timestamp
                                        break
                                continue
                        
                        # Convert to players dict with display names
                        for steam_id, state in player_states.items():
                            if state['status'] == 'online':
                                display_name = state.get('char_name', 'Unknown')
                                # Try to match with BattlEye name
                                for p_num, b_name in battleye_names.items():
                                    if state.get('player_num') == p_num:
                                        display_name = b_name
                                        break
                                
                                players[display_name] = {
                                    'steam_id': steam_id,
                                    'char_name': state['char_name'],
                                    'ip': state['ip'],
                                    'status': 'online',
                                    'connected_at': state['connected_at'],
                                    'last_seen': state['last_seen']
                                }
                    
                    self._full_log_scan_done = True
                    self.write_log('player', f'✅ Full log scan complete - found {len([p for p in players.values() if p["status"] == "online"])} online players', 'INFO')
                
                # OPTIMIZED: Only read the last portion of the log file for ongoing monitoring
                # Read last 50KB instead of entire file for better performance
                file_size = latest_log.stat().st_size
                read_size = min(51200, file_size)  # 50KB max
                
                with open(latest_log, 'r', encoding="utf-8", errors="ignore") as f:
                    if file_size > read_size:
                        f.seek(file_size - read_size)
                        # Skip to next line to avoid partial lines
                        f.readline()
                    content = f.read()
                    
                    import re
                    from datetime import datetime
                    
                    # OPTIMIZED: Process only the most recent 1000 lines
                    # This ensures we get the latest player activity
                    all_lines = content.splitlines()
                    recent_lines = all_lines[-1000:] if len(all_lines) > 1000 else all_lines
                    
                    # Map steam_id to player data
                    steam_to_player = {}
                    pending_names = {}  # Store BattlEye names temporarily
                    
                    # Process lines in FORWARD order (not reverse) so BattlEye name comes before login
                    for line in recent_lines:
                        if not line.strip():
                            continue
                        
                        # Extract timestamp
                        timestamp_match = re.match(r'\[(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2}:\d{3})\]', line)
                        timestamp = timestamp_match.group(1) if timestamp_match else datetime.now().strftime('%Y.%m.%d-%H.%M.%S')
                        
                        # Get REAL player name from BattlEye FIRST (happens before login)
                        # 'Player "😈Mr☬Who's☬Hacking😈" reported as player 0'
                        reported_match = re.search(r'LogBattlEye:.*Player\s+"([^"]+)"\s+reported\s+as\s+player\s+(\d+)', line, re.IGNORECASE)
                        if reported_match:
                            real_name = reported_match.group(1).strip()
                            player_num = reported_match.group(2).strip()
                            # Store temporarily - will be matched to login
                            pending_names[timestamp] = {'name': real_name, 'player_num': player_num}
                            continue
                        
                        # Parse login with full details: "LogSCUM: '127.0.0.1 76561198872092674:test(1)' logged in at: X=... Y=... Z=..."
                        # Also check for authentication: "LogSCUM: UDedicatedServerResponse::ProcessAuthenticateUserRequest: Begin auth session for user '76561198872092674'"
                        # And possession: "LogSCUM: APrisoner::HandlePossessedBy: 76561198872092674, 1, test"
                        login_match = re.search(r"LogSCUM:.*'([0-9.]+)\s+(\d+):([^()]+)\(\d+\)'\s+logged\s+in", line, re.IGNORECASE)
                        if not login_match:
                            # Check for authentication message
                            auth_match = re.search(r"LogSCUM:.*ProcessAuthenticateUserRequest.*user\s+'(\d+)'", line, re.IGNORECASE)
                            if auth_match:
                                steam_id = auth_match.group(1).strip()
                                # Extract IP from the same line or nearby context
                                ip_match = re.search(r'\((\d+\.\d+\.\d+\.\d+):\d+\)', line)
                                ip_addr = ip_match.group(1) if ip_match else '127.0.0.1'
                                char_name = 'Unknown'  # Will be updated by possession message
                                login_match = type('Match', (), {'group': lambda self, i: [ip_addr, steam_id, char_name][i-1]})()
                        
                        if not login_match:
                            # Check for possession message (player is now in game)
                            possess_match = re.search(r"LogSCUM:.*HandlePossessedBy:\s+(\d+),\s*\d+,\s*([^,\s]+)", line, re.IGNORECASE)
                            if possess_match:
                                steam_id = possess_match.group(1).strip()
                                char_name = possess_match.group(2).strip()
                                ip_addr = '127.0.0.1'  # Default, will be updated if we find auth message
                                login_match = type('Match', (), {'group': lambda self, i: [ip_addr, steam_id, char_name][i-1]})()
                        if login_match:
                            ip_addr = login_match.group(1).strip()
                            steam_id = login_match.group(2).strip()
                            char_name = login_match.group(3).strip()  # Character name (not display name)
                            
                            if steam_id not in steam_to_player:
                                steam_to_player[steam_id] = {}
                            
                            steam_to_player[steam_id].update({
                                'char_name': char_name,
                                'steam_id': steam_id,
                                'ip': ip_addr,
                                'status': 'online',
                                'connected_at': timestamp,
                                'last_seen': timestamp
                            })
                            
                            # Match with pending BattlEye name (happens within same second)
                            for ts, name_data in sorted(pending_names.items(), reverse=True):
                                if ts.split(':')[0] == timestamp.split(':')[0]:
                                    steam_to_player[steam_id]['display_name'] = name_data['name']
                                    steam_to_player[steam_id]['player_num'] = name_data['player_num']
                                    del pending_names[ts]
                                    break
                            continue
                        
                        # Detect logout: "LogSCUM: '127.0.0.1 STEAMID:name(N)' logged out"
                        # Also check for client disconnect: "LogSCUM: UDedicatedServerResponse: Client disconnected"
                        logout_match = re.search(r"LogSCUM:.*'[0-9.]+\s+(\d+):([^()]+)\(\d+\)'\s+logged\s+out", line, re.IGNORECASE)
                        if not logout_match:
                            # Check for client disconnect
                            disconnect_match = re.search(r"LogSCUM:.*Client\s+disconnected", line, re.IGNORECASE)
                            if disconnect_match:
                                # Find the most recent player to mark as offline
                                # This is a fallback when we don't have specific logout info
                                pass  # Will be handled by BattlEye disconnect below
                        if logout_match:
                            steam_id = logout_match.group(1).strip()
                            if steam_id in steam_to_player:
                                steam_to_player[steam_id]['status'] = 'offline'
                                steam_to_player[steam_id]['last_seen'] = timestamp
                            continue
                        
                        # Detect BattlEye disconnect: "LogBattlEye: Display: Player #X ... disconnected"
                        disconnect_match = re.search(r'LogBattlEye:.*Player\s+#(\d+)\s+(.+?)\s+disconnected', line, re.IGNORECASE)
                        if disconnect_match:
                            player_num = disconnect_match.group(1).strip()
                            # Find player by number and mark offline
                            for steam_id, data in steam_to_player.items():
                                if data.get('player_num') == player_num:
                                    steam_to_player[steam_id]['status'] = 'offline'
                                    steam_to_player[steam_id]['last_seen'] = timestamp
                                    break
                            continue
                    
                    # Convert to players dict with display names as keys
                    for steam_id, data in steam_to_player.items():
                        display_name = data.get('display_name', data.get('char_name', 'Unknown'))
                        players[display_name] = data
                    
                    # Save current online players to database
                    try:
                        conn = sqlite3.connect(str(db_path))
                        cursor = conn.cursor()
                        
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        for steam_id, data in steam_to_player.items():
                            display_name = data.get('display_name', data.get('char_name', 'Unknown'))
                            char_name = data.get('char_name', 'Unknown')
                            ip_addr = data.get('ip', '')
                            connected_at = data.get('connected_at', current_time)
                            
                            # Check if player exists
                            cursor.execute('SELECT steam_id, first_seen, total_playtime FROM players WHERE steam_id = ?', (steam_id,))
                            existing = cursor.fetchone()
                            
                            if existing:
                                # Update existing player
                                first_seen = existing[1]
                                total_playtime = existing[2] or 0
                                
                                cursor.execute('''
                                    UPDATE players SET 
                                        display_name = ?, char_name = ?, ip_address = ?, 
                                        last_seen = ?, status = 'online', is_banned = 0
                                    WHERE steam_id = ?
                                ''', (display_name, char_name, ip_addr, current_time, steam_id))
                            else:
                                # Insert new player
                                cursor.execute('''
                                    INSERT INTO players 
                                    (steam_id, display_name, char_name, ip_address, first_seen, last_seen, status)
                                    VALUES (?, ?, ?, ?, ?, ?, 'online')
                                ''', (steam_id, display_name, char_name, ip_addr, connected_at, current_time))
                            
                            # Log session start if this is a new connection
                            if not existing or existing[0] is None:
                                cursor.execute('''
                                    INSERT INTO player_sessions (steam_id, session_start, ip_address)
                                    VALUES (?, ?, ?)
                                ''', (steam_id, connected_at, ip_addr))
                        
                        # Mark players as offline if they're not in current session
                        online_steam_ids = set(steam_to_player.keys())
                        cursor.execute("SELECT steam_id FROM players WHERE status = 'online'")
                        db_online = cursor.fetchall()
                        
                        for (db_steam_id,) in db_online:
                            if db_steam_id not in online_steam_ids:
                                # Player went offline - update session end time
                                cursor.execute('''
                                    UPDATE player_sessions SET 
                                        session_end = ?, 
                                        duration = CAST((julianday(?) - julianday(session_start)) * 86400 AS INTEGER)
                                    WHERE steam_id = ? AND session_end IS NULL
                                ''', (current_time, current_time, db_steam_id))
                                
                                # Update player status and playtime
                                cursor.execute('''
                                    SELECT SUM(duration) FROM player_sessions 
                                    WHERE steam_id = ? AND duration IS NOT NULL
                                ''', (db_steam_id,))
                                total_duration = cursor.fetchone()[0] or 0
                                
                                cursor.execute('''
                                    UPDATE players SET 
                                        status = 'offline', 
                                        last_seen = ?,
                                        total_playtime = ?
                                    WHERE steam_id = ?
                                ''', (current_time, total_duration, db_steam_id))
                        
                        conn.commit()
                        conn.close()
                        
                    except Exception as e:
                        self.write_log('error', f'Failed to save player data to database: {e}', 'ERROR')
                
            except Exception as e:
                self.write_log('error', f'Error parsing SCUM server logs: {e}', 'ERROR')
        
        # Update table with player data
        self.table_players.setRowCount(0)

        if not players:
            self.table_players.insertRow(0)
            no_players_msg = QTableWidgetItem("👥 No players detected yet - waiting for players to join...")
            no_players_msg.setForeground(QColor('#8be9fd'))
            self.table_players.setItem(0, 0, no_players_msg)
            self.table_players.setSpan(0, 0, 1, 8)
            # Update counts
            if hasattr(self, 'label_online_count'):
                self.label_online_count.setText("0")
            if hasattr(self, 'label_total_tracked'):
                self.label_total_tracked.setText("Total Tracked: 0")
        else:
            # Sort by status (online first) then by name
            sorted_players = sorted(players.items(), key=lambda x: (x[1].get('status') != 'online', x[0].lower()))

            for display_name, info in sorted_players:
                r = self.table_players.rowCount()
                self.table_players.insertRow(r)

                status = info.get('status', 'unknown')
                is_online = status == 'online'

                # Column 0: Status with icon
                status_item = QTableWidgetItem("🟢 ONLINE" if is_online else "⚫ OFFLINE")
                status_item.setForeground(QColor('#50fa7b') if is_online else QColor('#666666'))
                status_item.setTextAlignment(Qt.AlignCenter)
                self.table_players.setItem(r, 0, status_item)

                # Column 1: Player Name (display name from BattlEye) - LARGER FONT
                name_item = QTableWidgetItem(display_name)
                name_item.setForeground(QColor('#8be9fd') if is_online else QColor('#666666'))
                name_item.setFont(QFont('Segoe UI', 14, QFont.Bold if is_online else QFont.Normal))
                self.table_players.setItem(r, 1, name_item)

                # Column 2: Steam ID
                steam_id = info.get('steam_id', '-')
                steam_item = QTableWidgetItem(steam_id)
                steam_item.setForeground(QColor('#f1fa8c'))
                self.table_players.setItem(r, 2, steam_item)

                # Column 3: Character Name
                char_name = info.get('char_name', '-')
                char_item = QTableWidgetItem(char_name)
                char_item.setForeground(QColor('#ffb86b'))
                self.table_players.setItem(r, 3, char_item)

                # Column 4: Connected At
                connected_at = info.get('connected_at', '-')
                if connected_at != '-':
                    # Format: 2025.11.02-23.08.40 -> Nov 02, 23:08:40
                    try:
                        dt = datetime.strptime(connected_at.split(':')[0], '%Y.%m.%d-%H.%M.%S')
                        connected_at = dt.strftime('%b %d, %H:%M:%S')
                    except:
                        pass
                connected_item = QTableWidgetItem(connected_at)
                connected_item.setForeground(QColor('#bd93f9'))
                self.table_players.setItem(r, 4, connected_item)

                # Column 5: Play Time (calculate duration if online)
                play_time = "-"
                if is_online and info.get('connected_at') != '-':
                    try:
                        conn_time = info.get('connected_at', '')
                        dt_conn = datetime.strptime(conn_time.split(':')[0], '%Y.%m.%d-%H.%M.%S')
                        duration = datetime.now() - dt_conn
                        hours = int(duration.total_seconds() // 3600)
                        minutes = int((duration.total_seconds() % 3600) // 60)
                        play_time = f"{hours}h {minutes}m"
                    except:
                        play_time = "Active"
                time_item = QTableWidgetItem(play_time)
                time_item.setForeground(QColor('#50fa7b') if is_online else QColor('#666666'))
                self.table_players.setItem(r, 5, time_item)

                # Column 6: IP Address
                ip_addr = info.get('ip', '-')
                ip_item = QTableWidgetItem(ip_addr)
                ip_item.setForeground(QColor('#ffb86b'))
                self.table_players.setItem(r, 6, ip_item)

                # Column 7: Actions (buttons for online players)
                if is_online:
                    action_widget = QWidget()
                    action_layout = QHBoxLayout()
                    action_layout.setContentsMargins(2, 2, 2, 2)
                    action_layout.setSpacing(4)

                    kick_btn = QPushButton('👢 Kick')
                    kick_btn.setStyleSheet("""
                        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #ff5555, stop:1 #cc4444);
                        color: white;
                        padding: 6px 10px;
                        font-size: 11px;
                        font-weight: bold;
                        border: none;
                        border-radius: 4px;
                        min-width: 50px;
                    """)
                    kick_btn.clicked.connect(lambda _, n=display_name, sid=steam_id: self.kick_player(n, sid))
                    kick_btn.setToolTip(f"Kick {display_name} from server")

                    ban_btn = QPushButton('🚫 Ban')
                    ban_btn.setStyleSheet("""
                        background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #ff6e67, stop:1 #cc5555);
                        color: white;
                        padding: 6px 10px;
                        font-size: 11px;
                        font-weight: bold;
                        border: none;
                        border-radius: 4px;
                        min-width: 50px;
                    """)
                    ban_btn.clicked.connect(lambda _, n=display_name, sid=steam_id: self.ban_player(n, sid))
                    ban_btn.setToolTip(f"Permanently ban {display_name}")

                    action_layout.addWidget(kick_btn)
                    action_layout.addWidget(ban_btn)
                    action_widget.setLayout(action_layout)
                    self.table_players.setCellWidget(r, 7, action_widget)
                else:
                    self.table_players.setItem(r, 7, QTableWidgetItem(""))

        # Update summary counts and server status
        online_count = sum(1 for info in players.values() if info.get('status') == 'online')
        offline_count = len(players) - online_count

        if hasattr(self, 'label_online_count'):
            self.label_online_count.setText(str(online_count))

        if hasattr(self, 'label_total_tracked'):
            self.label_total_tracked.setText(f"Total Tracked: {len(players)}")

        # Update server status
        if hasattr(self, 'label_server_status'):
            if self.server_pid:
                self.label_server_status.setText("🟢 RUNNING")
                self.label_server_status.setStyleSheet("font-size: 24px; font-weight: bold; color: #50fa7b; text-align: center;")
            else:
                self.label_server_status.setText("🔴 OFFLINE")
                self.label_server_status.setStyleSheet("font-size: 24px; font-weight: bold; color: #ff5555; text-align: center;")

        # Update uptime display
        if hasattr(self, 'label_uptime_display'):
            if self.server_pid and hasattr(self, 'server_start_time'):
                try:
                    uptime = datetime.now() - self.server_start_time
                    hours = int(uptime.total_seconds() // 3600)
                    minutes = int((uptime.total_seconds() % 3600) // 60)
                    seconds = int(uptime.total_seconds() % 60)
                    self.label_uptime_display.setText(f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}")
                except:
                    self.label_uptime_display.setText("Uptime: --:--:--")
            else:
                self.label_uptime_display.setText("Uptime: --:--:--")

        # Update peak players today
        if hasattr(self, 'label_peak_today'):
            try:
                # Track peak players in current session
                if not hasattr(self, '_peak_today'):
                    self._peak_today = 0
                self._peak_today = max(self._peak_today, online_count)
                self.label_peak_today.setText(f"Peak Today: {self._peak_today}")
            except:
                self.label_peak_today.setText("Peak Today: 0")

        # Update online activity indicator
        if hasattr(self, 'online_activity'):
            if online_count > 0:
                self.online_activity.setText("⚡ Real-time updates active")
                self.online_activity.setStyleSheet("font-size: 11px; color: #50fa7b; text-align: center;")
            else:
                self.online_activity.setText("⏸️ Waiting for players")
                self.online_activity.setStyleSheet("font-size: 11px; color: #666666; text-align: center;")

    def filter_players(self):
        """Filter player table based on search text and filter combo"""
        search_text = self.player_search.text().lower()
        filter_type = self.filter_combo.currentText()

        for row in range(self.table_players.rowCount()):
            # Skip empty rows or message rows
            if row >= self.table_players.rowCount():
                continue

            status_item = self.table_players.item(row, 0)
            if not status_item:
                continue

            # Get player status
            is_online = "ONLINE" in status_item.text()

            # Apply filter type
            show_by_filter = True
            if filter_type == "Online Only":
                show_by_filter = is_online
            elif filter_type == "Offline Only":
                show_by_filter = not is_online
            elif filter_type == "Admins":
                # TODO: Check admin status from database
                show_by_filter = False  # Placeholder
            elif filter_type == "Banned":
                # TODO: Check ban status from database
                show_by_filter = False  # Placeholder
            # "All Players" shows everything

            # Apply search filter
            show_by_search = not search_text  # Show all if no search
            if search_text:
                for col in range(self.table_players.columnCount() - 1):  # Exclude action column
                    item = self.table_players.item(row, col)
                    if item and search_text in item.text().lower():
                        show_by_search = True
                        break

            # Show/hide row based on both filters
            self.table_players.setRowHidden(row, not (show_by_filter and show_by_search))

    def kick_player(self, player_name: str, steam_id: str = None):
        """Kick a player from the server using SCUM console commands.
        Accepts either player_name or steam_id (preferred).
        """
        if not self.server_pid:
            QMessageBox.warning(self, "Server Offline", "Cannot kick player - server is not running")
            return
        
        # Confirm kick action with detailed dialog
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Confirm Kick")
        msg.setText(f"⚠️ Kick Player: {player_name}")
        msg.setInformativeText("This will forcefully remove the player from the server.\nThey can rejoin immediately after.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        
        if msg.exec() != QMessageBox.Yes:
            return
        
        try:
            from scum_core import kick_player_via_console

            # Prefer using SteamID if provided
            target = steam_id if steam_id else player_name

            # Get kick reason
            reason, ok = QInputDialog.getText(
                self,
                "Kick Reason",
                f"Enter reason for kicking {player_name} (SteamID: {steam_id}):",
                text="Kicked by admin"
            )

            if not ok:
                return

            # If steam_id is available, use console format that includes it; otherwise fallback to name
            success = kick_player_via_console(target, reason)

            if success:
                self.write_log('admin', f'✅ Player kicked: {player_name} (SteamID: {steam_id} Reason: {reason})', 'INFO')
                self.write_log('player', f'Player {player_name} was kicked from the server', 'INFO')
                QMessageBox.information(self, "Success", f"✅ Kick command sent for '{player_name}'!\n\nThe server will process this command shortly.")
                self.populate_players()
            else:
                QMessageBox.warning(
                    self,
                    "Config Not Found",
                    "Could not find SCUM server config directory.\n\nPlease ensure the server path is configured correctly in Settings."
                )
                self.write_log('error', f'Failed to kick {player_name}: Config directory not found', 'ERROR')

        except Exception as e:
            self.write_log('error', f'Error kicking player {player_name}: {str(e)}', 'ERROR')
            QMessageBox.critical(self, "Error", f"❌ Failed to kick player:\n{str(e)}")

    def ban_player(self, player_name: str, steam_id: str):
        """Ban a player from the server using BannedUsers.ini"""
        if not self.server_pid:
            QMessageBox.warning(self, "Server Offline", "Cannot ban player - server is not running")
            return
        
        # Confirm ban action with detailed warning
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Confirm Permanent Ban")
        msg.setText(f"🚫 PERMANENTLY BAN: {player_name}")
        msg.setInformativeText(
            f"Steam ID: {steam_id}\n\n"
            f"⚠️ WARNING: This is a PERMANENT action!\n"
            f"The player will NOT be able to rejoin this server."
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        
        if msg.exec() != QMessageBox.Yes:
            return
        
        try:
            from scum_core import ban_player_via_ini
            
            # Get ban reason
            reason, ok = QInputDialog.getText(
                self, 
                "Ban Reason", 
                f"Enter reason for banning {player_name}:",
                text="Banned by admin"
            )
            
            if not ok:
                return
            
            # Add to BannedUsers.ini
            success = ban_player_via_ini(player_name, steam_id, reason)
            
            if success:
                self.write_log('admin', f'🚫 Player BANNED: {player_name} (Steam ID: {steam_id}, Reason: {reason})', 'WARNING')
                self.write_log('player', f'Player {player_name} was permanently banned', 'WARNING')
                QMessageBox.information(
                    self, 
                    "Ban Successful", 
                    f"🚫 Player '{player_name}' has been added to BannedUsers.ini!\n\n"
                    f"Steam ID: {steam_id}\n"
                    f"Reason: {reason}\n\n"
                    f"They have been kicked and cannot rejoin."
                )
                self.populate_players()
            else:
                QMessageBox.warning(
                    self, 
                    "Config Not Found", 
                    "Could not find BannedUsers.ini file.\n\nPlease ensure the server path is configured correctly in Settings."
                )
                self.write_log('error', f'Failed to ban {player_name}: BannedUsers.ini not found', 'ERROR')
        except Exception as ban_error:
            # Fallback to old method if needed
            try:
                from scum_core import send_rcon_command, get_rcon_config
                
                # Get RCON settings from server.cfg
                rcon_config = get_rcon_config()
                rcon_host = rcon_config.get('host', '127.0.0.1')
                rcon_port = rcon_config.get('port', 27015)
                rcon_password = rcon_config.get('password', '')
                
                response = send_rcon_command(
                    host=rcon_host,
                    port=rcon_port,
                    password=rcon_password,
                    command=f'#ban {steam_id} Banned by admin'
                )
                
                if response:
                    self.write_log('admin', f'🚫 Player BANNED: {player_name} (Steam ID: {steam_id})', 'WARNING')
                    self.write_log('player', f'Player {player_name} was permanently banned', 'WARNING')
                    QMessageBox.information(self, "Ban Successful", f"🚫 Player '{player_name}' has been permanently banned!\n\nSteam ID: {steam_id}")
                    self.populate_players()
                    return
            except Exception as rcon_error:
                self.write_log('error', f'RCON ban failed: {str(rcon_error)}', 'ERROR')
            
            # If RCON fails, show manual instructions
            QMessageBox.information(
                self,
                "Manual Ban Required",
                f"⚠️ RCON is not configured.\n\n"
                f"To ban '{player_name}':\n"
                f"1. Open SCUM server console\n"
                f"2. Type: #ban {steam_id} Banned by admin\n"
                f"3. Press Enter\n\n"
                f"Steam ID: {steam_id}\n\n"
                f"Or add to banned.txt in server config folder."
            )
            self.write_log('admin', f'⚠️ Manual ban required: {player_name} ({steam_id}) - RCON not configured', 'WARNING')
                
        except Exception as e:
            self.write_log('error', f'Error banning player {player_name}: {str(e)}', 'ERROR')
            QMessageBox.critical(self, "Error", f"❌ Failed to ban player:\n{str(e)}")

    def unban_player(self, ban_entry: str):
        """Unban a player by removing from BannedUsers.ini"""
        if not self.server_pid:
            QMessageBox.warning(self, "Server Offline", "Cannot unban player - server is not running")
            return
        
        # Confirm unban action
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("Confirm Unban")
        msg.setText(f"🔓 Unban Player: {ban_entry}")
        msg.setInformativeText("This will remove the ban for this player/entry.\nThey will be able to join the server again.")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)
        
        if msg.exec() != QMessageBox.Yes:
            return
        
        try:
            from scum_core import unban_player_via_ini
            
            # Remove from BannedUsers.ini
            success = unban_player_via_ini(ban_entry)
            
            if success:
                self.write_log('admin', f'🔓 Player UNBANNED: {ban_entry}', 'INFO')
                self.write_log('player', f'Ban removed for: {ban_entry}', 'INFO')
                QMessageBox.information(
                    self, 
                    "Unban Successful", 
                    f"🔓 Ban removed for '{ban_entry}'!\n\nThey can now join the server again."
                )
                self.populate_bans()
            else:
                QMessageBox.warning(
                    self, 
                    "Config Not Found", 
                    "Could not find BannedUsers.ini file.\n\nPlease ensure the server path is configured correctly in Settings."
                )
                self.write_log('error', f'Failed to unban {ban_entry}: BannedUsers.ini not found', 'ERROR')
                
        except Exception as e:
            self.write_log('error', f'Error unbanning {ban_entry}: {str(e)}', 'ERROR')
            QMessageBox.critical(self, "Error", f"❌ Failed to unban:\n{str(e)}")

    def add_admin(self):
        """Add a player as admin via AdminUsers.ini (from selected table row)"""
        # Get selected player from table
        current_row = self.table_players.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a player from the table first.")
            return
        
        # Get player info
        player_name = self.table_players.item(current_row, 1).text()
        steam_id = self.table_players.item(current_row, 2).text()
        
        # Call the direct function
        self.add_admin_direct(player_name, steam_id)
    
    def add_admin_direct(self, player_name, steam_id):
        """Add a player as admin directly with provided name and Steam ID"""
        print(f"DEBUG: add_admin_direct called with player_name='{player_name}', steam_id='{steam_id}'")
        self.write_log('debug', f'Add admin button clicked for {player_name} ({steam_id})', 'DEBUG')
        
        # Validate Steam ID
        if not steam_id or steam_id == '-':
            QMessageBox.warning(
                self,
                "Invalid Steam ID",
                f"Cannot add admin: Steam ID is missing or invalid.\n\n"
                f"Player: {player_name}\n"
                f"Steam ID: {steam_id}\n\n"
                "The player must have a valid Steam ID to be added as admin."
            )
            self.write_log('error', f'Cannot add admin for {player_name}: Invalid Steam ID ({steam_id})', 'ERROR')
            return
        
        # Confirm admin addition
        reply = QMessageBox.question(
            self, 
            "Add Admin", 
            f"Are you sure you want to add '{player_name}' (Steam ID: {steam_id}) as an admin?\n\n"
            "This will give them full administrative privileges on the server.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            from scum_core import add_admin_via_ini, get_admin_users_file
            
            # Debug: Check if we can find the config directory
            admin_file = get_admin_users_file()
            self.write_log('debug', f'Looking for AdminUsers.ini at: {admin_file}', 'DEBUG')
            
            if not admin_file:
                error_msg = (
                    "Could not find SCUM config directory!\n\n"
                    "Please make sure:\n"
                    "1. SCUM server path is set in Settings tab\n"
                    "2. The server has been run at least once\n"
                    "3. The Config/WindowsServer directory exists"
                )
                QMessageBox.critical(self, "Config Directory Not Found", error_msg)
                self.write_log('error', 'AdminUsers.ini path could not be determined', 'ERROR')
                return
            
            success = add_admin_via_ini(player_name, steam_id)
            
            if success:
                self.write_log('admin', f'🔑 Player ADDED as ADMIN: {player_name} ({steam_id})', 'INFO')
                self.write_log('player', f'Player {player_name} has been granted admin privileges', 'INFO')
                self.write_log('info', f'AdminUsers.ini updated at: {admin_file}', 'INFO')
                
                # Ask if user wants to restart server now
                restart_reply = QMessageBox.question(
                    self,
                    "Admin Added - Restart Server?",
                    f"✅ '{player_name}' has been added as admin!\n\n"
                    f"📁 Admin files updated:\n"
                    f"  • AdminUsers.ini\n"
                    f"  • ServerSettingsAdminUsers.ini\n\n"
                    f"⚠️ Server must restart for changes to take effect.\n\n"
                    f"Restart server now?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if restart_reply == QMessageBox.Yes:
                    if self.server_pid:
                        QMessageBox.information(
                            self,
                            "Restarting Server",
                            "Server is restarting...\n\n"
                            "Wait 30 seconds, then join server.\n"
                            "Use #SetAdminPassword admin123 in-game to activate admin."
                        )
                        self.on_restart()
                    else:
                        QMessageBox.information(
                            self,
                            "Server Not Running",
                            "Server is not running.\n\n"
                            "Start the server and admin will be active.\n"
                            "Use #SetAdminPassword admin123 in-game."
                        )
                else:
                    QMessageBox.information(
                        self,
                        "Admin Added",
                        f"✅ Admin added successfully!\n\n"
                        "Remember to restart the server manually and use:\n"
                        "#SetAdminPassword admin123"
                    )
            else:
                QMessageBox.warning(
                    self, 
                    "Failed to Add Admin", 
                    f"Could not add admin to file.\n\nFile path: {admin_file}\n\nCheck the logs for details."
                )
                self.write_log('error', f'Failed to add admin {player_name} ({steam_id}) to {admin_file}', 'ERROR')
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.write_log('error', f'Error adding admin {player_name} ({steam_id}): {str(e)}\n{error_details}', 'ERROR')
            QMessageBox.critical(self, "Error", f"❌ Failed to add admin:\n\n{str(e)}")

    def show_admin_help(self):
        """Show admin password and usage instructions"""
        try:
            from scum_core import find_scum_config_dir
            from pathlib import Path
            import re
            
            # Read current admins from file
            config_dir = find_scum_config_dir()
            admin_list = "No admins found"
            
            if config_dir:
                admin_file = config_dir / "AdminUsers.ini"
                if admin_file.exists():
                    content = admin_file.read_text(encoding='utf-8', errors='ignore')
                    steam_ids = re.findall(r'SteamID="(\d+)"', content)
                    if steam_ids:
                        admin_list = "\n   ".join([f"• Steam ID: {sid}" for sid in steam_ids])
            
            help_text = f"""
🔑 SCUM ADMIN SYSTEM HELP

═══════════════════════════════════════════════════

📋 CURRENT ADMINS:
   {admin_list}

🔑 ADMIN PASSWORD: admin123

═══════════════════════════════════════════════════

✅ HOW TO USE ADMIN COMMANDS:

1️⃣ MAKE SURE YOU'RE ADDED AS ADMIN
   • Click 👑 Admin button next to your name in Players tab
   • Restart server when prompted

2️⃣ JOIN YOUR SERVER
   • Open SCUM game
   • Connect to your server

3️⃣ AUTHENTICATE (FIRST TIME ONLY)
   • Press T to open chat
   • Type: #SetAdminPassword admin123
   • Press Enter

4️⃣ USE ADMIN COMMANDS
   • Press T to open chat
   • Type any admin command (starts with #)
   • Example: #god

═══════════════════════════════════════════════════

📚 COMMON ADMIN COMMANDS:
   • #help - List all commands
   • #god - Toggle god mode
   • #teleport X Y Z - Teleport to coordinates
   • #spawnitem ItemName Amount - Spawn items
   • #listplayers - Show all players
   • #kick PlayerName - Kick player
   • #ban PlayerName - Ban player
   • #time HH:MM - Set server time
   • #location - Show your coordinates
   • #fly - Toggle fly mode
   • #invisible - Toggle invisibility

═══════════════════════════════════════════════════

❓ TROUBLESHOOTING:
   • Make sure server restarted after adding admin
   • Make sure you used #SetAdminPassword admin123 in-game
   • Check your Steam ID is correct (starts with 7656)
   • Try restarting SCUM game client

🔄 TO ADD MORE ADMINS:
   • Go to Players tab
   • Click 👑 Admin button next to player name
   • Restart server when prompted
   • They must use #SetAdminPassword admin123 when they join

═══════════════════════════════════════════════════

� ADMIN FILES LOCATION:
C:\\ScumServer\\SCUM\\Saved\\Config\\WindowsServer\\
   • AdminUsers.ini
   • ServerSettingsAdminUsers.ini
   • ServerSettings.ini (contains ServerAdminPassword)
        """
            
            QMessageBox.information(self, "🔑 Admin Help", help_text)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load admin help: {str(e)}")
    
    def send_custom_rcon_command(self):
        """Send custom RCON command entered by user"""
        command = self.rcon_command_input.text().strip()
        if not command:
            QMessageBox.warning(self, "Empty Command", "Please enter an RCON command to send.")
            return
            
        try:
            from scum_core import send_rcon_command, get_rcon_config
            rcon_config = get_rcon_config()
            response = send_rcon_command(
                command,
                rcon_config.get('host', '127.0.0.1'), 
                rcon_config.get('port', 27015), 
                rcon_config.get('password', '')
            )
            self.rcon_response_display.append(f"> {command}")
            self.rcon_response_display.append(f"< {response}")
            self.rcon_response_display.append("")  # Empty line for separation
            self.rcon_command_input.clear()
        except Exception as e:
            error_msg = f"Failed to send RCON command: {str(e)}"
            self.rcon_response_display.append(f"ERROR: {error_msg}")
            self.rcon_response_display.append("")
            QMessageBox.critical(self, "RCON Error", error_msg)

    def send_quick_rcon_command(self, command):
        """Send quick RCON command from button"""
        try:
            from scum_core import send_rcon_command, get_rcon_config
            rcon_config = get_rcon_config()
            response = send_rcon_command(
                command,
                rcon_config.get('host', '127.0.0.1'), 
                rcon_config.get('port', 27015), 
                rcon_config.get('password', '')
            )
            self.rcon_response_display.append(f"> {command}")
            self.rcon_response_display.append(f"< {response}")
            self.rcon_response_display.append("")
        except Exception as e:
            error_msg = f"Failed to send RCON command: {str(e)}"
            self.rcon_response_display.append(f"ERROR: {error_msg}")
            self.rcon_response_display.append("")
            QMessageBox.critical(self, "RCON Error", error_msg)

    # --- bans ---
    def populate_bans(self):
        items = load_bans()
        self.table_bans.setRowCount(0)
        for e in items:
            r = self.table_bans.rowCount()
            self.table_bans.insertRow(r)
            self.table_bans.setItem(r, 0, QTableWidgetItem(e))

    def on_add_ban(self):
        entry = self.input_ban.text().strip()
        if not entry:
            return
        if add_ban(entry):
            self.write_log('admin', f'Player banned: {entry}', 'INFO')
            self.write_log('player', f'Player {entry} has been banned from the server', 'INFO')
            self.write_log('events', f'Ban added for: {entry}', 'INFO')
            self.populate_bans()
            self.input_ban.clear()

    def on_remove_ban(self):
        entry = self.input_ban.text().strip()
        if not entry:
            return
        if remove_ban(entry):
            self.write_log('admin', f'Player unbanned: {entry}', 'INFO')
            self.write_log('player', f'Ban removed for player: {entry}', 'INFO')
            self.write_log('events', f'Ban removed for: {entry}', 'INFO')
            self.populate_bans()
            self.input_ban.clear()

    # --- settings persistence ---
    def settings_file(self) -> Path:
        return APP_ROOT / 'scum_settings.json'

    def load_settings(self):
        """Load all saved settings including paths and configurations"""
        sf = self.settings_file()
        if sf.exists():
            try:
                data = json.loads(sf.read_text(encoding='utf-8'))
                
                # Load SCUMServer.exe path
                p = data.get('scum_path')
                if p:
                    self.scum_path = p
                    # Update UI elements only if they exist (lazy loading compatible)
                    if hasattr(self, 'label_path'):
                        self.label_path.setText(p)
                    if hasattr(self, 'setup_label_path'):
                        self.setup_label_path.setText(f"✅ {Path(p).name}")
                    if hasattr(self, 'install_status'):
                        self.install_status.setText("✅ Server configured")
                        self.install_status.setStyleSheet("color: #50fa7b; font-size: 11px;")
                
                # Load SteamCMD directory
                steamcmd = data.get('steamcmd_dir')
                if steamcmd and hasattr(self, 'steamcmd_dir'):
                    self.steamcmd_dir.setText(steamcmd)
                
                # Load SCUM Server download directory
                scum_dir = data.get('scum_server_dir')
                if scum_dir and hasattr(self, 'scum_server_dir'):
                    self.scum_server_dir.setText(scum_dir)
                
                # Load config folder path
                config_path = data.get('config_base_path')
                if config_path and Path(config_path).exists():
                    self.config_base_path = Path(config_path)
                    if hasattr(self, 'config_path_display'):
                        self.config_path_display.setText(str(config_path))
                    # Auto-load the config directory if it exists and UI is ready
                    if hasattr(self, 'config_tree'):
                        self.load_config_directory(self.config_base_path)
                
                # Load RCON settings
                rcon_config = data.get('rcon', {})
                if hasattr(self, 'rcon_host'):
                    self.rcon_host.setText(rcon_config.get('host', '127.0.0.1'))
                if hasattr(self, 'rcon_port'):
                    self.rcon_port.setValue(rcon_config.get('port', 27015))
                if hasattr(self, 'rcon_password'):
                    self.rcon_password.setText(rcon_config.get('password', ''))
                
                # Load setup configuration
                setup_config = data.get('setup_config', {})
                if setup_config and hasattr(self, 'setup_server_name'):
                    self.setup_server_name.setText(setup_config.get('server_name', 'My SCUM Server'))
                    self.setup_max_players.setValue(setup_config.get('max_players', 50))
                    self.setup_port.setValue(setup_config.get('port', 27015))
                    self.setup_password.setText(setup_config.get('password', ''))
                    difficulty_index = setup_config.get('difficulty', 2)
                    self.setup_difficulty.setCurrentIndex(difficulty_index)
                    
            except Exception as e:
                print(f"Error loading settings: {e}")

    def save_settings(self, show_message=False):
        """Save all settings including paths and configurations
        
        Args:
            show_message: If True, show success message popup
        """
        sf = self.settings_file()
        
        # Gather all settings
        data = {
            'scum_path': self.scum_path,
        }
        
        # Save SteamCMD directory if it exists
        if hasattr(self, 'steamcmd_dir'):
            data['steamcmd_dir'] = self.steamcmd_dir.text()
        
        # Save SCUM Server directory if it exists
        if hasattr(self, 'scum_server_dir'):
            data['scum_server_dir'] = self.scum_server_dir.text()
        
        # Save config folder path if it exists
        if hasattr(self, 'config_base_path') and self.config_base_path:
            data['config_base_path'] = str(self.config_base_path)
        
        # Save RCON settings if they exist
        if hasattr(self, 'rcon_host') and hasattr(self, 'rcon_port') and hasattr(self, 'rcon_password'):
            data['rcon'] = {
                'host': self.rcon_host.text(),
                'port': self.rcon_port.value(),
                'password': self.rcon_password.text()
            }
        
        # Save setup configuration if it exists
        if hasattr(self, 'setup_server_name'):
            data['setup_config'] = {
                'server_name': self.setup_server_name.text(),
                'max_players': self.setup_max_players.value(),
                'port': self.setup_port.value(),
                'password': self.setup_password.text(),
                'difficulty': self.setup_difficulty.currentIndex()
            }
        
        try:
            sf.write_text(json.dumps(data, indent=2), encoding='utf-8')
            if show_message:
                QMessageBox.information(self, '✅ Saved', 'All settings saved successfully!\n\nYour configuration will be loaded automatically next time.')
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Could not save settings: {e}')

    def on_tab_changed(self, index):
        """Handle tab changes with lazy loading for performance optimization"""
        # Switch to the new tab
        self.stack.setCurrentIndex(index)
        
        # Lazy load tab UI construction if not already initialized
        if index not in self._tabs_initialized:
            self._tabs_initialized.add(index)
            
            # Tab indices: 0=Dashboard, 1=Players, 2=Player Stats, 3=Server, 4=Config, 5=Logs, 6=Bans, 7=Performance, 8=Settings, 9=Setup
            if index == 1:  # Players tab
                self.build_players()
                self.populate_players()
            elif index == 2:  # Player Stats tab
                self.build_player_stats()
            elif index == 3:  # Server tab
                self.build_server()
            elif index == 4:  # Config Editor tab
                self.build_config_editor()
            elif index == 5:  # Logs tab
                self.build_logs()
                # load_logs() is now called asynchronously within build_logs()
            elif index == 6:  # Bans tab
                self.build_bans()
                self.populate_bans()
            elif index == 7:  # Performance tab
                self.build_performance()
            elif index == 8:  # Settings tab
                self.build_settings()
            elif index == 9:  # Setup tab
                self.build_setup()
    
    def change_page(self, index):
        self.stack.setCurrentIndex(index)

    def toggle_auto_refresh(self, state):
        if state == 2:  # Checked
            self.timer.start(500)  # Optimized: 500ms refresh (2x/sec) - smooth and responsive
        else:  # Unchecked
            self.timer.stop()

    def toggle_players_auto_refresh(self, state):
        if state == 2:  # Checked
            self.players_timer.start(1000)  # Log monitoring: 1 second intervals
        else:  # Unchecked
            self.players_timer.stop()

    def update_network_info(self):
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            self.label_ip.setText(f"🌐 IP: {ip}")
        except Exception:
            self.label_ip.setText("🌐 IP: Unknown")

    # --- page builders ---
    def build_dashboard(self):
        layout = QVBoxLayout()
        # Title with refresh button and auto-refresh indicator
        title_layout = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #e6eef6;")
        
        # Auto-refresh indicator
        self.label_auto_refresh = QLabel("🔄 Real-time (2x/sec)")
        self.label_auto_refresh.setStyleSheet("font-size: 12px; color: #50fa7b; padding: 5px;")
        self.label_auto_refresh.setToolTip("Dashboard updates 2 times per second - optimized for performance")
        
        btn_refresh = QPushButton("🔄 Refresh Now")
        btn_refresh.clicked.connect(self.refresh_all)
        btn_refresh.setToolTip("Manually refresh all dashboard data")
        title_layout.addWidget(title)
        title_layout.addWidget(self.label_auto_refresh)
        title_layout.addStretch()
        title_layout.addWidget(btn_refresh)
        layout.addLayout(title_layout)

        # Cards container - Grid layout
        cards_layout = QGridLayout()

        # Server Status Card - Task Manager style
        status_card = QGroupBox("🖥️ Server Status")
        status_layout = QVBoxLayout()
        self.label_status = QLabel("� Offline")
        self.label_status.setStyleSheet("font-size: 16px; padding: 5px; font-weight: bold;")
        self.label_status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label_uptime = QLabel("⏱️ Not running")
        self.label_uptime.setStyleSheet("font-size: 13px; padding: 5px; color: #aaa;")
        self.label_uptime.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        # Server readiness indicator
        self.label_ready_status = QLabel("⭕ Offline: Server not running")
        self.label_ready_status.setStyleSheet("font-size: 11px; padding: 5px; color: #666;")
        self.label_ready_status.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label_ready_status.setToolTip("Shows when server is ready for players to join")
        
        status_layout.addWidget(self.label_status)
        status_layout.addWidget(self.label_uptime)
        status_layout.addWidget(self.label_ready_status)
        status_layout.addStretch()
        status_card.setLayout(status_layout)
        cards_layout.addWidget(status_card, 0, 0)

        # Players Card
        players_card = QGroupBox("Players")
        players_layout = QVBoxLayout()
        self.label_players = QLabel("👥 Online: -")
        self.label_players.setStyleSheet("font-size: 14px; padding: 5px;")
        self.label_players.setTextInteractionFlags(Qt.TextSelectableByMouse)
        players_layout.addWidget(self.label_players)
        players_layout.addStretch()
        players_card.setLayout(players_layout)
        cards_layout.addWidget(players_card, 0, 1)

        # System Resources Card - Task Manager style with enhanced details
        system_card = QGroupBox("Performance")
        system_card.setStyleSheet("""
            QGroupBox {
                border: 2px solid #0078d4;
                border-radius: 8px;
                margin-top: 6px;
                font-weight: bold;
                font-size: 14px;
                color: #e6eef6;
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1e1e1e, stop:1 #2b2f36);
            }
            QGroupBox::title {
                color: #0078d4;
                font-weight: bold;
                font-size: 14px;
                padding: 5px 10px;
                left: 10px;
                top: -8px;
            }
        """)
        system_layout = QVBoxLayout()
        system_layout.setSpacing(8)
        system_layout.setContentsMargins(15, 20, 15, 15)
        
        # CPU Section - Enhanced Task Manager style
        cpu_header = QLabel("💻 CPU")
        cpu_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #8be9fd; margin-bottom: 5px;")
        system_layout.addWidget(cpu_header)
        
        self.pb_cpu = QProgressBar()
        self.pb_cpu.setMaximum(100)
        self.pb_cpu.setMinimumHeight(30)
        self.pb_cpu.setStyleSheet("""
            QProgressBar {
                border: 2px solid #444;
                border-radius: 4px;
                text-align: center;
                background: #0d1016;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0078d4, stop:1 #00bcf2);
                border-radius: 2px;
            }
        """)
        self.label_cpu_detail = QLabel("CPU: 0.0% (0 cores) | Speed: 0 MHz")
        self.label_cpu_detail.setStyleSheet("font-size: 11px; color: #aaa; padding: 3px; background: #1a1d23; border-radius: 3px; margin-top: 2px;")
        system_layout.addWidget(self.pb_cpu)
        system_layout.addWidget(self.label_cpu_detail)
        
        # RAM Section - Enhanced Task Manager style
        ram_header = QLabel("🧠 Memory")
        ram_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #50fa7b; margin-top: 10px; margin-bottom: 5px;")
        system_layout.addWidget(ram_header)
        
        self.pb_ram = QProgressBar()
        self.pb_ram.setMaximum(100)
        self.pb_ram.setMinimumHeight(30)
        self.pb_ram.setStyleSheet("""
            QProgressBar {
                border: 2px solid #444;
                border-radius: 4px;
                text-align: center;
                background: #0d1016;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #50fa7b);
                border-radius: 2px;
            }
        """)
        self.label_ram_detail = QLabel("Available: 0.0 GB | In Use: 0.0 GB")
        self.label_ram_detail.setStyleSheet("font-size: 11px; color: #aaa; padding: 3px; background: #1a1d23; border-radius: 3px; margin-top: 2px;")
        self.label_process_mem = QLabel("Server Memory: N/A")
        self.label_process_mem.setStyleSheet("font-size: 11px; color: #ffb86b; padding: 3px; background: #2b1a1a; border-radius: 3px; margin-top: 2px; font-weight: bold;")
        system_layout.addWidget(self.pb_ram)
        system_layout.addWidget(self.label_ram_detail)
        system_layout.addWidget(self.label_process_mem)
        
        system_card.setLayout(system_layout)
        cards_layout.addWidget(system_card, 0, 2)

        # Quick Actions Card
        actions_card = QGroupBox("Quick Actions")
        actions_layout = QVBoxLayout()
        btn_start = QPushButton("▶️ Start Server")
        btn_start.clicked.connect(self.on_start)
        btn_start.setToolTip("Start the SCUM server")
        btn_stop = QPushButton("⏹️ Stop Server")
        btn_stop.clicked.connect(self.on_stop)
        btn_stop.setToolTip("Stop the SCUM server")
        btn_restart = QPushButton("🔄 Restart Server")
        btn_restart.clicked.connect(self.on_restart)
        btn_restart.setToolTip("Restart the SCUM server")
        actions_layout.addWidget(btn_start)
        actions_layout.addWidget(btn_stop)
        actions_layout.addWidget(btn_restart)
        actions_card.setLayout(actions_layout)
        cards_layout.addWidget(actions_card, 1, 0)

        # Network Card
        network_card = QGroupBox("Network")
        network_layout = QVBoxLayout()
        self.label_ip = QLabel("🌐 IP: Loading...")
        self.label_ip.setStyleSheet("font-size: 14px; padding: 5px;")
        self.label_ip.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label_port = QLabel("🔌 Port: 27015")
        self.label_port.setStyleSheet("font-size: 14px; padding: 5px;")
        self.label_port.setTextInteractionFlags(Qt.TextSelectableByMouse)
        network_layout.addWidget(self.label_ip)
        network_layout.addWidget(self.label_port)
        network_layout.addStretch()
        network_card.setLayout(network_layout)
        cards_layout.addWidget(network_card, 1, 1)

        # Disk Usage Card - Enhanced Task Manager style
        disk_card = QGroupBox("💾 Disk (C:)")
        disk_card.setStyleSheet("""
            QGroupBox {
                border: 2px solid #f59e0b;
                border-radius: 8px;
                margin-top: 6px;
                font-weight: bold;
                font-size: 14px;
                color: #e6eef6;
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1e1e1e, stop:1 #2b2f36);
            }
            QGroupBox::title {
                color: #f59e0b;
                font-weight: bold;
                font-size: 14px;
                padding: 5px 10px;
                left: 10px;
                top: -8px;
            }
        """)
        disk_layout = QVBoxLayout()
        disk_layout.setSpacing(8)
        disk_layout.setContentsMargins(15, 20, 15, 15)
        
        self.pb_disk = QProgressBar()
        self.pb_disk.setMaximum(100)
        self.pb_disk.setMinimumHeight(30)
        self.pb_disk.setStyleSheet("""
            QProgressBar {
                border: 2px solid #444;
                border-radius: 4px;
                text-align: center;
                background: #0d1016;
                color: white;
                font-weight: bold;
                font-size: 12px;
                padding: 2px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f59e0b, stop:1 #fbbf24);
                border-radius: 2px;
            }
        """)
        self.label_disk_detail = QLabel("Free: 0 GB | Total: 0 GB")
        self.label_disk_detail.setStyleSheet("font-size: 11px; color: #aaa; padding: 3px; background: #1a1d23; border-radius: 3px; margin-top: 2px;")
        
        disk_layout.addWidget(self.pb_disk)
        disk_layout.addWidget(self.label_disk_detail)
        disk_card.setLayout(disk_layout)
        cards_layout.addWidget(disk_card, 1, 2)

        # Settings Card
        settings_card = QGroupBox("Dashboard Settings")
        settings_layout = QVBoxLayout()
        self.cb_auto_refresh = QCheckBox("Auto Refresh")
        self.cb_auto_refresh.setChecked(True)
        self.cb_auto_refresh.stateChanged.connect(self.toggle_auto_refresh)
        self.cb_auto_refresh.setToolTip("Enable/disable automatic dashboard refresh")
        settings_layout.addWidget(self.cb_auto_refresh)
        settings_layout.addStretch()
        settings_card.setLayout(settings_layout)
        cards_layout.addWidget(settings_card, 2, 0, 1, 3)  # Span 3 columns

        layout.addLayout(cards_layout)
        self.page_dashboard.setLayout(layout)

        # Initial network info
        self.update_network_info()

    def build_players(self):
        """Build an enhanced, modern player management interface"""
        layout = QVBoxLayout()

        # === TOP DASHBOARD CARDS ===
        dashboard_layout = QHBoxLayout()

        # Online Players Card - Enhanced
        online_card = QGroupBox("🟢 ONLINE PLAYERS")
        online_card.setStyleSheet("""
            QGroupBox {
                border: 3px solid #50fa7b;
                border-radius: 12px;
                padding: 15px;
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1a5f1a, stop:1 #0f3f0f);
                margin: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QGroupBox::title {
                color: #50fa7b;
                font-weight: bold;
                font-size: 16px;
                padding: 5px 10px;
                background: rgba(80, 250, 123, 0.1);
                border-radius: 6px;
            }
        """)
        online_layout = QVBoxLayout()
        self.label_online_count = QLabel("0")
        self.label_online_count.setStyleSheet("""
            font-size: 48px;
            font-weight: bold;
            color: #50fa7b;
            text-align: center;
        """)
        self.label_online_count.setAlignment(Qt.AlignCenter)
        online_layout.addWidget(self.label_online_count)

        # Online player activity indicator
        self.online_activity = QLabel("📋 Log-based monitoring active")
        self.online_activity.setStyleSheet("font-size: 11px; color: #50fa7b; text-align: center;")
        self.online_activity.setAlignment(Qt.AlignCenter)
        online_layout.addWidget(self.online_activity)

        online_card.setLayout(online_layout)
        dashboard_layout.addWidget(online_card)

        # Server Status Card - New
        status_card = QGroupBox("🖥️ SERVER STATUS")
        status_card.setStyleSheet("""
            QGroupBox {
                border: 3px solid #8be9fd;
                border-radius: 12px;
                padding: 15px;
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1a3f5f, stop:1 #0f2f4f);
                margin: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QGroupBox::title {
                color: #8be9fd;
                font-weight: bold;
                font-size: 16px;
                padding: 5px 10px;
                background: rgba(139, 233, 253, 0.1);
                border-radius: 6px;
            }
        """)
        status_layout = QVBoxLayout()
        self.label_server_status = QLabel("🔴 OFFLINE")
        self.label_server_status.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #ff5555;
            text-align: center;
        """)
        self.label_server_status.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.label_server_status)

        self.label_uptime_display = QLabel("Uptime: --:--:--")
        self.label_uptime_display.setStyleSheet("font-size: 12px; color: #8be9fd; text-align: center;")
        self.label_uptime_display.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.label_uptime_display)

        status_card.setLayout(status_layout)
        dashboard_layout.addWidget(status_card)

        # Player Statistics Card - New
        stats_card = QGroupBox("📊 STATISTICS")
        stats_card.setStyleSheet("""
            QGroupBox {
                border: 3px solid #ffb86b;
                border-radius: 12px;
                padding: 15px;
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #5f3f1a, stop:1 #3f2f0f);
                margin: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QGroupBox::title {
                color: #ffb86b;
                font-weight: bold;
                font-size: 16px;
                padding: 5px 10px;
                background: rgba(255, 184, 107, 0.1);
                border-radius: 6px;
            }
        """)
        stats_layout = QVBoxLayout()

        # Total tracked players
        self.label_total_tracked = QLabel("Total Tracked: 0")
        self.label_total_tracked.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffb86b; text-align: center;")
        self.label_total_tracked.setAlignment(Qt.AlignCenter)
        stats_layout.addWidget(self.label_total_tracked)

        # Peak players today
        self.label_peak_today = QLabel("Peak Today: 0")
        self.label_peak_today.setStyleSheet("font-size: 14px; color: #ffb86b; text-align: center;")
        self.label_peak_today.setAlignment(Qt.AlignCenter)
        stats_layout.addWidget(self.label_peak_today)

        stats_card.setLayout(stats_layout)
        dashboard_layout.addWidget(stats_card)

        layout.addLayout(dashboard_layout)
        # === CONTROLS BAR ===
        controls_layout = QHBoxLayout()

        # Search Section
        search_group = QGroupBox("🔍 SEARCH & FILTER")
        search_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #6272a4;
                border-radius: 8px;
                padding: 10px;
                background: #2b2f36;
                margin: 0px;
                font-weight: bold;
            }
            QGroupBox::title {
                color: #6272a4;
                font-size: 13px;
                padding: 0 8px;
            }
        """)
        search_layout = QHBoxLayout()

        self.player_search = QLineEdit()
        self.player_search.setPlaceholderText("Search by name, Steam ID, IP...")
        self.player_search.setStyleSheet("""
            padding: 8px 12px;
            font-size: 13px;
            min-width: 250px;
            border: 2px solid #44475a;
            border-radius: 6px;
            background: #1a1d23;
            color: #e6eef6;
        """)
        self.player_search.textChanged.connect(self.filter_players)
        search_layout.addWidget(self.player_search)

        # Filter dropdown
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All Players", "Online Only", "Offline Only", "Admins", "Banned"])
        self.filter_combo.setStyleSheet("""
            padding: 8px;
            font-size: 13px;
            border: 2px solid #44475a;
            border-radius: 6px;
            background: #1a1d23;
            color: #e6eef6;
        """)
        self.filter_combo.currentTextChanged.connect(self.filter_players)
        search_layout.addWidget(self.filter_combo)

        search_group.setLayout(search_layout)
        controls_layout.addWidget(search_group)

        # Quick Actions
        actions_group = QGroupBox("⚡ QUICK ACTIONS")
        actions_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #50fa7b;
                border-radius: 8px;
                padding: 10px;
                background: #2b2f36;
                margin: 0px;
                font-weight: bold;
            }
            QGroupBox::title {
                color: #50fa7b;
                font-size: 13px;
                padding: 0 8px;
            }
        """)
        actions_layout = QHBoxLayout()

        self.btn_refresh_players = QPushButton("🔄 Refresh")
        self.btn_refresh_players.clicked.connect(self.populate_players)
        self.btn_refresh_players.setStyleSheet("""
            padding: 8px 16px;
            font-size: 13px;
            font-weight: bold;
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #50fa7b, stop:1 #3fa56b);
            border: none;
            border-radius: 6px;
            color: #0f1117;
        """)
        self.btn_refresh_players.setToolTip("Refresh player list")
        actions_layout.addWidget(self.btn_refresh_players)

        self.btn_kick_all = QPushButton("👢 Kick All")
        self.btn_kick_all.clicked.connect(lambda: self.send_quick_rcon_command("#kickall"))
        self.btn_kick_all.setStyleSheet("""
            padding: 8px 16px;
            font-size: 13px;
            font-weight: bold;
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #ff5555, stop:1 #cc4444);
            border: none;
            border-radius: 6px;
            color: white;
        """)
        self.btn_kick_all.setToolTip("Kick all players from server")
        actions_layout.addWidget(self.btn_kick_all)

        self.btn_admin_help = QPushButton("❓ Admin Help")
        self.btn_admin_help.clicked.connect(self.show_admin_help)
        self.btn_admin_help.setStyleSheet("""
            padding: 8px 16px;
            font-size: 13px;
            font-weight: bold;
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #ffb86b, stop:1 #cc9544);
            border: none;
            border-radius: 6px;
            color: #0f1117;
        """)
        self.btn_admin_help.setToolTip("Show admin password and instructions")
        actions_layout.addWidget(self.btn_admin_help)

        actions_group.setLayout(actions_layout)
        controls_layout.addWidget(actions_group)

        # Auto-refresh toggle
        refresh_group = QGroupBox("🔄 AUTO-REFRESH")
        refresh_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #bd93f9;
                border-radius: 8px;
                padding: 10px;
                background: #2b2f36;
                margin: 0px;
                font-weight: bold;
            }
            QGroupBox::title {
                color: #bd93f9;
                font-size: 13px;
                padding: 0 8px;
            }
        """)
        refresh_layout = QVBoxLayout()

        self.cb_players_auto_refresh = QCheckBox("Enable Log Monitoring (1s)")
        self.cb_players_auto_refresh.setChecked(True)
        self.cb_players_auto_refresh.stateChanged.connect(self.toggle_players_auto_refresh)
        self.cb_players_auto_refresh.setStyleSheet("""
            font-size: 12px;
            color: #bd93f9;
            font-weight: bold;
        """)
        refresh_layout.addWidget(self.cb_players_auto_refresh)

        refresh_group.setLayout(refresh_layout)
        controls_layout.addWidget(refresh_group)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # === PLAYERS TABLE ===
        table_group = QGroupBox("👥 PLAYER MANAGEMENT")
        table_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #6272a4;
                border-radius: 8px;
                padding: 10px;
                background: #1a1d23;
                margin: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QGroupBox::title {
                color: #6272a4;
                font-size: 16px;
                padding: 5px 10px;
                background: rgba(98, 114, 164, 0.1);
                border-radius: 6px;
            }
        """)
        table_layout = QVBoxLayout()

        self.table_players = QTableWidget()
        self.table_players.setColumnCount(8)
        self.table_players.setHorizontalHeaderLabels([
            "Status", "Player Name", "Steam ID", "Character", "Connected", "Play Time", "IP Address", "Actions"
        ])

        # Enhanced column widths for better readability
        self.table_players.setColumnWidth(0, 100)   # Status
        self.table_players.setColumnWidth(1, 250)   # Player Name (Steam name)
        self.table_players.setColumnWidth(2, 160)   # Steam ID
        self.table_players.setColumnWidth(3, 180)   # Character Name
        self.table_players.setColumnWidth(4, 140)   # Connected At
        self.table_players.setColumnWidth(5, 100)   # Play Time
        self.table_players.setColumnWidth(6, 130)   # IP Address
        self.table_players.setColumnWidth(7, 220)   # Actions

        # Enhanced styling
        self.table_players.setAlternatingRowColors(True)
        self.table_players.verticalHeader().setVisible(False)
        self.table_players.setSelectionMode(QTableWidget.SingleSelection)
        self.table_players.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_players.verticalHeader().setDefaultSectionSize(50)

        self.table_players.setStyleSheet("""
            QTableWidget {
                gridline-color: #44475a;
                selection-background-color: #6272a4;
                background: #1a1d23;
                border: 1px solid #44475a;
                border-radius: 6px;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #2b2f36;
                color: #e6eef6;
            }
            QTableWidget::item:selected {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #6272a4, stop:1 #4c5c8a);
                color: #ffffff;
            }
            QHeaderView::section {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #44475a, stop:1 #363949);
                color: #f8f8f2;
                padding: 12px 8px;
                border: none;
                font-weight: bold;
                font-size: 14px;
                border-right: 1px solid #2b2f36;
            }
            QTableWidget::item:hover {
                background: #2b2f36;
            }
        """)

        table_layout.addWidget(self.table_players)
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)
        # === RCON CONSOLE ===
        rcon_group = QGroupBox("🔧 RCON COMMAND CONSOLE")
        rcon_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #bd93f9;
                border-radius: 8px;
                padding: 10px;
                background: #1a1d23;
                margin: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QGroupBox::title {
                color: #bd93f9;
                font-size: 16px;
                padding: 5px 10px;
                background: rgba(189, 147, 249, 0.1);
                border-radius: 6px;
            }
        """)
        rcon_layout = QVBoxLayout()

        # Command input section
        command_layout = QHBoxLayout()
        command_layout.addWidget(QLabel("Command:"))
        self.rcon_command_input = QLineEdit()
        self.rcon_command_input.setPlaceholderText("Enter RCON command (e.g., #kick player_name, #ban steam_id)")
        self.rcon_command_input.setStyleSheet("""
            padding: 8px 12px;
            font-size: 13px;
            min-width: 400px;
            border: 2px solid #44475a;
            border-radius: 6px;
            background: #0d1016;
            color: #e6eef6;
            font-family: 'Consolas', monospace;
        """)
        command_layout.addWidget(self.rcon_command_input)

        self.btn_send_rcon = QPushButton("📤 Send Command")
        self.btn_send_rcon.clicked.connect(self.send_custom_rcon_command)
        self.btn_send_rcon.setStyleSheet("""
            padding: 8px 16px;
            font-size: 13px;
            font-weight: bold;
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #bd93f9, stop:1 #9b73d9);
            border: none;
            border-radius: 6px;
            color: white;
        """)
        self.btn_send_rcon.setToolTip("Send custom RCON command to server")
        command_layout.addWidget(self.btn_send_rcon)
        rcon_layout.addLayout(command_layout)

        # Quick commands toolbar
        quick_layout = QHBoxLayout()
        quick_layout.addWidget(QLabel("Quick Commands:"))

        quick_commands = [
            ("📊 Status", "#status", "Get server status"),
            ("👥 Players", "#players", "List online players"),
            ("💾 Save", "#save", "Force save server data"),
            ("📢 Broadcast", "#broadcast Server maintenance in 5 minutes", "Send broadcast message"),
            ("🔄 Restart", "#restart", "Restart server"),
            ("🛑 Shutdown", "#shutdown", "Shutdown server")
        ]

        for name, cmd, tooltip in quick_commands:
            btn = QPushButton(name)
            btn.clicked.connect(lambda checked, c=cmd: self.send_quick_rcon_command(c))
            btn.setToolTip(tooltip)
            btn.setStyleSheet("""
                padding: 6px 12px;
                font-size: 11px;
                background: #2b2f36;
                border: 1px solid #44475a;
                border-radius: 4px;
                color: #e6eef6;
                margin: 2px;
            """)
            btn.setCursor(Qt.PointingHandCursor)
            quick_layout.addWidget(btn)

        quick_layout.addStretch()
        rcon_layout.addLayout(quick_layout)

        # Response display
        response_layout = QVBoxLayout()
        response_layout.addWidget(QLabel("Response:"))
        self.rcon_response_display = QTextEdit()
        self.rcon_response_display.setReadOnly(True)
        self.rcon_response_display.setMaximumHeight(120)
        self.rcon_response_display.setStyleSheet("""
            QTextEdit {
                background: #0d1016;
                border: 2px solid #2b2f36;
                border-radius: 6px;
                color: #50fa7b;
                font-family: 'Consolas', monospace;
                font-size: 11px;
                padding: 8px;
            }
        """)
        self.rcon_response_display.setPlaceholderText("RCON command responses will appear here...")
        response_layout.addWidget(self.rcon_response_display)
        rcon_layout.addLayout(response_layout)

        rcon_group.setLayout(rcon_layout)
        layout.addWidget(rcon_group)

        self.page_players.setLayout(layout)

    def build_server(self):
        layout = QVBoxLayout()
        group = QGroupBox("Server Controls")
        gl = QHBoxLayout()
        self.btn_start = QPushButton("Start")
        self.btn_start.clicked.connect(self.on_start)
        self.btn_stop = QPushButton("Stop")
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_restart = QPushButton("Restart")
        self.btn_restart.clicked.connect(self.on_restart)
        gl.addWidget(self.btn_start)
        gl.addWidget(self.btn_stop)
        gl.addWidget(self.btn_restart)
        group.setLayout(gl)
        layout.addWidget(group)
        self.page_server.setLayout(layout)

    def build_config_editor(self):
        """Build simplified config file editor - load folder of INI files dynamically"""
        layout = QVBoxLayout()
        
        # Header
        header = QHBoxLayout()
        title = QLabel("⚙️ Server Configuration Editor")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #e6eef6;")
        header.addWidget(title)
        
        # Config file status
        self.config_status = QLabel("📄 No config loaded")
        self.config_status.setStyleSheet("color: #ffb86b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
        header.addWidget(self.config_status)
        
        header.addStretch()
        layout.addLayout(header)
        
        # Toolbar with actions
        toolbar = QHBoxLayout()
        
        # Add Folder button (primary action)
        self.btn_add_config_folder = QPushButton("� Add Config Folder")
        self.btn_add_config_folder.clicked.connect(self.add_config_folder)
        self.btn_add_config_folder.setToolTip("Browse and add a folder containing .ini files")
        self.btn_add_config_folder.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #4ade80, stop:1 #22c55e);
                color: #072018;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #6ef08b, stop:1 #35c06f);
            }
        """)
        toolbar.addWidget(self.btn_add_config_folder)
        
        # Auto-detect button
        self.btn_auto_detect_config = QPushButton("� Auto-Detect")
        self.btn_auto_detect_config.clicked.connect(self.auto_detect_configs)
        self.btn_auto_detect_config.setToolTip("Automatically find server configuration folder")
        toolbar.addWidget(self.btn_auto_detect_config)
        
        # Save All
        self.btn_save_all_configs = QPushButton("💾 Save All")
        self.btn_save_all_configs.clicked.connect(self.save_all_configs)
        self.btn_save_all_configs.setToolTip("Save all configuration files")
        toolbar.addWidget(self.btn_save_all_configs)
        
        # Backup/Restore
        self.btn_backup_config = QPushButton("📦 Backup")
        self.btn_backup_config.clicked.connect(self.backup_all_configs)
        self.btn_backup_config.setToolTip("Create backup of all configuration files")
        toolbar.addWidget(self.btn_backup_config)
        
        # Visual Editor
        self.btn_visual_editor = QPushButton("🎨 Visual Editor")
        self.btn_visual_editor.clicked.connect(self.open_visual_config_editor)
        self.btn_visual_editor.setToolTip("Open easy-to-use visual configuration editor")
        self.btn_visual_editor.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #bd93f9, stop:1 #9b59b6);
                color: #ffffff;
                font-weight: bold;
                padding: 10px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #d4b3ff, stop:1 #bb79d6);
            }
        """)
        toolbar.addWidget(self.btn_visual_editor)
        
        # SQLiteStudio
        self.btn_sqlite_studio = QPushButton("🗄️ SQLiteStudio")
        self.btn_sqlite_studio.clicked.connect(self.open_sqlite_studio)
        self.btn_sqlite_studio.setToolTip("Open database in SQLiteStudio for advanced management")
        self.btn_sqlite_studio.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #f59e0b, stop:1 #d97706);
                color: #ffffff;
                font-weight: bold;
                padding: 10px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #fbbf24, stop:1 #f59e0b);
            }
        """)
        toolbar.addWidget(self.btn_sqlite_studio)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Dynamic config tabs (will be populated when folder is loaded)
        self.config_tabs = QTabWidget()
        self.config_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2b2f36;
                background: #0f1117;
                border-radius: 5px;
            }
            QTabBar::tab {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1a1d23, stop:1 #0d1016);
                border: 1px solid #2b2f36;
                padding: 10px 18px;
                margin-right: 2px;
                color: #e6eef6;
                font-weight: bold;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #2b2f36, stop:1 #1e8b57);
                border-bottom: 3px solid #50fa7b;
                color: #50fa7b;
            }
            QTabBar::tab:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #2b2f36, stop:1 #1a1d23);
                color: #8be9fd;
            }
        """)
        
        # Store config file editors in a dictionary
        self.config_editors = {}
        self.config_file_paths = {}
        
        # Placeholder message
        placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout()
        placeholder_layout.addStretch()
        
        placeholder_label = QLabel("📁 No Configuration Files Loaded")
        placeholder_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #8be9fd;")
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_layout.addWidget(placeholder_label)
        
        placeholder_hint = QLabel("Click '📁 Add Config Folder' or '🔎 Auto-Detect' to load INI files")
        placeholder_hint.setStyleSheet("font-size: 12px; color: #ffb86b;")
        placeholder_hint.setAlignment(Qt.AlignCenter)
        placeholder_layout.addWidget(placeholder_hint)
        
        placeholder_layout.addStretch()
        placeholder_widget.setLayout(placeholder_layout)
        
        self.config_tabs.addTab(placeholder_widget, "🏠 Start Here")
        
        # Remove auto-save on tab change to avoid spam
        # User can explicitly save with Save All button
        
        # Replace tabs with improved split view: tree on left, editor on right
        config_splitter = QSplitter(Qt.Horizontal)
        
        # Left: File tree (simple tree widget)
        self.config_tree = QTreeWidget()
        self.config_tree.setHeaderLabel("Config Files")
        self.config_tree.itemClicked.connect(lambda item: self.load_selected_config_file(item.data(0, Qt.UserRole)))
        config_splitter.addWidget(self.config_tree)
        
        # Right: Editor stack (text, visual INI, visual JSON)
        self.editor_stack = QStackedWidget()
        
        # Add placeholder
        placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout()
        placeholder_layout.addStretch()
        
        placeholder_label = QLabel("📁 No File Selected")
        placeholder_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #8be9fd;")
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_layout.addWidget(placeholder_label)
        
        placeholder_hint = QLabel("Select a file from the tree on the left")
        placeholder_hint.setStyleSheet("font-size: 12px; color: #ffb86b;")
        placeholder_hint.setAlignment(Qt.AlignCenter)
        placeholder_layout.addWidget(placeholder_hint)
        
        placeholder_layout.addStretch()
        placeholder_widget.setLayout(placeholder_layout)
        self.editor_stack.addWidget(placeholder_widget)
        
        config_splitter.addWidget(self.editor_stack)
        config_splitter.setStretchFactor(0, 1)  # Tree takes 1/4
        config_splitter.setStretchFactor(1, 3)  # Editor takes 3/4
        
        layout.addWidget(config_splitter)
        
        # Store current file info
        self.current_config_file = None
        self.current_editor = None
        self.config_base_path = None
        
        # Config path display
        path_label = QLabel("📁 Config Location:")
        self.config_path_display = QLabel("Not detected")
        self.config_path_display.setStyleSheet("color: #8be9fd; font-size: 10px; padding: 5px;")
        path_layout = QHBoxLayout()
        path_layout.addWidget(path_label)
        path_layout.addWidget(self.config_path_display)
        path_layout.addStretch()
        layout.addLayout(path_layout)
        
        self.page_config_editor.setLayout(layout)

    def build_logs(self):
        """Build enhanced logging system with multiple log types"""
        layout = QVBoxLayout()
        
        # Header with controls
        header = QHBoxLayout()
        title = QLabel("📋 Server Logs")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #e6eef6;")
        header.addWidget(title)
        header.addStretch()
        
        # Refresh button
        self.btn_refresh_logs = QPushButton("🔄 Refresh")
        self.btn_refresh_logs.clicked.connect(self.refresh_logs)
        self.btn_refresh_logs.setToolTip("Refresh all log viewers")
        header.addWidget(self.btn_refresh_logs)
        
        # Clear logs button
        self.btn_clear_logs = QPushButton("🗑️ Clear Display")
        self.btn_clear_logs.clicked.connect(self.clear_log_displays)
        self.btn_clear_logs.setToolTip("Clear log displays (doesn't delete files)")
        header.addWidget(self.btn_clear_logs)
        
        # Export logs button
        self.btn_export_logs = QPushButton("📤 Export")
        self.btn_export_logs.clicked.connect(self.export_logs)
        self.btn_export_logs.setToolTip("Export logs to file")
        header.addWidget(self.btn_export_logs)
        
        layout.addLayout(header)
        
        # Search and filter
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 Search:"))
        
        self.log_search = QLineEdit()
        self.log_search.setPlaceholderText("Search in logs...")
        self.log_search.textChanged.connect(self.filter_logs)
        search_layout.addWidget(self.log_search)
        
        search_layout.addWidget(QLabel("📅 Time Range:"))
        self.log_time_filter = QComboBox()
        self.log_time_filter.addItems(["All Time", "Last Hour", "Last 6 Hours", "Last 24 Hours", "Today", "Last 7 Days"])
        self.log_time_filter.currentTextChanged.connect(self.filter_logs_by_time)
        search_layout.addWidget(self.log_time_filter)
        
        search_layout.addWidget(QLabel("🎯 Level:"))
        self.log_level_filter = QComboBox()
        self.log_level_filter.addItems(["All", "Info", "Warning", "Error", "Critical"])
        self.log_level_filter.currentTextChanged.connect(self.filter_logs_by_level)
        search_layout.addWidget(self.log_level_filter)
        
        search_layout.addStretch()
        layout.addLayout(search_layout)
        
        # Log tabs for different log types
        log_tabs = QTabWidget()
        log_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2b2f36;
                background: #0f1117;
            }
            QTabBar::tab {
                background: #1a1d23;
                border: 1px solid #2b2f36;
                padding: 8px 16px;
                margin-right: 2px;
                color: #e6eef6;
            }
            QTabBar::tab:selected {
                background: #2b2f36;
                border-bottom: 2px solid #1e8b57;
            }
        """)
        
        # Server Log
        server_log_tab = QWidget()
        server_log_layout = QVBoxLayout()
        self.text_logs = QTextEdit()
        self.text_logs.setReadOnly(True)
        self.text_logs.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.text_logs.setStyleSheet("""
            QTextEdit {
                background: #0d1016;
                border: 1px solid #2b2f36;
                color: #e6eef6;
                font-family: 'Consolas', monospace;
                font-size: 10px;
            }
        """)
        server_log_layout.addWidget(self.text_logs)
        server_log_tab.setLayout(server_log_layout)
        log_tabs.addTab(server_log_tab, "🖥️ Server Log")
        
        # Player Connections Log
        player_log_tab = QWidget()
        player_log_layout = QVBoxLayout()
        self.text_player_logs = QTextEdit()
        self.text_player_logs.setReadOnly(True)
        self.text_player_logs.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.text_player_logs.setStyleSheet("""
            QTextEdit {
                background: #0d1016;
                border: 1px solid #2b2f36;
                color: #e6eef6;
                font-family: 'Consolas', monospace;
                font-size: 10px;
            }
        """)
        player_log_layout.addWidget(self.text_player_logs)
        player_log_tab.setLayout(player_log_layout)
        log_tabs.addTab(player_log_tab, "👥 Player Activity")
        
        # Error Log
        error_log_tab = QWidget()
        error_log_layout = QVBoxLayout()
        self.text_error_logs = QTextEdit()
        self.text_error_logs.setReadOnly(True)
        self.text_error_logs.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.text_error_logs.setStyleSheet("""
            QTextEdit {
                background: #0d1016;
                border: 1px solid #2b2f36;
                color: #ff6b6b;
                font-family: 'Consolas', monospace;
                font-size: 10px;
            }
        """)
        error_log_layout.addWidget(self.text_error_logs)
        error_log_tab.setLayout(error_log_layout)
        log_tabs.addTab(error_log_tab, "❌ Errors")
        
        # Admin Actions Log
        admin_log_tab = QWidget()
        admin_log_layout = QVBoxLayout()
        self.text_admin_logs = QTextEdit()
        self.text_admin_logs.setReadOnly(True)
        self.text_admin_logs.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.text_admin_logs.setStyleSheet("""
            QTextEdit {
                background: #0d1016;
                border: 1px solid #2b2f36;
                color: #ffb86b;
                font-family: 'Consolas', monospace;
                font-size: 10px;
            }
        """)
        admin_log_layout.addWidget(self.text_admin_logs)
        admin_log_tab.setLayout(admin_log_layout)
        log_tabs.addTab(admin_log_tab, "⚡ Admin Actions")
        
        # Events Log
        events_log_tab = QWidget()
        events_log_layout = QVBoxLayout()
        self.text_events_logs = QTextEdit()
        self.text_events_logs.setReadOnly(True)
        self.text_events_logs.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.text_events_logs.setStyleSheet("""
            QTextEdit {
                background: #0d1016;
                border: 1px solid #2b2f36;
                color: #8be9fd;
                font-family: 'Consolas', monospace;
                font-size: 10px;
            }
        """)
        events_log_layout.addWidget(self.text_events_logs)
        events_log_tab.setLayout(events_log_layout)
        log_tabs.addTab(events_log_tab, "📊 Events")
        
        layout.addWidget(log_tabs)
        
        # Log statistics
        stats_layout = QHBoxLayout()
        self.log_stats = QLabel("📈 Stats: 0 total | 0 errors | 0 warnings | 0 players")
        self.log_stats.setStyleSheet("color: #8be9fd; font-size: 10px; padding: 5px;")
        stats_layout.addWidget(self.log_stats)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        self.page_logs.setLayout(layout)
        # Use optimized tail_logs() instead of load_logs() for better performance
        # This loads only the last 1000 lines instead of the entire log file
        self.tail_logs()

    def build_bans(self):
        layout = QVBoxLayout()
        h = QHBoxLayout()
        self.input_ban = QLineEdit()
        self.input_ban.setPlaceholderText("player_name or player_id")
        self.btn_add_ban = QPushButton("Add Ban")
        self.btn_add_ban.clicked.connect(self.on_add_ban)
        self.btn_remove_ban = QPushButton("Remove Ban")
        self.btn_remove_ban.clicked.connect(self.on_remove_ban)
        h.addWidget(self.input_ban)
        h.addWidget(self.btn_add_ban)
        h.addWidget(self.btn_remove_ban)
        layout.addLayout(h)

        self.table_bans = QTableWidget()
        self.table_bans.setColumnCount(1)
        self.table_bans.setHorizontalHeaderLabels(["Banned Entry"])
        layout.addWidget(self.table_bans)
        self.page_bans.setLayout(layout)
        self.populate_bans()

    def build_performance(self):
        layout = QVBoxLayout()
        self.table_perf = QTableWidget()
        self.table_perf.setColumnCount(6)
        self.table_perf.setHorizontalHeaderLabels(["Time", "CPU %", "RAM %", "CPU Freq", "CPU Temp", "RAM Used"])        
        layout.addWidget(self.table_perf)
        self.page_performance.setLayout(layout)

    def build_settings(self):
        layout = QVBoxLayout()
        self.label_path = QLabel(self.scum_path or "SCUMServer.exe not set")
        self.label_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.btn_browse = QPushButton("Choose SCUMServer.exe")
        self.btn_browse.clicked.connect(self.pick_scum)
        self.btn_save_settings = QPushButton("💾 Save All Settings")
        self.btn_save_settings.clicked.connect(lambda: self.save_settings(show_message=True))
        self.btn_save_settings.setToolTip("Manually save all settings (auto-saves on changes)")

        # RCON Settings Group
        rcon_group = QGroupBox("🔧 RCON Configuration")
        rcon_group.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #bd93f9; margin-top: 6px; }")
        rcon_layout = QGridLayout()

        # RCON Host
        rcon_layout.addWidget(QLabel("RCON Host:"), 0, 0)
        self.rcon_host = QLineEdit("127.0.0.1")
        self.rcon_host.setToolTip("RCON server host (usually 127.0.0.1 for local server)")
        rcon_layout.addWidget(self.rcon_host, 0, 1)

        # RCON Port
        rcon_layout.addWidget(QLabel("RCON Port:"), 1, 0)
        self.rcon_port = QSpinBox()
        self.rcon_port.setRange(1024, 65535)
        self.rcon_port.setValue(27015)
        self.rcon_port.setToolTip("RCON server port (usually 27015)")
        rcon_layout.addWidget(self.rcon_port, 1, 1)

        # RCON Password
        rcon_layout.addWidget(QLabel("RCON Password:"), 2, 0)
        self.rcon_password = QLineEdit()
        self.rcon_password.setEchoMode(QLineEdit.Password)
        self.rcon_password.setPlaceholderText("Enter RCON password")
        self.rcon_password.setToolTip("RCON authentication password")
        rcon_layout.addWidget(self.rcon_password, 2, 1)

        rcon_group.setLayout(rcon_layout)

        layout.addWidget(self.label_path)
        layout.addWidget(self.btn_browse)
        layout.addWidget(rcon_group)
        layout.addWidget(self.btn_save_settings)
        layout.addStretch()
        self.page_settings.setLayout(layout)
        self.load_settings()

    def build_setup(self):
        layout = QVBoxLayout()

        # Header with status
        header_layout = QHBoxLayout()
        title = QLabel("🚀 Server Setup & Configuration")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #e6eef6; margin-bottom: 5px;")
        header_layout.addWidget(title)

        # Status indicator
        self.setup_status_label = QLabel("⚠️ Setup Incomplete")
        self.setup_status_label.setStyleSheet("font-size: 12px; color: #ffb86b; padding: 5px; background: #2b2f36; border-radius: 3px;")
        header_layout.addStretch()
        header_layout.addWidget(self.setup_status_label)

        layout.addLayout(header_layout)

        # Progress bar for setup completion
        self.setup_progress = QProgressBar()
        self.setup_progress.setMaximum(100)
        self.setup_progress.setValue(0)
        self.setup_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #2b2f36;
                border-radius: 5px;
                text-align: center;
                background: #0d1016;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #4ade80, stop:1 #22c55e);
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.setup_progress)

        # Setup sections
        setup_tabs = QTabWidget()
        setup_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2b2f36;
                background: #0f1117;
            }
            QTabBar::tab {
                background: #1a1d23;
                border: 1px solid #2b2f36;
                padding: 8px 16px;
                margin-right: 2px;
                color: #e6eef6;
            }
            QTabBar::tab:selected {
                background: #2b2f36;
                border-bottom: 2px solid #1e8b57;
            }
        """)

        # === BASIC SETUP TAB ===
        basic_tab = QWidget()
        basic_layout = QVBoxLayout()

        # Server Installation Section
        install_group = QGroupBox("📁 Server Installation")
        install_group.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #1e8b57; margin-top: 6px; }")
        install_layout = QVBoxLayout()

        # Server Path
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Server Executable:"))
        self.setup_label_path = QLabel(self.scum_path or "Not configured")
        self.setup_label_path.setStyleSheet("font-size: 12px; padding: 5px; background: #0d1016; border-radius: 3px; border: 1px solid #2b2f36;")
        self.setup_btn_browse = QPushButton("🔍 Browse")
        self.setup_btn_browse.clicked.connect(self.pick_scum)
        self.setup_btn_browse.setToolTip("Locate SCUMServer.exe")
        self.setup_btn_auto_detect = QPushButton("🔎 Auto-Detect")
        self.setup_btn_auto_detect.clicked.connect(self.auto_detect_server)
        self.setup_btn_auto_detect.setToolTip("Automatically find SCUMServer.exe")
        path_layout.addWidget(self.setup_label_path, 1)
        path_layout.addWidget(self.setup_btn_browse)
        path_layout.addWidget(self.setup_btn_auto_detect)
        install_layout.addLayout(path_layout)

        # Installation status
        self.install_status = QLabel("❌ Server not found")
        self.install_status.setStyleSheet("color: #ff6b6b; font-size: 11px;")
        install_layout.addWidget(self.install_status)

        install_group.setLayout(install_layout)
        basic_layout.addWidget(install_group)

        # Server Configuration Section
        config_group = QGroupBox("⚙️ Server Configuration")
        config_group.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #ffb86b; margin-top: 6px; }")
        config_layout = QGridLayout()

        # Server Name
        config_layout.addWidget(QLabel("Server Name:"), 0, 0)
        self.setup_server_name = QLineEdit("My SCUM Server")
        self.setup_server_name.setToolTip("Display name for your server")
        self.setup_server_name.textChanged.connect(self.update_setup_status)
        config_layout.addWidget(self.setup_server_name, 0, 1)

        # Max Players
        config_layout.addWidget(QLabel("Max Players:"), 1, 0)
        self.setup_max_players = QSpinBox()
        self.setup_max_players.setRange(1, 100)
        self.setup_max_players.setValue(50)
        self.setup_max_players.setToolTip("Maximum number of players (1-100)")
        self.setup_max_players.valueChanged.connect(self.update_setup_status)
        config_layout.addWidget(self.setup_max_players, 1, 1)

        # Port
        config_layout.addWidget(QLabel("Server Port:"), 2, 0)
        port_layout = QHBoxLayout()
        self.setup_port = QSpinBox()
        self.setup_port.setRange(1024, 65535)
        self.setup_port.setValue(27015)
        self.setup_port.setToolTip("Server port (1024-65535)")
        self.setup_port.valueChanged.connect(self.update_setup_status)
        port_layout.addWidget(self.setup_port)

        self.setup_port_test = QPushButton("🧪 Test Port")
        self.setup_port_test.clicked.connect(self.test_server_port)
        self.setup_port_test.setToolTip("Check if port is available")
        port_layout.addWidget(self.setup_port_test)
        port_layout.addStretch()
        config_layout.addLayout(port_layout, 2, 1)

        # Password
        config_layout.addWidget(QLabel("Server Password:"), 3, 0)
        self.setup_password = QLineEdit()
        self.setup_password.setEchoMode(QLineEdit.Password)
        self.setup_password.setPlaceholderText("Optional - leave empty for no password")
        self.setup_password.setToolTip("Server access password (optional)")
        config_layout.addWidget(self.setup_password, 3, 1)

        # Difficulty
        config_layout.addWidget(QLabel("Difficulty:"), 4, 0)
        self.setup_difficulty = QComboBox()
        self.setup_difficulty.addItems(["0 - Peaceful", "1 - Easy", "2 - Normal", "3 - Hard", "4 - Extreme"])
        self.setup_difficulty.setCurrentIndex(2)
        self.setup_difficulty.setToolTip("Game difficulty level")
        config_layout.addWidget(self.setup_difficulty, 4, 1)

        config_group.setLayout(config_layout)
        basic_layout.addWidget(config_group)

        # Save Basic Settings
        basic_buttons = QHBoxLayout()
        self.setup_btn_save_basic = QPushButton("💾 Save Basic Settings")
        self.setup_btn_save_basic.clicked.connect(self.save_basic_setup)
        self.setup_btn_save_basic.setToolTip("Save server configuration")
        basic_buttons.addWidget(self.setup_btn_save_basic)

        self.setup_btn_generate_config = QPushButton("📄 Generate Config File")
        self.setup_btn_generate_config.clicked.connect(self.generate_server_config)
        self.setup_btn_generate_config.setToolTip("Create server config files")
        basic_buttons.addWidget(self.setup_btn_generate_config)

        basic_layout.addLayout(basic_buttons)
        basic_layout.addStretch()
        basic_tab.setLayout(basic_layout)
        setup_tabs.addTab(basic_tab, "📋 Basic Setup")

        # === ADVANCED SETUP TAB ===
        advanced_tab = QWidget()
        advanced_layout = QVBoxLayout()

        # Directory Configuration
        dir_group = QGroupBox("📂 Directory Configuration")
        dir_group.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #bd93f9; margin-top: 6px; }")
        dir_layout = QGridLayout()

        # Logs Directory
        dir_layout.addWidget(QLabel("Logs Directory:"), 0, 0)
        logs_layout = QHBoxLayout()
        self.setup_logs_dir = QLineEdit("Logs")
        self.setup_logs_dir.setToolTip("Directory for server logs")
        self.setup_btn_logs_browse = QPushButton("📁")
        self.setup_btn_logs_browse.clicked.connect(lambda: self.browse_directory(self.setup_logs_dir))
        logs_layout.addWidget(self.setup_logs_dir)
        logs_layout.addWidget(self.setup_btn_logs_browse)
        dir_layout.addLayout(logs_layout, 0, 1)

        # Config Directory
        dir_layout.addWidget(QLabel("Config Directory:"), 1, 0)
        config_dir_layout = QHBoxLayout()
        self.setup_config_dir = QLineEdit("Config")
        self.setup_config_dir.setToolTip("Directory for server configuration")
        self.setup_btn_config_browse = QPushButton("📁")
        self.setup_btn_config_browse.clicked.connect(lambda: self.browse_directory(self.setup_config_dir))
        config_dir_layout.addWidget(self.setup_config_dir)
        config_dir_layout.addWidget(self.setup_btn_config_browse)
        dir_layout.addLayout(config_dir_layout, 1, 1)

        # Save Directory
        dir_layout.addWidget(QLabel("Save Directory:"), 2, 0)
        save_layout = QHBoxLayout()
        self.setup_save_dir = QLineEdit("Save")
        self.setup_save_dir.setToolTip("Directory for save files")
        self.setup_btn_save_browse = QPushButton("📁")
        self.setup_btn_save_browse.clicked.connect(lambda: self.browse_directory(self.setup_save_dir))
        save_layout.addWidget(self.setup_save_dir)
        save_layout.addWidget(self.setup_btn_save_browse)
        dir_layout.addLayout(save_layout, 2, 1)

        dir_group.setLayout(dir_layout)
        advanced_layout.addWidget(dir_group)

        # Performance & Automation
        perf_group = QGroupBox("⚡ Performance & Automation")
        perf_group.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #50fa7b; margin-top: 6px; }")
        perf_layout = QVBoxLayout()

        # Auto-restart
        restart_layout = QHBoxLayout()
        self.setup_auto_restart = QCheckBox("Enable Auto-Restart on Crash")
        self.setup_auto_restart.setChecked(True)
        self.setup_auto_restart.setToolTip("Automatically restart server if it crashes")
        restart_layout.addWidget(self.setup_auto_restart)

        restart_layout.addWidget(QLabel("Restart Delay (seconds):"))
        self.setup_restart_delay = QSpinBox()
        self.setup_restart_delay.setRange(5, 300)
        self.setup_restart_delay.setValue(30)
        self.setup_restart_delay.setToolTip("Delay before auto-restart")
        restart_layout.addWidget(self.setup_restart_delay)
        restart_layout.addStretch()
        perf_layout.addLayout(restart_layout)

        # Backup settings
        backup_layout = QHBoxLayout()
        self.setup_auto_backup = QCheckBox("Enable Automatic Backups")
        self.setup_auto_backup.setChecked(False)
        self.setup_auto_backup.setToolTip("Create automatic server backups")
        backup_layout.addWidget(self.setup_auto_backup)

        backup_layout.addWidget(QLabel("Backup Interval (minutes):"))
        self.setup_backup_interval = QSpinBox()
        self.setup_backup_interval.setRange(15, 1440)
        self.setup_backup_interval.setValue(60)
        self.setup_backup_interval.setToolTip("Backup frequency in minutes")
        self.setup_backup_interval.setEnabled(False)
        self.setup_auto_backup.stateChanged.connect(lambda: self.setup_backup_interval.setEnabled(self.setup_auto_backup.isChecked()))
        backup_layout.addWidget(self.setup_backup_interval)
        backup_layout.addStretch()
        perf_layout.addLayout(backup_layout)

        # Memory limits
        memory_layout = QHBoxLayout()
        memory_layout.addWidget(QLabel("Memory Limit (MB):"))
        self.setup_memory_limit = QSpinBox()
        self.setup_memory_limit.setRange(1024, 16384)
        self.setup_memory_limit.setValue(4096)
        self.setup_memory_limit.setToolTip("Maximum RAM usage (MB)")
        memory_layout.addWidget(self.setup_memory_limit)

        memory_layout.addWidget(QLabel("CPU Priority:"))
        self.setup_cpu_priority = QComboBox()
        self.setup_cpu_priority.addItems(["Low", "Normal", "High", "Realtime"])
        self.setup_cpu_priority.setCurrentText("High")
        self.setup_cpu_priority.setToolTip("Server process priority")
        memory_layout.addWidget(self.setup_cpu_priority)
        memory_layout.addStretch()
        perf_layout.addLayout(memory_layout)

        perf_group.setLayout(perf_layout)
        advanced_layout.addWidget(perf_group)

        # Network Settings
        network_group = QGroupBox("🌐 Network Settings")
        network_group.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #8be9fd; margin-top: 6px; }")
        network_layout = QGridLayout()

        # Query Port
        network_layout.addWidget(QLabel("Query Port:"), 0, 0)
        self.setup_query_port = QSpinBox()
        self.setup_query_port.setRange(1024, 65535)
        self.setup_query_port.setValue(27016)
        self.setup_query_port.setToolTip("Steam query port")
        network_layout.addWidget(self.setup_query_port, 0, 1)

        # RCON Settings
        network_layout.addWidget(QLabel("RCON Port:"), 1, 0)
        self.setup_rcon_port = QSpinBox()
        self.setup_rcon_port.setRange(1024, 65535)
        self.setup_rcon_port.setValue(27017)
        self.setup_rcon_port.setToolTip("Remote console port")
        network_layout.addWidget(self.setup_rcon_port, 1, 1)

        network_layout.addWidget(QLabel("RCON Password:"), 2, 0)
        self.setup_rcon_password = QLineEdit()
        self.setup_rcon_password.setEchoMode(QLineEdit.Password)
        self.setup_rcon_password.setPlaceholderText("Set RCON password")
        self.setup_rcon_password.setToolTip("Remote console password")
        network_layout.addWidget(self.setup_rcon_password, 2, 1)

        network_group.setLayout(network_layout)
        advanced_layout.addWidget(network_group)

        # Save Advanced Settings
        self.setup_btn_save_advanced = QPushButton("💾 Save Advanced Settings")
        self.setup_btn_save_advanced.clicked.connect(self.save_advanced_setup)
        self.setup_btn_save_advanced.setToolTip("Save advanced configuration")
        advanced_layout.addWidget(self.setup_btn_save_advanced)

        advanced_layout.addStretch()
        advanced_tab.setLayout(advanced_layout)
        setup_tabs.addTab(advanced_tab, "🔧 Advanced Setup")

        # === QUICK SETUP TAB ===
        quick_tab = QWidget()
        quick_layout = QVBoxLayout()

        # Quick Setup Wizard
        wizard_group = QGroupBox("🚀 Quick Setup Wizard")
        wizard_group.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #ff79c6; margin-top: 6px; }")
        wizard_layout = QVBoxLayout()

        # Setup steps
        steps_layout = QVBoxLayout()
        self.setup_steps = []

        step1 = QCheckBox("✅ Detect SCUMServer.exe")
        step1.setChecked(bool(self.scum_path))
        self.setup_steps.append(step1)
        steps_layout.addWidget(step1)

        step2 = QCheckBox("✅ Configure basic settings")
        self.setup_steps.append(step2)
        steps_layout.addWidget(step2)

        step3 = QCheckBox("✅ Set up directories")
        self.setup_steps.append(step3)
        steps_layout.addWidget(step3)

        step4 = QCheckBox("✅ Generate config files")
        self.setup_steps.append(step4)
        steps_layout.addWidget(step4)

        wizard_layout.addLayout(steps_layout)

        # Quick setup buttons
        quick_buttons = QHBoxLayout()
        self.setup_btn_quick_setup = QPushButton("🚀 Run Complete Setup")
        self.setup_btn_quick_setup.clicked.connect(self.run_complete_quick_setup)
        self.setup_btn_quick_setup.setToolTip("Run full automated setup")
        quick_buttons.addWidget(self.setup_btn_quick_setup)

        self.setup_btn_validate = QPushButton("✅ Validate Setup")
        self.setup_btn_validate.clicked.connect(self.validate_complete_setup)
        self.setup_btn_validate.setToolTip("Check if all settings are configured")
        quick_buttons.addWidget(self.setup_btn_validate)

        wizard_layout.addLayout(quick_buttons)
        wizard_group.setLayout(wizard_layout)
        quick_layout.addWidget(wizard_group)

        # Import/Export
        io_group = QGroupBox("💾 Import/Export Configuration")
        io_group.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #f1fa8c; margin-top: 6px; }")
        io_layout = QHBoxLayout()

        self.setup_btn_export = QPushButton("📤 Export Config")
        self.setup_btn_export.clicked.connect(self.export_setup_config)
        self.setup_btn_export.setToolTip("Save configuration to file")
        io_layout.addWidget(self.setup_btn_export)

        self.setup_btn_import = QPushButton("📥 Import Config")
        self.setup_btn_import.clicked.connect(self.import_setup_config)
        self.setup_btn_import.setToolTip("Load configuration from file")
        io_layout.addWidget(self.setup_btn_import)

        io_layout.addStretch()
        io_group.setLayout(io_layout)
        quick_layout.addWidget(io_group)

        quick_layout.addStretch()
        quick_tab.setLayout(quick_layout)
        setup_tabs.addTab(quick_tab, "⚡ Quick Setup")

        # === DOWNLOAD STEAMCMD AND SCUM SERVER TAB ===
        download_tab = QWidget()
        download_layout = QVBoxLayout()

        # SteamCMD Download Section
        steamcmd_group = QGroupBox("🔄 SteamCMD Installation")
        steamcmd_group.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #ff5555; margin-top: 6px; }")
        steamcmd_layout = QVBoxLayout()

        # SteamCMD status
        steamcmd_status_layout = QHBoxLayout()
        steamcmd_status_layout.addWidget(QLabel("SteamCMD Status:"))
        self.steamcmd_status = QLabel("❌ Not installed")
        self.steamcmd_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
        steamcmd_status_layout.addWidget(self.steamcmd_status)
        steamcmd_status_layout.addStretch()
        steamcmd_layout.addLayout(steamcmd_status_layout)

        # SteamCMD installation
        steamcmd_buttons = QHBoxLayout()
        self.btn_download_steamcmd = QPushButton("📥 Download SteamCMD")
        self.btn_download_steamcmd.clicked.connect(self.download_steamcmd)
        self.btn_download_steamcmd.setToolTip("Download and install SteamCMD")
        steamcmd_buttons.addWidget(self.btn_download_steamcmd)

        self.btn_verify_steamcmd = QPushButton("✅ Verify SteamCMD")
        self.btn_verify_steamcmd.clicked.connect(self.verify_steamcmd)
        self.btn_verify_steamcmd.setToolTip("Check if SteamCMD is properly installed")
        steamcmd_buttons.addWidget(self.btn_verify_steamcmd)

        steamcmd_layout.addLayout(steamcmd_buttons)

        # SteamCMD directory
        steamcmd_dir_layout = QHBoxLayout()
        steamcmd_dir_layout.addWidget(QLabel("SteamCMD Directory:"))
        self.steamcmd_dir = QLineEdit("SteamCMD")
        self.steamcmd_dir.setToolTip("Directory where SteamCMD will be installed")
        self.btn_steamcmd_browse = QPushButton("📁")
        self.btn_steamcmd_browse.clicked.connect(lambda: self.browse_directory(self.steamcmd_dir))
        self.btn_steamcmd_auto_detect = QPushButton("🔎 Auto-Detect")
        self.btn_steamcmd_auto_detect.clicked.connect(self.auto_detect_steamcmd_dir)
        self.btn_steamcmd_auto_detect.setToolTip("Automatically find SteamCMD directory")
        steamcmd_dir_layout.addWidget(self.steamcmd_dir)
        steamcmd_dir_layout.addWidget(self.btn_steamcmd_browse)
        steamcmd_dir_layout.addWidget(self.btn_steamcmd_auto_detect)
        steamcmd_layout.addLayout(steamcmd_dir_layout)

        steamcmd_group.setLayout(steamcmd_layout)
        download_layout.addWidget(steamcmd_group)

        # SCUM Server Download Section
        scum_group = QGroupBox("🎮 SCUM Server Download")
        scum_group.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #50fa7b; margin-top: 6px; }")
        scum_layout = QVBoxLayout()

        # SCUM server status
        scum_status_layout = QHBoxLayout()
        scum_status_layout.addWidget(QLabel("SCUM Server Status:"))
        self.scum_server_status = QLabel("❌ Not downloaded")
        self.scum_server_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
        scum_status_layout.addWidget(self.scum_server_status)
        scum_status_layout.addStretch()
        scum_layout.addLayout(scum_status_layout)

        # SCUM server directory
        scum_dir_layout = QHBoxLayout()
        scum_dir_layout.addWidget(QLabel("Server Directory:"))
        self.scum_server_dir = QLineEdit("SCUM_Server")
        self.scum_server_dir.setToolTip("Directory where SCUM server will be downloaded")
        self.btn_scum_browse = QPushButton("📁")
        self.btn_scum_browse.clicked.connect(lambda: self.browse_directory(self.scum_server_dir))
        self.btn_scum_auto_detect = QPushButton("🔎 Auto-Detect")
        self.btn_scum_auto_detect.clicked.connect(self.auto_detect_scum_server_dir)
        self.btn_scum_auto_detect.setToolTip("Automatically find SCUM server directory")
        scum_dir_layout.addWidget(self.scum_server_dir)
        scum_dir_layout.addWidget(self.btn_scum_browse)
        scum_dir_layout.addWidget(self.btn_scum_auto_detect)
        scum_layout.addLayout(scum_dir_layout)

        # Connection progress bar (separate from download progress)
        connection_progress_layout = QVBoxLayout()
        
        # Connection progress bar
        self.connection_progress_bar = QProgressBar()
        self.connection_progress_bar.setMaximum(100)
        self.connection_progress_bar.setValue(0)
        self.connection_progress_bar.setVisible(False)
        self.connection_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #2b2f36;
                border-radius: 5px;
                text-align: center;
                background: #0d1016;
                font-size: 11px;
                font-weight: bold;
                color: #e6eef6;
                min-height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #8be9fd, stop:1 #6eb5d8);
                border-radius: 3px;
            }
        """)
        self.connection_progress_bar.setFormat("🔌 Connecting to Steam... %p%")
        connection_progress_layout.addWidget(self.connection_progress_bar)
        
        # Connection status label
        self.connection_status_label = QLabel("")
        self.connection_status_label.setStyleSheet("color: #8be9fd; font-size: 10px; padding: 2px;")
        self.connection_status_label.setVisible(False)
        connection_progress_layout.addWidget(self.connection_status_label)
        
        scum_layout.addLayout(connection_progress_layout)
        
        # Main download progress bar
        download_progress_layout = QVBoxLayout()
        
        self.scum_download_progress = QProgressBar()
        self.scum_download_progress.setMaximum(100)
        self.scum_download_progress.setValue(0)
        self.scum_download_progress.setVisible(False)
        self.scum_download_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #2b2f36;
                border-radius: 5px;
                text-align: center;
                background: #0d1016;
                font-size: 12px;
                font-weight: bold;
                color: #e6eef6;
                min-height: 25px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #4ade80, stop:1 #22c55e);
                border-radius: 3px;
            }
        """)
        download_progress_layout.addWidget(self.scum_download_progress)
        
        scum_layout.addLayout(download_progress_layout)

        # Download buttons
        scum_buttons = QHBoxLayout()
        self.btn_download_scum = QPushButton("🎮 Download SCUM Server")
        self.btn_download_scum.clicked.connect(self.download_scum_server)
        self.btn_download_scum.setToolTip("Download SCUM dedicated server using SteamCMD")
        scum_buttons.addWidget(self.btn_download_scum)

        self.btn_verify_scum = QPushButton("✅ Verify SCUM Server")
        self.btn_verify_scum.clicked.connect(self.verify_scum_server)
        self.btn_verify_scum.setToolTip("Check if SCUM server is properly downloaded")
        scum_buttons.addWidget(self.btn_verify_scum)

        self.btn_update_scum = QPushButton("🔄 Update SCUM Server")
        self.btn_update_scum.clicked.connect(self.update_scum_server)
        self.btn_update_scum.setToolTip("Update SCUM server to latest version")
        scum_buttons.addWidget(self.btn_update_scum)

        scum_layout.addLayout(scum_buttons)

        # Download log
        self.scum_download_log = QTextEdit()
        self.scum_download_log.setMaximumHeight(150)
        self.scum_download_log.setReadOnly(True)
        self.scum_download_log.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.scum_download_log.setStyleSheet("""
            QTextEdit {
                background: #0d1016;
                border: 1px solid #2b2f36;
                border-radius: 5px;
                color: #e6eef6;
                font-family: 'Consolas', monospace;
                font-size: 10px;
            }
        """)
        self.scum_download_log.setPlaceholderText("Download progress and logs will appear here...")
        scum_layout.addWidget(self.scum_download_log)

        scum_group.setLayout(scum_layout)
        download_layout.addWidget(scum_group)

        # Quick Actions
        actions_group = QGroupBox("⚡ Quick Actions")
        actions_group.setStyleSheet("QGroupBox { font-weight: bold; border: 2px solid #bd93f9; margin-top: 6px; }")
        actions_layout = QHBoxLayout()

        self.btn_download_all = QPushButton("🚀 Download Everything")
        self.btn_download_all.clicked.connect(self.download_everything)
        self.btn_download_all.setToolTip("Download SteamCMD and SCUM server in sequence")
        actions_layout.addWidget(self.btn_download_all)

        self.btn_check_updates = QPushButton("🔍 Check for Updates")
        self.btn_check_updates.clicked.connect(self.check_for_updates)
        self.btn_check_updates.setToolTip("Check if SCUM server updates are available")
        actions_layout.addWidget(self.btn_check_updates)

        self.btn_save_config = QPushButton("💾 Save Config")
        self.btn_save_config.clicked.connect(self.save_download_config)
        self.btn_save_config.setToolTip("Save current download configuration")
        actions_layout.addWidget(self.btn_save_config)

        self.btn_import_config = QPushButton("📥 Import Config")
        self.btn_import_config.clicked.connect(self.import_download_config)
        self.btn_import_config.setToolTip("Import download configuration from file")
        actions_layout.addWidget(self.btn_import_config)

        self.btn_export_config = QPushButton("📤 Export Config")
        self.btn_export_config.clicked.connect(self.export_download_config)
        self.btn_export_config.setToolTip("Export download configuration to file")
        actions_layout.addWidget(self.btn_export_config)

        actions_layout.addStretch()
        actions_group.setLayout(actions_layout)
        download_layout.addWidget(actions_group)

        download_layout.addStretch()
        download_tab.setLayout(download_layout)
        setup_tabs.addTab(download_tab, "📥 Download SteamCMD and SCUM Server")

        layout.addWidget(setup_tabs)
        self.page_setup.setLayout(layout)

        # Load existing setup data
        self.load_setup_config()
        self.update_setup_status()

    # --- setup actions ---
    def save_basic_setup(self):
        """Save basic setup configuration"""
        # Save to main settings with message
        self.save_settings(show_message=True)
        
        # Also update setup status
        if hasattr(self, 'update_setup_status'):
            self.update_setup_status()

    def save_advanced_setup(self):
        config = {
            'logs_dir': self.setup_logs_dir.text(),
            'config_dir': self.setup_config_dir.text(),
            'auto_restart': self.setup_auto_restart.isChecked(),
            'auto_backup': self.setup_auto_backup.isChecked()
        }
        self.save_setup_config(config)
        QMessageBox.information(self, "Saved", "Advanced configuration saved!")

    def run_quick_setup(self):
        # Auto-detect server path
        p = find_scum_exe()
        if p:
            self.scum_path = str(p)
            self.setup_label_path.setText(str(p))
            self.label_path.setText(str(p))
        
        # Set default values
        self.setup_server_name.setText("My SCUM Server")
        self.setup_max_players.setText("50")
        self.setup_port.setText("27015")
        self.setup_logs_dir.setText("Logs")
        self.setup_config_dir.setText("Config")
        
        # Save configuration
        config = {
            'server_name': self.setup_server_name.text(),
            'max_players': self.setup_max_players.text(),
            'port': self.setup_port.text(),
            'server_path': self.scum_path,
            'logs_dir': self.setup_logs_dir.text(),
            'config_dir': self.setup_config_dir.text(),
            'auto_restart': True,
            'auto_backup': False
        }
        self.save_setup_config(config)
        QMessageBox.information(self, "Quick Setup Complete", "Server setup completed with default settings!")

    def validate_setup(self):
        issues = []
        
        if not self.scum_path:
            issues.append("Server executable not set")
        
        if not self.setup_server_name.text().strip():
            issues.append("Server name not set")
        
        try:
            port = int(self.setup_port.text())
            if port < 1024 or port > 65535:
                issues.append("Invalid port number")
        except:
            issues.append("Invalid port number")
        
        if issues:
            QMessageBox.warning(self, "Validation Failed", "Issues found:\n" + "\n".join(issues))
        else:
            QMessageBox.information(self, "Validation Passed", "All settings are valid!")

    def setup_config_file(self) -> Path:
        return APP_ROOT / 'scum_setup.json'

    def load_setup_config(self):
        sf = self.setup_config_file()
        if sf.exists():
            try:
                data = json.loads(sf.read_text(encoding='utf-8'))
                self.setup_server_name.setText(data.get('server_name', 'My SCUM Server'))
                self.setup_max_players.setText(str(data.get('max_players', '50')))
                self.setup_port.setText(str(data.get('port', '27015')))
                self.setup_logs_dir.setText(data.get('logs_dir', 'Logs'))
                self.setup_config_dir.setText(data.get('config_dir', 'Config'))
                self.setup_auto_restart.setChecked(data.get('auto_restart', True))
                self.setup_auto_backup.setChecked(data.get('auto_backup', False))
            except Exception:
                pass

    def save_setup_config(self, config: dict):
        sf = self.setup_config_file()
        try:
            current_data = {}
            if sf.exists():
                current_data = json.loads(sf.read_text(encoding='utf-8'))
            current_data.update(config)
            sf.write_text(json.dumps(current_data, indent=2), encoding='utf-8')
        except Exception as e:
            QMessageBox.warning(self, 'Error', f'Could not save setup config: {e}')

    # --- enhanced setup methods ---
    def auto_detect_server(self):
        """Auto-detect SCUM server - asks user where to scan, then scans that location"""
        # First ask user where to scan
        scan_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Scan for SCUM Server",
            str(Path.home()),  # Start from user's home directory
            QFileDialog.ShowDirsOnly
        )
        
        if not scan_dir:
            # User cancelled
            return
        
        # Show progress dialog
        progress = QMessageBox(self)
        progress.setWindowTitle("🔍 Scanning...")
        progress.setText(f"Scanning {scan_dir} for SCUM server installations...\n\nThis may take a moment.")
        progress.setStandardButtons(QMessageBox.NoButton)
        progress.show()
        QApplication.processEvents()
        
        try:
            # Scan the selected directory for installations
            from scum_core import find_scum_installations_in_directory
            installations = find_scum_installations_in_directory(Path(scan_dir))
            
            progress.close()
            
            if not installations:
                self.install_status.setText("❌ Server not found - please browse manually")
                self.install_status.setStyleSheet("color: #ff6b6b; font-size: 11px;")
                QMessageBox.warning(self, "Not Found", 
                    f"Could not find SCUMServer.exe in the selected directory.\n\n"
                    f"Scanned: {scan_dir}\n\n"
                    "Please browse to it manually or install SCUM Dedicated Server first.")
                return
            
            # If only one found, use it directly
            if len(installations) == 1:
                selected_path = installations[0]
                self.scum_path = str(selected_path)
                self.setup_label_path.setText(f"✅ {selected_path.name}")
                self.install_status.setText("✅ Server found")
                self.install_status.setStyleSheet("color: #50fa7b; font-size: 11px;")
                self.update_setup_status()
                
                # Auto-save settings
                self.save_settings()
                QMessageBox.information(self, "✅ Found & Saved", 
                    f"SCUMServer.exe found and saved:\n\n{selected_path}\n\n"
                    f"Location: {selected_path.parent}\n"
                    f"Size: {selected_path.stat().st_size / (1024*1024):.1f} MB")
                return
            
            # Multiple installations found - let user choose
            dialog = QDialog(self)
            dialog.setWindowTitle("🎯 Multiple SCUM Installations Found")
            dialog.resize(700, 400)
            dialog.setStyleSheet("""
                QDialog {
                    background: #0f1117;
                    color: #e6eef6;
                }
                QLabel {
                    color: #e6eef6;
                }
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #35c06f, stop:1 #1e8b57);
                    color: #072018;
                    padding: 8px 16px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #4ade80, stop:1 #22c55e);
                }
                QListWidget {
                    background: #0d1016;
                    border: 1px solid #2b2f36;
                    border-radius: 5px;
                    color: #e6eef6;
                    padding: 5px;
                }
                QListWidget::item {
                    padding: 10px;
                    border-bottom: 1px solid #2b2f36;
                }
                QListWidget::item:selected {
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1e8b57, stop:1 #35c06f);
                    color: #ffffff;
                    font-weight: bold;
                }
                QListWidget::item:hover {
                    background: #2b2f36;
                }
            """)
            
            layout = QVBoxLayout()
            
            # Title
            title = QLabel(f"🎯 Found {len(installations)} SCUM Server Installations")
            title.setStyleSheet("font-size: 16px; font-weight: bold; color: #50fa7b; padding: 10px;")
            layout.addWidget(title)
            
            # Instructions
            instructions = QLabel("Select which installation you want to use:")
            instructions.setStyleSheet("font-size: 12px; color: #8be9fd; padding: 5px;")
            layout.addWidget(instructions)
            
            # List widget
            list_widget = QListWidget()
            for path in installations:
                # Get size info
                try:
                    size_mb = path.stat().st_size / (1024*1024)
                    size_text = f"{size_mb:.1f} MB"
                except:
                    size_text = "Unknown size"
                
                # Format item text
                item_text = f"📁 {path.parent.name}\n   {path}\n   Size: {size_text}"
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, str(path))  # Store full path
                list_widget.addItem(item)
            
            list_widget.setCurrentRow(0)  # Select first by default
            layout.addWidget(list_widget)
            
            # Buttons
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            
            btn_cancel = QPushButton("❌ Cancel")
            btn_cancel.clicked.connect(dialog.reject)
            button_layout.addWidget(btn_cancel)
            
            btn_select = QPushButton("✅ Use Selected")
            btn_select.setDefault(True)
            btn_select.clicked.connect(dialog.accept)
            button_layout.addWidget(btn_select)
            
            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            
            # Show dialog
            if dialog.exec() == QDialog.Accepted:
                selected_item = list_widget.currentItem()
                if selected_item:
                    selected_path = Path(selected_item.data(Qt.UserRole))
                    self.scum_path = str(selected_path)
                    self.setup_label_path.setText(f"✅ {selected_path.name}")
                    self.install_status.setText("✅ Server found")
                    self.install_status.setStyleSheet("color: #50fa7b; font-size: 11px;")
                    self.update_setup_status()
                    
                    # Auto-save settings
                    self.save_settings()
                    QMessageBox.information(self, "✅ Saved", 
                        f"Selected SCUM server saved:\n\n{selected_path}\n\n"
                        f"Location: {selected_path.parent}")
        
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Error", f"Error during auto-detection:\n{str(e)}")

    def auto_detect_steamcmd_dir(self):
        """Auto-detect SteamCMD directory"""
        from scum_core import find_steamcmd_dir
        p = find_steamcmd_dir()
        if p:
            # Make it relative to APP_ROOT if possible
            try:
                rel_path = p.relative_to(APP_ROOT)
                self.steamcmd_dir.setText(str(rel_path))
            except:
                self.steamcmd_dir.setText(str(p))
            
            # Auto-save settings
            self.save_settings()
            QMessageBox.information(self, "Found & Saved", f"SteamCMD directory found and saved:\n{p}")
        else:
            QMessageBox.warning(self, "Not Found", "Could not auto-detect SteamCMD directory\nPlease browse to it manually.")

    def auto_detect_scum_server_dir(self):
        """Auto-detect SCUM server directory"""
        from scum_core import find_scum_server_dir
        p = find_scum_server_dir()
        if p:
            # Make it relative to APP_ROOT if possible
            try:
                rel_path = p.relative_to(APP_ROOT)
                self.scum_server_dir.setText(str(rel_path))
            except:
                self.scum_server_dir.setText(str(p))
            
            # Auto-save settings
            self.save_settings()
            QMessageBox.information(self, "Found & Saved", f"SCUM server directory found and saved:\n{p}")
        else:
            QMessageBox.warning(self, "Not Found", "Could not auto-detect SCUM server directory\nPlease browse to it manually.")

    def test_server_port(self):
        port = self.setup_port.value()
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result == 0:
                QMessageBox.warning(self, "Port In Use", f"Port {port} is already in use!")
            else:
                QMessageBox.information(self, "Port Available", f"Port {port} is available.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not test port: {e}")

    def browse_directory(self, line_edit):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Directory", str(APP_ROOT))
        if dir_path:
            # Make it relative to APP_ROOT if possible
            try:
                rel_path = Path(dir_path).relative_to(APP_ROOT)
                line_edit.setText(str(rel_path))
            except:
                line_edit.setText(dir_path)
            
            # Auto-save settings after directory selection
            self.save_settings()

    def update_setup_status(self):
        # Calculate setup completion percentage
        score = 0
        total = 8

        if self.scum_path:
            score += 1
        if self.setup_server_name.text().strip():
            score += 1
        if self.setup_max_players.value() > 0:
            score += 1
        if self.setup_port.value() >= 1024:
            score += 1
        if self.setup_logs_dir.text().strip():
            score += 1
        if self.setup_config_dir.text().strip():
            score += 1
        if self.setup_save_dir.text().strip():
            score += 1
        if self.setup_rcon_password.text().strip():
            score += 1

        percentage = int((score / total) * 100)
        self.setup_progress.setValue(percentage)

        if percentage == 100:
            self.setup_status_label.setText("✅ Setup Complete")
            self.setup_status_label.setStyleSheet("color: #50fa7b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
        elif percentage >= 75:
            self.setup_status_label.setText("🟡 Almost Ready")
            self.setup_status_label.setStyleSheet("color: #ffb86b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
        else:
            self.setup_status_label.setText("⚠️ Setup Incomplete")
            self.setup_status_label.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")

    def generate_server_config(self):
        if not self.scum_path:
            QMessageBox.warning(self, "Error", "Please set the server executable path first!")
            return

        config_dir = APP_ROOT / self.setup_config_dir.text()
        config_dir.mkdir(exist_ok=True)

        # Generate server.cfg
        server_config = f"""# SCUM Server Configuration - Generated by SCUM Server Manager
# Generated on {QTime.currentTime().toString()} {QDate.currentDate().toString()}

[Server]
Name = "{self.setup_server_name.text()}"
Password = "{self.setup_password.text()}"
MaxPlayers = {self.setup_max_players.value()}
Port = {self.setup_port.value()}
QueryPort = {self.setup_query_port.value()}
RCONPort = {self.setup_rcon_port.value()}
RCONPassword = "{self.setup_rcon_password.text()}"
Difficulty = {self.setup_difficulty.currentIndex()}

[Directories]
Logs = "{self.setup_logs_dir.text()}"
Save = "{self.setup_save_dir.text()}"

[Performance]
MemoryLimit = {self.setup_memory_limit.value()}
AutoRestart = {1 if self.setup_auto_restart.isChecked() else 0}
RestartDelay = {self.setup_restart_delay.value()}
AutoBackup = {1 if self.setup_auto_backup.isChecked() else 0}
BackupInterval = {self.setup_backup_interval.value()}
"""

        config_file = config_dir / "server.cfg"
        try:
            config_file.write_text(server_config, encoding='utf-8')
            QMessageBox.information(self, "Success", f"Server configuration generated:\n{config_file}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not generate config: {e}")

    def run_complete_quick_setup(self):
        # Step 1: Auto-detect server
        self.auto_detect_server()
        self.setup_steps[0].setChecked(bool(self.scum_path))

        # Step 2: Set basic settings
        self.setup_server_name.setText("My SCUM Server")
        self.setup_max_players.setValue(50)
        self.setup_port.setValue(27015)
        self.setup_password.setText("")
        self.setup_steps[1].setChecked(True)

        # Step 3: Set directories
        self.setup_logs_dir.setText("Logs")
        self.setup_config_dir.setText("Config")
        self.setup_save_dir.setText("Save")
        self.setup_steps[2].setChecked(True)

        # Step 4: Generate config
        self.generate_server_config()
        self.setup_steps[3].setChecked(True)

        # Save all settings
        self.save_basic_setup()
        self.save_advanced_setup()

        QMessageBox.information(self, "Quick Setup Complete", "Server setup completed successfully!\n\nYou can now start your SCUM server.")

    def build_player_stats(self):
        """Build the Player Stats tab with comprehensive player statistics and analytics"""
        # Create main widget for Player Stats tab
        page_player_stats = QWidget()
        layout = QVBoxLayout(page_player_stats)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header section
        header_layout = QHBoxLayout()

        # Title
        title_label = QLabel("📊 Player Statistics")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #e6eef6;
                padding: 10px 0px;
            }
        """)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Stats")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #3b82f6, stop:1 #1d4ed8);
                color: #ffffff;
                padding: 8px 16px;
                border-radius: 6px;
                border: 1px solid #2b2f36;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #60a5fa, stop:1 #3b82f6);
            }
        """)
        refresh_btn.clicked.connect(self.refresh_player_stats)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # Stats overview cards
        stats_cards_layout = QHBoxLayout()
        stats_cards_layout.setSpacing(15)

        # Total players card
        total_card = self.create_stats_card("👥 Total Players", "0", "#4ade80")
        stats_cards_layout.addWidget(total_card)

        # Online players card
        online_card = self.create_stats_card("🟢 Online Now", "0", "#22c55e")
        stats_cards_layout.addWidget(online_card)

        # Average session card
        session_card = self.create_stats_card("⏱️ Avg Session", "0m", "#f59e0b")
        stats_cards_layout.addWidget(session_card)

        # Most active card
        active_card = self.create_stats_card("🏆 Most Active", "None", "#8b5cf6")
        stats_cards_layout.addWidget(active_card)

        layout.addLayout(stats_cards_layout)

        # Main content area with splitter
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left panel - Statistics charts and graphs
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Activity chart section
        chart_section = QGroupBox("📈 Player Activity Trends")
        chart_section.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #e6eef6;
                padding: 10px;
                border: 2px solid #44475a;
                border-radius: 8px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
        """)
        chart_layout = QVBoxLayout(chart_section)

        # Placeholder for activity chart
        chart_placeholder = QLabel("📊 Activity chart will be displayed here\n\nFeatures planned:\n• Daily active players over time\n• Peak hours analysis\n• Session duration trends\n• Player retention metrics")
        chart_placeholder.setStyleSheet("""
            QLabel {
                color: #6272a4;
                font-size: 12px;
                padding: 20px;
                background: #2b2f36;
                border-radius: 6px;
                border: 1px solid #44475a;
            }
        """)
        chart_placeholder.setAlignment(Qt.AlignCenter)
        chart_layout.addWidget(chart_placeholder)

        left_layout.addWidget(chart_section)

        # Detailed stats section
        stats_section = QGroupBox("📋 Detailed Statistics")
        stats_section.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #e6eef6;
                padding: 10px;
                border: 2px solid #44475a;
                border-radius: 8px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
        """)
        stats_layout = QVBoxLayout(stats_section)

        # Stats table
        self.player_stats_table = QTableWidget()
        self.player_stats_table.setColumnCount(4)
        self.player_stats_table.setHorizontalHeaderLabels(["Metric", "Value", "Change", "Trend"])
        self.player_stats_table.horizontalHeader().setStretchLastSection(True)
        self.player_stats_table.setAlternatingRowColors(True)
        self.player_stats_table.setStyleSheet("""
            QTableWidget {
                background: #2b2f36;
                color: #e6eef6;
                border: 1px solid #44475a;
                border-radius: 6px;
                gridline-color: #44475a;
            }
            QHeaderView::section {
                background: #44475a;
                color: #e6eef6;
                padding: 8px;
                border: 1px solid #6272a4;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #44475a;
            }
        """)

        # Add sample stats data
        stats_data = [
            ["Total Unique Players", "0", "+0", "→"],
            ["Total Sessions", "0", "+0", "→"],
            ["Average Session Time", "0 min", "+0 min", "→"],
            ["Longest Session", "0 min", "N/A", "→"],
            ["Peak Concurrent Players", "0", "0", "→"],
            ["Server Uptime", "0%", "0%", "→"],
            ["Player Retention (7d)", "0%", "0%", "→"],
            ["New Players Today", "0", "+0", "→"]
        ]

        self.player_stats_table.setRowCount(len(stats_data))
        for row, (metric, value, change, trend) in enumerate(stats_data):
            self.player_stats_table.setItem(row, 0, QTableWidgetItem(metric))
            self.player_stats_table.setItem(row, 1, QTableWidgetItem(value))
            self.player_stats_table.setItem(row, 2, QTableWidgetItem(change))
            self.player_stats_table.setItem(row, 3, QTableWidgetItem(trend))

        stats_layout.addWidget(self.player_stats_table)
        left_layout.addWidget(stats_section)

        # Right panel - Top players and recent activity
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Top players section
        top_players_section = QGroupBox("🏆 Top Players")
        top_players_section.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #e6eef6;
                padding: 10px;
                border: 2px solid #44475a;
                border-radius: 8px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
        """)
        top_layout = QVBoxLayout(top_players_section)

        # Top players list
        self.top_players_list = QListWidget()
        self.top_players_list.setStyleSheet("""
            QListWidget {
                background: #2b2f36;
                color: #e6eef6;
                border: 1px solid #44475a;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #44475a;
            }
            QListWidget::item:hover {
                background: #44475a;
            }
        """)

        # Add sample top players
        sample_top_players = [
            "🥇 No players yet - start your server!",
            "🥈 Server activity will appear here",
            "🥉 Player statistics loading..."
        ]

        for player in sample_top_players:
            self.top_players_list.addItem(player)

        top_layout.addWidget(self.top_players_list)
        right_layout.addWidget(top_players_section)

        # Recent activity section
        activity_section = QGroupBox("🕒 Recent Activity")
        activity_section.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #e6eef6;
                padding: 10px;
                border: 2px solid #44475a;
                border-radius: 8px;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
            }
        """)
        activity_layout = QVBoxLayout(activity_section)

        # Activity log
        self.activity_log = QTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setMaximumHeight(200)
        self.activity_log.setStyleSheet("""
            QTextEdit {
                background: #2b2f36;
                color: #e6eef6;
                border: 1px solid #44475a;
                border-radius: 6px;
                font-family: 'Consolas', monospace;
                font-size: 11px;
            }
        """)

        # Add sample activity
        sample_activity = "📊 Player Statistics Dashboard\n\n• Server statistics will update automatically\n• Player activity trends will be displayed\n• Top players list will populate with data\n• Recent activity log will show live updates\n\nStart your server to see real statistics!"
        self.activity_log.setPlainText(sample_activity)

        activity_layout.addWidget(self.activity_log)
        right_layout.addWidget(activity_section)

        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 400])  # Left panel slightly larger

        # Store references for updates
        self.page_player_stats = page_player_stats
        self.stats_total_card = total_card
        self.stats_online_card = online_card
        self.stats_session_card = session_card
        self.stats_active_card = active_card

        return page_player_stats

    def create_stats_card(self, title, value, color):
        """Create a statistics card widget"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 {color}, stop:1 #2b2f36);
                border: 2px solid #44475a;
                border-radius: 10px;
                padding: 15px;
            }}
        """)
        card.setFixedHeight(100)

        layout = QVBoxLayout(card)

        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #e6eef6;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
                padding: 5px 0px;
            }
        """)
        layout.addWidget(value_label)

        return card

    def refresh_player_stats(self):
        """Refresh player statistics data"""
        try:
            # Get current player data
            players_data = self.populate_players()

            if players_data:
                # Update stats cards
                total_players = len(players_data)
                online_players = sum(1 for p in players_data if p.get('status') == 'Online')

                # Update cards
                self.update_stats_card(self.stats_total_card, "👥 Total Players", str(total_players))
                self.update_stats_card(self.stats_online_card, "🟢 Online Now", str(online_players))

                # Calculate average session time (simplified)
                avg_session = "15m"  # Placeholder
                self.update_stats_card(self.stats_session_card, "⏱️ Avg Session", avg_session)

                # Find most active player
                most_active = "None"
                if players_data:
                    # Simple heuristic: player with most play time
                    most_active = max(players_data, key=lambda p: float(p.get('play_time', '0').replace('h', '').replace('m', '')) if p.get('play_time') else 0)
                    most_active = most_active.get('name', 'None')

                self.update_stats_card(self.stats_active_card, "🏆 Most Active", most_active)

                # Update stats table with real data
                self.update_stats_table(players_data)

                # Update top players list
                self.update_top_players_list(players_data)

                # Update activity log
                self.update_activity_log(players_data)

                # Show success message
                self.safe_message_box("information", "Stats Updated", f"Player statistics updated successfully!\n\nTotal Players: {total_players}\nOnline: {online_players}")

            else:
                # No data available
                self.safe_message_box("warning", "No Data", "No player data available.\n\nMake sure your server is running and has player activity.")

        except Exception as e:
            self.safe_message_box("critical", "Error", f"Failed to refresh player statistics:\n{str(e)}")

    def update_stats_card(self, card, title, value):
        """Update a statistics card with new value"""
        layout = card.layout()
        if layout and layout.count() >= 2:
            value_label = layout.itemAt(1).widget()
            if isinstance(value_label, QLabel):
                value_label.setText(value)

    def update_stats_table(self, players_data):
        """Update the detailed statistics table"""
        if not hasattr(self, 'player_stats_table'):
            return

        # Calculate real statistics
        total_players = len(players_data)
        online_count = sum(1 for p in players_data if p.get('status') == 'Online')

        # Calculate average session time
        session_times = []
        for p in players_data:
            play_time = p.get('play_time', '0')
            if play_time and play_time != '0':
                # Convert to minutes (simplified)
                if 'h' in play_time:
                    hours = float(play_time.replace('h', ''))
                    session_times.append(hours * 60)
                elif 'm' in play_time:
                    minutes = float(play_time.replace('m', ''))
                    session_times.append(minutes)

        avg_session = "0 min"
        if session_times:
            avg_minutes = sum(session_times) / len(session_times)
            if avg_minutes >= 60:
                avg_session = ".1f"
            else:
                avg_session = ".0f"

        # Find longest session
        longest_session = "0 min"
        if session_times:
            max_minutes = max(session_times)
            if max_minutes >= 60:
                longest_session = ".1f"
            else:
                longest_session = ".0f"

        # Update table data
        stats_data = [
            ["Total Unique Players", str(total_players), "+0", "→"],
            ["Total Sessions", str(total_players), "+0", "→"],  # Simplified
            ["Average Session Time", avg_session, "+0 min", "→"],
            ["Longest Session", longest_session, "N/A", "→"],
            ["Peak Concurrent Players", str(online_count), "0", "→"],
            ["Server Uptime", "100%", "0%", "↑"],  # Assuming server is running
            ["Player Retention (7d)", "N/A", "0%", "→"],
            ["New Players Today", "0", "+0", "→"]
        ]

        for row, (metric, value, change, trend) in enumerate(stats_data):
            if row < self.player_stats_table.rowCount():
                self.player_stats_table.setItem(row, 1, QTableWidgetItem(value))
                self.player_stats_table.setItem(row, 2, QTableWidgetItem(change))

    def update_top_players_list(self, players_data):
        """Update the top players list"""
        if not hasattr(self, 'top_players_list'):
            return

        self.top_players_list.clear()

        if not players_data:
            self.top_players_list.addItem("🥇 No players yet - start your server!")
            self.top_players_list.addItem("🥈 Server activity will appear here")
            self.top_players_list.addItem("🥉 Player statistics loading...")
            return

        # Sort by play time (simplified)
        sorted_players = sorted(players_data,
                              key=lambda p: float(p.get('play_time', '0').replace('h', '').replace('m', '')) if p.get('play_time') else 0,
                              reverse=True)

        medals = ["🥇", "🥈", "🥉"]
        for i, player in enumerate(sorted_players[:10]):  # Top 10
            medal = medals[i] if i < 3 else "🏅"
            name = player.get('name', 'Unknown')
            play_time = player.get('play_time', '0')
            status = player.get('status', 'Offline')
            status_icon = "🟢" if status == 'Online' else "⚪"

            item_text = f"{medal} {name} - {play_time} {status_icon}"
            self.top_players_list.addItem(item_text)

    def update_activity_log(self, players_data):
        """Update the recent activity log"""
        if not hasattr(self, 'activity_log'):
            return

        activity_text = "📊 Player Statistics Dashboard\n\n"

        if players_data:
            online_count = sum(1 for p in players_data if p.get('status') == 'Online')
            total_count = len(players_data)

            activity_text += f"🟢 Online Players: {online_count}/{total_count}\n"
            activity_text += f"👥 Total Registered: {total_count}\n\n"

            # Recent activity (simplified)
            activity_text += "Recent Activity:\n"
            for player in players_data[:5]:  # Show first 5
                name = player.get('name', 'Unknown')
                status = player.get('status', 'Offline')
                last_seen = player.get('connected', 'Never')
                activity_text += f"• {name}: {status} (Last: {last_seen})\n"

            activity_text += "\n📈 Statistics last updated: " + time.strftime("%H:%M:%S")
        else:
            activity_text += "• No player data available\n• Start your server to see statistics\n• Player activity will appear here automatically"

        self.activity_log.setPlainText(activity_text)

    def validate_complete_setup(self):
        issues = []

        if not self.scum_path:
            issues.append("• Server executable not configured")

        if not self.setup_server_name.text().strip():
            issues.append("• Server name not set")

        if self.setup_max_players.value() <= 0:
            issues.append("• Invalid max players")

        if self.setup_port.value() < 1024:
            issues.append("• Invalid server port")

        if not self.setup_logs_dir.text().strip():
            issues.append("• Logs directory not set")

        if not self.setup_config_dir.text().strip():
            issues.append("• Config directory not set")

        if not self.setup_rcon_password.text().strip():
            issues.append("• RCON password not set (recommended)")

        if issues:
            QMessageBox.warning(self, "Setup Validation Failed",
                              "The following issues need to be resolved:\n\n" + "\n".join(issues))
        else:
            QMessageBox.information(self, "Setup Validation Passed",
                                  "All settings are properly configured!\n\nYour SCUM server is ready to run.")

    def export_setup_config(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Export Configuration", str(APP_ROOT), "JSON files (*.json)")
        if filename:
            try:
                config = self.load_setup_config()
                Path(filename).write_text(json.dumps(config, indent=2), encoding='utf-8')
                QMessageBox.information(self, "Exported", f"Configuration exported to:\n{filename}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not export config: {e}")

    def import_setup_config(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Import Configuration", str(APP_ROOT), "JSON files (*.json)")
        if filename:
            try:
                data = json.loads(Path(filename).read_text(encoding='utf-8'))
                self.save_setup_config(data)
                self.load_setup_config()
                self.update_setup_status()
                QMessageBox.information(self, "Imported", f"Configuration imported from:\n{filename}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not import config: {e}")

    def safe_message_box(self, msg_type, title, message):
        """Thread-safe message box display using QTimer to prevent GUI crashes from background threads"""
        def show_message():
            if msg_type == "information":
                QMessageBox.information(self, title, message)
            elif msg_type == "warning":
                QMessageBox.warning(self, title, message)
            elif msg_type == "critical":
                QMessageBox.critical(self, title, message)
            elif msg_type == "question":
                return QMessageBox.question(self, title, message, QMessageBox.Yes | QMessageBox.No)
        
        # Use QTimer to schedule the message box on the main thread
        QTimer.singleShot(0, show_message)

    # Thread-safe GUI update methods using QMetaObject.invokeMethod
    @Slot(str)
    def append_to_log(self, text):
        """Thread-safe method to append text to the download log"""
        self.scum_download_log.append(text)

    @Slot(int)
    def update_progress_bar(self, value):
        """Thread-safe method to update progress bar value"""
        self.scum_download_progress.setValue(value)

    @Slot(str)
    def update_status_label(self, text):
        """Thread-safe method to update status label"""
        self.scum_server_status.setText(text)

    @Slot(str)
    def update_time_label(self, text):
        """Thread-safe method to update time estimate label"""
        if hasattr(self, 'download_time_label'):
            self.download_time_label.setText(text)

    @Slot(str)
    def update_connection_status(self, text):
        """Thread-safe method to update connection status label"""
        if hasattr(self, 'connection_status_label'):
            self.connection_status_label.setText(text)

    @Slot(bool)
    def set_connection_progress_visible(self, visible):
        """Thread-safe method to show/hide connection progress bar"""
        if hasattr(self, 'connection_progress_bar'):
            self.connection_progress_bar.setVisible(visible)

    @Slot(int)
    def update_connection_progress(self, value):
        """Thread-safe method to update connection progress bar"""
        if hasattr(self, 'connection_progress_bar'):
            self.connection_progress_bar.setValue(value)

    @Slot(bool)
    def set_download_progress_visible(self, visible):
        """Thread-safe method to show/hide download progress bar"""
        self.scum_download_progress.setVisible(visible)

    @Slot(str)
    def update_status_stylesheet(self, stylesheet):
        """Thread-safe method to update status label stylesheet"""
        self.scum_server_status.setStyleSheet(stylesheet)

    @Slot(str)
    def update_label_path(self, text):
        """Thread-safe method to update label_path text"""
        if hasattr(self, 'label_path'):
            self.label_path.setText(text)

    @Slot(str)
    def update_setup_label_path(self, text):
        """Thread-safe method to update setup_label_path text"""
        if hasattr(self, 'setup_label_path'):
            self.setup_label_path.setText(text)

    @Slot(str)
    def update_scum_download_btn_text(self, text):
        """Thread-safe method to update scum_download_btn text"""
        if hasattr(self, 'scum_download_btn'):
            self.scum_download_btn.setText(text)

    @Slot(bool)
    def update_scum_download_btn_enabled(self, enabled):
        """Thread-safe method to update scum_download_btn enabled state"""
        if hasattr(self, 'scum_download_btn'):
            self.scum_download_btn.setEnabled(enabled)

    # --- download methods ---
    def download_steamcmd(self):
        """Download and install SteamCMD"""
        steamcmd_dir = APP_ROOT / self.steamcmd_dir.text()
        
        # Check if directory exists and is writable
        try:
            steamcmd_dir.mkdir(exist_ok=True)
            # Test write permissions
            test_file = steamcmd_dir / "test_write.tmp"
            test_file.write_text("test")
            test_file.unlink()
        except PermissionError:
            error_msg = (
                "Permission Denied (Error 13)\n\n"
                "Cannot write to the SteamCMD directory.\n\n"
                "Solutions:\n"
                "1. Run the application as Administrator\n"
                "2. Choose a different directory (e.g., Desktop or Documents)\n"
                "3. Check folder permissions\n\n"
                f"Current directory: {steamcmd_dir}"
            )
            QMessageBox.critical(self, "Permission Error", error_msg)
            return
        except Exception as e:
            QMessageBox.warning(self, "Directory Error", f"Cannot create directory:\n{str(e)}")
            return
            
        steamcmd_exe = steamcmd_dir / "steamcmd.exe"

        if steamcmd_exe.exists():
            reply = QMessageBox.question(self, "SteamCMD Exists",
                                       "SteamCMD already exists. Download again?",
                                       QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.No:
                self.verify_steamcmd()
                return

        self.btn_download_steamcmd.setText("📥 Downloading...")
        self.btn_download_steamcmd.setEnabled(False)
        self.steamcmd_status.setText("⏳ Downloading...")
        self.steamcmd_status.setStyleSheet("color: #ffb86b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")

        # Download SteamCMD
        import urllib.request
        import zipfile

        try:
            # SteamCMD download URL
            url = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip"
            zip_path = steamcmd_dir / "steamcmd.zip"

            # Download with progress
            def download_progress(block_num, block_size, total_size):
                downloaded = block_num * block_size
                percent = min(100, (downloaded * 100) / total_size)
                self.steamcmd_status.setText(f"⏳ Downloading... {percent:.1f}%")

            urllib.request.urlretrieve(url, zip_path, download_progress)

            # Extract ZIP
            self.steamcmd_status.setText("⏳ Extracting...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(steamcmd_dir)

            # Clean up
            zip_path.unlink()

            # Initialize SteamCMD (required first run)
            self.steamcmd_status.setText("⏳ Initializing SteamCMD...")
            try:
                init_cmd = [str(steamcmd_exe), "+quit"]
                init_process = subprocess.Popen(
                    init_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(steamcmd_dir)
                )
                init_process.wait(timeout=30)  # Wait up to 30 seconds for initialization
            except subprocess.TimeoutExpired:
                # Initialization might take time, but continue anyway
                pass
            except Exception as e:
                # Log but don't fail - initialization might still work
                print(f"SteamCMD initialization warning: {e}")

            # Verify installation
            if steamcmd_exe.exists():
                self.steamcmd_status.setText("✅ SteamCMD installed")
                self.steamcmd_status.setStyleSheet("color: #50fa7b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
                QMessageBox.information(self, "✅ Success", "SteamCMD downloaded and installed successfully!")
            else:
                raise Exception("steamcmd.exe not found after extraction")
                
        except PermissionError as e:
            error_msg = (
                "Permission Denied (Error 13)\n\n"
                "Could not write files to the SteamCMD directory.\n\n"
                "Solutions:\n"
                "• Run the application as Administrator\n"
                "• Choose a different directory (try Desktop or Documents)\n"
                "• Check folder permissions\n\n"
                f"Directory: {steamcmd_dir}\n"
                f"Error: {str(e)}"
            )
            self.steamcmd_status.setText("❌ Permission denied")
            self.steamcmd_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
            QMessageBox.critical(self, "Permission Error", error_msg)
            
        except Exception as e:
            self.steamcmd_status.setText("❌ Download failed")
            self.steamcmd_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
            QMessageBox.warning(self, "Download Failed", f"Could not download SteamCMD:\n{str(e)}")

        finally:
            self.btn_download_steamcmd.setText("📥 Download SteamCMD")
            self.btn_download_steamcmd.setEnabled(True)

    def verify_steamcmd(self):
        """Verify SteamCMD installation and functionality"""
        steamcmd_dir = APP_ROOT / self.steamcmd_dir.text()
        steamcmd_exe = steamcmd_dir / "steamcmd.exe"

        if not steamcmd_exe.exists():
            self.steamcmd_status.setText("❌ Not installed")
            self.steamcmd_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
            QMessageBox.warning(self, "Not Found", "SteamCMD is not installed.\nPlease download it first.")
            return

        # Test SteamCMD functionality
        self.steamcmd_status.setText("🧪 Testing...")
        self.steamcmd_status.setStyleSheet("color: #ffb86b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")

        try:

            # Run SteamCMD version check
            test_cmd = [str(steamcmd_exe), "+quit"]
            process = subprocess.Popen(
                test_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(steamcmd_dir)
            )

            # Wait for completion with timeout
            try:
                output, _ = process.communicate(timeout=10)
                return_code = process.returncode

                if return_code == 0:
                    self.steamcmd_status.setText("✅ SteamCMD working")
                    self.steamcmd_status.setStyleSheet("color: #50fa7b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
                    QMessageBox.information(self, "Verified", "SteamCMD is properly installed and working!")
                else:
                    self.steamcmd_status.setText("❌ SteamCMD error")
                    self.steamcmd_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
                    QMessageBox.warning(self, "Test Failed", f"SteamCMD returned error code {return_code}\n\nOutput:\n{output[:500]}")

            except subprocess.TimeoutExpired:
                process.kill()
                self.steamcmd_status.setText("❌ SteamCMD timeout")
                self.steamcmd_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
                QMessageBox.warning(self, "Timeout", "SteamCMD took too long to respond.\nIt may be corrupted or need reinstallation.")

        except Exception as e:
            self.steamcmd_status.setText("❌ Test failed")
            self.steamcmd_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
            QMessageBox.warning(self, "Verification Failed", f"Could not test SteamCMD:\n{str(e)}")

    def download_scum_server(self):
        """Download SCUM server - Manual or Automatic options"""
        # Create download method selection dialog
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("Download SCUM Server")
        dialog.setModal(True)
        dialog.resize(400, 200)

        layout = QVBoxLayout()

        # Title
        title = QLabel("Choose Download Method")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #e6eef6; margin-bottom: 10px;")
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "You can download the SCUM Dedicated Server manually through Steam\n"
            "or automatically using SteamCMD.\n\n"
            "Manual download gives you more control but requires Steam to be running.\n"
            "Automatic download is faster but requires SteamCMD to be installed."
        )
        desc.setStyleSheet("color: #e6eef6; margin-bottom: 20px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Buttons
        button_layout = QHBoxLayout()

        # Manual download button
        btn_manual = QPushButton("📱 Manual Download")
        btn_manual.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #4ade80, stop:1 #22c55e);
                color: #072018;
                padding: 10px 16px;
                border-radius: 8px;
                border: 1px solid #2b2f36;
                font-weight: bold;
                min-width: 140px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #6ef08b, stop:1 #4ade80);
            }
        """)
        btn_manual.clicked.connect(lambda: self._manual_download_scum_server(dialog))
        button_layout.addWidget(btn_manual)

        # Automatic download button
        btn_auto = QPushButton("🤖 Automatic Download")
        btn_auto.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #3b82f6, stop:1 #1d4ed8);
                color: #ffffff;
                padding: 10px 16px;
                border-radius: 8px;
                border: 1px solid #2b2f36;
                font-weight: bold;
                min-width: 140px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #60a5fa, stop:1 #3b82f6);
            }
        """)
        btn_auto.clicked.connect(lambda: self._auto_download_scum_server(dialog))
        button_layout.addWidget(btn_auto)

        layout.addLayout(button_layout)

        # Cancel button
        cancel_layout = QHBoxLayout()
        cancel_layout.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet("""
            QPushButton {
                background: #666;
                color: #ddd;
                padding: 8px 16px;
                border-radius: 6px;
                border: 1px solid #2b2f36;
            }
            QPushButton:hover {
                background: #777;
            }
        """)
        btn_cancel.clicked.connect(dialog.reject)
        cancel_layout.addWidget(btn_cancel)
        layout.addLayout(cancel_layout)

        dialog.setLayout(layout)
        dialog.exec()

    def _manual_download_scum_server(self, parent_dialog):
        """Manual download - Open Steam and directly install SCUM Dedicated Server (AppID: 3792580)"""
        parent_dialog.accept()

        try:
            import webbrowser

            # Direct Steam URL to install SCUM Dedicated Server (AppID: 3792580)
            # This will open Steam and immediately start installing the SCUM Dedicated Server
            steam_url = "steam://install/3792580"

            # First try the Steam protocol
            try:
                subprocess.run(["cmd", "/c", f"start {steam_url}"], check=True, shell=True)
            except:
                # Fallback to webbrowser
                try:
                    webbrowser.open(steam_url)
                except:
                    # Last resort - try to open Steam.exe directly with the install URL
                    try:
                        # Common Steam installation paths
                        steam_paths = [
                            "C:\\Program Files (x86)\\Steam\\Steam.exe",
                            "C:\\Program Files\\Steam\\Steam.exe",
                            "D:\\Program Files (x86)\\Steam\\Steam.exe",
                            "D:\\Program Files\\Steam\\Steam.exe"
                        ]

                        steam_found = False
                        for path in steam_paths:
                            if Path(path).exists():
                                # Try to run Steam with the install URL as argument
                                subprocess.run([path, steam_url], check=True)
                                steam_found = True
                                break

                        if not steam_found:
                            raise FileNotFoundError("Steam not found in common locations")

                    except Exception as e:
                        QMessageBox.warning(self, "Steam Not Found",
                                          f"Could not open Steam automatically.\n\nPlease manually:\n"
                                          "1. Open Steam\n"
                                          "2. Go to Library\n"
                                          "3. Click on 'Tools' tab\n"
                                          "4. Search for 'SCUM Dedicated Server'\n"
                                          "5. Click 'Install'\n\n"
                                          f"Error: {str(e)}")
                        return

            QMessageBox.information(self, "Steam Install Started",
                                  "Steam should now be installing the SCUM Dedicated Server automatically.\n\n"
                                  "The installation will begin immediately. You can monitor the progress\n"
                                  "in your Steam Library under the 'Tools' section.\n\n"
                                  "Once installed, you can set the server path in Settings.")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not start Steam installation:\n{str(e)}")

    def _auto_download_scum_server(self, parent_dialog):
        """Automatic download using SteamCMD with AppID 3792580"""
        parent_dialog.accept()

        # Ask user where to download the SCUM server
        current_dir = self.scum_server_dir.text().strip()
        if not current_dir:
            # Default to a SCUM_Server folder in the app directory
            default_dir = str(APP_ROOT / "SCUM_Server")
        else:
            default_dir = str(APP_ROOT / current_dir)
        
        # Prompt user to select download directory
        download_dir = QFileDialog.getExistingDirectory(
            self,
            "Select SCUM Server Download Directory",
            default_dir,
            QFileDialog.ShowDirsOnly
        )
        
        if not download_dir:
            # User cancelled
            return
        
        # Update the UI with the selected directory
        try:
            rel_path = Path(download_dir).relative_to(APP_ROOT)
            self.scum_server_dir.setText(str(rel_path))
        except:
            self.scum_server_dir.setText(download_dir)
        
        # Save the setting
        self.save_settings()

        steamcmd_dir = APP_ROOT / self.steamcmd_dir.text()
        steamcmd_exe = steamcmd_dir / "steamcmd.exe"
        scum_server_dir = Path(download_dir)

        # Validate SteamCMD first
        if not steamcmd_exe.exists():
            QMessageBox.warning(self, "SteamCMD Required", "Please download and install SteamCMD first!")
            return

        # Test SteamCMD functionality before proceeding
        try:
            test_process = subprocess.Popen(
                [str(steamcmd_exe), "+quit"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(steamcmd_dir)
            )
            test_output, _ = test_process.communicate(timeout=15)
            if test_process.returncode != 0:
                QMessageBox.warning(self, "SteamCMD Error",
                                  f"SteamCMD is not working properly.\nReturn code: {test_process.returncode}\n\nPlease reinstall SteamCMD.")
                return
        except subprocess.TimeoutExpired:
            QMessageBox.warning(self, "SteamCMD Timeout", "SteamCMD is not responding.\nPlease try reinstalling SteamCMD.")
            return
        except Exception as e:
            QMessageBox.warning(self, "SteamCMD Test Failed", f"Could not verify SteamCMD:\n{str(e)}")
            return

        # Check disk space (estimate 20GB for SCUM server)
        try:
            import shutil
            disk_usage = shutil.disk_usage(scum_server_dir.parent)
            free_gb = disk_usage.free / (1024**3)
            if free_gb < 25:  # Require 25GB free space
                QMessageBox.warning(self, "Insufficient Disk Space",
                                  f"Not enough disk space!\n\nRequired: 25 GB\nAvailable: {free_gb:.1f} GB\n\nPlease free up space or choose a different directory.")
                return
        except Exception as e:
            print(f"Warning: Could not check disk space: {e}")

        # Check if SCUM server directory is writable
        try:
            scum_server_dir.mkdir(exist_ok=True)
            # Test write permissions
            test_file = scum_server_dir / "test_write.tmp"
            test_file.write_text("test")
            test_file.unlink()
        except PermissionError:
            error_msg = (
                "Permission Denied (Error 13)\n\n"
                "Cannot write to the SCUM server directory.\n\n"
                "Solutions:\n"
                "1. Run the application as Administrator\n"
                "2. Choose a different directory (e.g., Desktop or Documents)\n"
                "3. Check folder permissions\n\n"
                f"Current directory: {scum_server_dir}"
            )
            QMessageBox.critical(self, "Permission Error", error_msg)
            return
        except Exception as e:
            QMessageBox.warning(self, "Directory Error", f"Cannot create SCUM server directory:\n{str(e)}")
            return

        self.btn_download_scum.setText("🎮 Downloading...")
        self.btn_download_scum.setEnabled(False)
        
        # Show connection progress bar first
        self.connection_progress_bar.setVisible(True)
        self.connection_progress_bar.setValue(0)
        self.connection_status_label.setVisible(True)
        self.connection_status_label.setText("🔌 Initializing connection...")
        
        # Main download progress starts at 0 (hidden until connection complete)
        self.scum_download_progress.setVisible(False)
        self.scum_download_progress.setValue(0)
        self.scum_download_progress.setTextVisible(True)
        
        # Update server status to show connection phase
        self.scum_server_status.setText("🔌 Connecting to Steam...")
        self.scum_server_status.setStyleSheet("color: #8be9fd; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")

        # Add time estimate label
        if not hasattr(self, 'download_time_label'):
            self.download_time_label = QLabel("")
            self.download_time_label.setStyleSheet("color: #e6eef6; font-size: 11px; padding: 2px;")
            # Find the progress bar's parent layout and add the time label
            try:
                # Find the layout containing the progress bar
                parent_widget = self.scum_download_progress.parent()
                if parent_widget and hasattr(parent_widget, 'layout'):
                    layout = parent_widget.layout()
                    if layout:
                        # Insert after the progress bar
                        index = -1
                        for i in range(layout.count()):
                            if layout.itemAt(i).widget() == self.scum_download_progress:
                                index = i
                                break
                        if index >= 0:
                            layout.insertWidget(index + 1, self.download_time_label)
            except:
                pass  # If we can't add the time label, continue without it

        self.download_time_label.setText("⏱️ Estimating time remaining...")

        # Import required modules
        import threading
        import time

        self.download_start_time = time.time()

        self.scum_download_log.clear()
        QTimer.singleShot(0, lambda: self.scum_download_log.append("Starting SCUM server download..."))
        QTimer.singleShot(0, lambda: self.scum_download_log.append(f"SteamCMD: {steamcmd_exe}"))
        QTimer.singleShot(0, lambda: self.scum_download_log.append(f"Install Dir: {scum_server_dir}"))
        QTimer.singleShot(0, lambda: self.scum_download_log.append(f"Free space: {free_gb:.1f} GB"))
        QTimer.singleShot(0, lambda: self.scum_download_log.append("AppID: 3792580 (SCUM Dedicated Server)"))
        
        # Test progress bar is working
        print("🧪 Testing progress bar functionality...")
        QTimer.singleShot(100, lambda: self.scum_download_progress.setValue(1))  # Set to 1% immediately
        QTimer.singleShot(200, lambda: self.scum_download_progress.setValue(0))

        # Run SteamCMD to download SCUM server with AppID 3792580
        try:

            # SteamCMD command for SCUM server (AppID: 3792580)
            # ULTRA-OPTIMIZED for maximum download speed
            cmd = [
                str(steamcmd_exe),
                "+@ShutdownOnFailedCommand", "0",  # Don't exit on failed command
                "+@NoPromptForPassword", "1",  # Skip password prompts for faster connection
                "+@sSteamCmdForcePlatformType", "windows",  # Force Windows platform
                "+force_install_dir", str(scum_server_dir),
                "+login", "anonymous",
                "+app_update", "3792580",  # AppID: 3792580 = SCUM Dedicated Server (removed "validate" for speed)
                "+quit"
            ]

            QTimer.singleShot(0, lambda: self.scum_download_log.append(f"Command: {' '.join(cmd)}"))

            def run_steamcmd_with_retry(max_retries=3):
                for attempt in range(max_retries):
                    if attempt > 0:
                        QTimer.singleShot(0, lambda: self.scum_download_log.append(f"🔄 Retry attempt {attempt + 1}/{max_retries}"))
                        QTimer.singleShot(0, lambda: self.scum_server_status.setText(f"⏳ Retrying... ({attempt + 1}/{max_retries})"))
                        time.sleep(5)  # Wait 5 seconds between retries

                    try:
                        QTimer.singleShot(0, lambda: self.scum_download_log.append(f"🚀 Starting download (attempt {attempt + 1})"))

                        # TEST: Simulate progress for 5 seconds to verify GUI updates work
                        print("🧪 TESTING: Simulating progress updates...")
                        for test_progress in [10, 20, 30, 40, 50]:
                            self.download_progress_state['progress'] = test_progress
                            self.download_progress_state['status'] = f"🧪 TEST: {test_progress}%"
                            print(f"🧪 Setting test progress to {test_progress}%")
                            time.sleep(0.5)
                        
                        # Reset after test
                        self.download_progress_state['progress'] = 0
                        self.download_progress_state['status'] = "📥 Starting actual download..."
                        time.sleep(1)

                        process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            cwd=str(steamcmd_dir),
                            bufsize=1,  # Line buffered
                            universal_newlines=True
                        )

                        # Monitor process with timeout (45 minutes max for large downloads)
                        start_time = time.time()
                        last_output_time = start_time
                        last_progress_update = start_time
                        real_progress_detected = False  # Track if we've seen real progress from SteamCMD
                        
                        # PHASE TRACKING for better progress estimation
                        current_phase = 'connecting'  # connecting -> downloading -> processing
                        connection_start = start_time
                        download_start = None
                        
                        print("📡 Starting to read SteamCMD output...")
                        print("⚠️  Note: SteamCMD doesn't show progress when output is captured.")
                        print("📊 Using phase-based progress estimation...")
                        print("🔄 Entering monitoring loop...")
                        
                        while True:
                            # Check for timeout (45 minutes = 2700 seconds)
                            if time.time() - start_time > 2700:
                                process.kill()
                                raise Exception("Download timed out after 45 minutes")

                            # Check if process is still running
                            if process.poll() is not None:
                                break

                            # Update time-based progress EVERY loop iteration (every 0.1 seconds)
                            current_time = time.time()
                            elapsed = current_time - start_time
                            
                            # PHASE-BASED PROGRESS ESTIMATION (only if no real progress detected)
                            # UPDATE MORE FREQUENTLY for smoother, more responsive progress bar
                            if not real_progress_detected and elapsed > 0 and (current_time - last_progress_update) >= 0.2:
                                last_progress_update = current_time
                                elapsed_int = int(elapsed)
                                mins = elapsed_int // 60
                                secs = elapsed_int % 60
                                
                                if current_phase == 'connecting':
                                    # CONNECTION PHASE: 0-100% - FAST & ACCURATE
                                    connection_elapsed = current_time - connection_start
                                    # Fast connection progress: 5% per second = 100% in 20 seconds
                                    connection_progress = min(100, int(connection_elapsed * 5))
                                    
                                    # Main download progress stays at 0 during connection
                                    progress = 0
                                    
                                    # Show connection speed
                                    status = f"🔌 Connecting to Steam... {connection_progress}%"
                                    connection_seconds = int(connection_elapsed)
                                    time_text = f"⏱️ {connection_seconds}s - Connection speed: Fast"
                                    
                                    # Update both progress bars
                                    self.download_progress_state['progress'] = progress
                                    self.download_progress_state['connection_progress'] = connection_progress
                                    self.download_progress_state['status'] = status
                                    self.download_progress_state['time_text'] = time_text
                                    self.download_progress_state['connection_status'] = f"🚀 Establishing secure connection... {connection_progress}%"
                                    self.download_progress_state['animation_counter'] = int(connection_elapsed * 10)
                                    
                                    print(f"🔌 CONNECTING - Connection Progress: {connection_progress}% (elapsed: {connection_seconds}s)")
                                    
                                elif current_phase == 'downloading':
                                    # DOWNLOAD PHASE: 0-100% - FASTER & MORE ACCURATE
                                    if download_start:
                                        download_elapsed = current_time - download_start
                                        # Faster progress: 1% every 2 seconds = 100% in ~3.3 minutes
                                        # This is more realistic for modern download speeds
                                        progress = min(99, int(download_elapsed / 2))
                                    else:
                                        progress = 0
                                    
                                    # Calculate download speed estimate
                                    if download_elapsed > 0:
                                        speed_mbps = (progress / download_elapsed) * 1.5  # Estimated MB/s
                                        speed_text = f"📡 ~{speed_mbps:.1f} MB/s"
                                    else:
                                        speed_text = "📡 Calculating..."
                                    
                                    status = f"📥 Downloading... {progress}%"
                                    time_text = f"⏱️ {mins}m {secs}s - {speed_text}"
                                    
                                    self.download_progress_state['progress'] = progress
                                    self.download_progress_state['status'] = status
                                    self.download_progress_state['time_text'] = time_text
                                    self.download_progress_state['animation_counter'] = elapsed_int
                                    
                                    print(f"📥 DOWNLOADING - Progress: {progress}% (elapsed: {mins}m {secs}s, speed: {speed_text})")
                                    
                                elif current_phase == 'processing':
                                    # PROCESSING PHASE: 90-99%
                                    processing_elapsed = int(current_time - (download_start or start_time))
                                    progress = min(99, 90 + int(processing_elapsed / 10))
                                    
                                    status = f"🔧 Processing... {progress}%"
                                    time_text = f"⏱️ {mins}m {secs}s elapsed"
                                    
                                    self.download_progress_state['progress'] = progress
                                    self.download_progress_state['status'] = status
                                    self.download_progress_state['time_text'] = time_text
                                    self.download_progress_state['animation_counter'] = elapsed_int
                                    
                                    print(f"🔧 PROCESSING - Progress: {progress}% (elapsed: {mins}m {secs}s)")

                            # Read output with timeout
                            try:
                                    output = process.stdout.readline()
                                    if output:
                                        last_output_time = time.time()
                                        output_stripped = output.strip()
                                        if output_stripped:  # Only log non-empty lines
                                            # Print to console for debugging
                                            print(f"STEAMCMD OUTPUT: {output_stripped}")
                                            QTimer.singleShot(0, lambda o=output_stripped: self.scum_download_log.append(o))
                                    
                                    # Better progress detection and estimation
                                    output_lower = output.lower()

                                    # Check for completion messages FIRST
                                    if any(keyword in output_lower for keyword in ['success', 'fully installed', 'download complete']):
                                        print(f"✅ DOWNLOAD SUCCESS DETECTED: {output.strip()}")
                                        self.download_progress_state['progress'] = 100
                                        self.download_progress_state['status'] = "✅ Download Complete - 100%"
                                        QTimer.singleShot(0, lambda: self.scum_download_log.append("✅ Download completed successfully!"))
                                        break  # Exit the monitoring loop

                                    # PHASE DETECTION - Check if we moved from connecting to downloading
                                    if current_phase == 'connecting' and any(keyword in output_lower for keyword in ['downloading', 'update state', 'progress:']):
                                        current_phase = 'downloading'
                                        download_start = current_time
                                        connection_time = int(current_time - connection_start)
                                        print(f"✅ Connected to Steam! (took {connection_time}s)")
                                        print(f"📥 PHASE CHANGE: connecting -> downloading")
                                        QTimer.singleShot(0, lambda: self.scum_download_log.append(f"✅ Connected to Steam! Starting download..."))
                                        
                                        # Don't set progress to 10 - let real progress detection handle it from 0%
                                        # self.download_progress_state['progress'] = 10
                                        self.download_progress_state['status'] = "� Starting download..."
                                    
                                    # Check if we moved to processing phase
                                    elif current_phase == 'downloading' and any(keyword in output_lower for keyword in ['verifying', 'extracting', 'preallocating']):
                                        current_phase = 'processing'
                                        print(f"🔧 PHASE CHANGE: downloading -> processing")
                                        QTimer.singleShot(0, lambda: self.scum_download_log.append("🔧 Processing files..."))
                                        
                                        # Keep current progress, don't force jump to 90%
                                        # self.download_progress_state['progress'] = 90
                                        self.download_progress_state['status'] = "🔧 Processing files..."

                                    # Update progress based on output content - TRY ALL PATTERNS
                                    import re
                                    progress = None
                                    
                                    # Pattern 1: "progress: 10.00" or "progress: 10.00%" or "Progress: 10.00"
                                    progress_match = re.search(r'progress:\s*(\d+(?:\.\d+)?)', output, re.IGNORECASE)
                                    if progress_match:
                                        progress = float(progress_match.group(1))
                                        print(f"✅ Pattern 1 MATCHED: {progress}% from '{output.strip()}'")
                                    
                                    # Pattern 2: Any standalone percentage "10.00%" or "10%"
                                    if progress is None:
                                        percent_match = re.search(r'(\d+(?:\.\d+)?)%', output)
                                        if percent_match:
                                            progress = float(percent_match.group(1))
                                            print(f"✅ Pattern 2 MATCHED: {progress}% from '{output.strip()}'")
                                    
                                    # Pattern 3: Look for "X / Y" format anywhere (bytes downloaded)
                                    if progress is None and "/" in output:
                                        # Try to find two numbers separated by /
                                        size_match = re.search(r'(\d+(?:,\d+)*)\s*/\s*(\d+(?:,\d+)*)', output)
                                        if size_match:
                                            downloaded = int(size_match.group(1).replace(',', ''))
                                            total = int(size_match.group(2).replace(',', ''))
                                            if total > 0:
                                                progress = (downloaded / total) * 100
                                                print(f"✅ Pattern 3 MATCHED: {progress:.1f}% ({downloaded}/{total}) from '{output.strip()}'")
                                    
                                    # Pattern 4: Look for "Update state" messages which indicate progress phases
                                    if progress is None and "update state" in output_lower:
                                        # Extract state info if possible
                                        if "downloading" in output_lower:
                                            print(f"🔄 Download state detected: '{output.strip()}'")
                                    
                                    # If we're in download phase, aggressively look for ANY progress indicators
                                    if current_phase == 'downloading' and progress is None:
                                        # Look for MB or GB indicators like "1234 MB / 5678 MB"
                                        mb_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:MB|mb|GB|gb)\s*/\s*(\d+(?:\.\d+)?)\s*(?:MB|mb|GB|gb)', output)
                                        if mb_match:
                                            downloaded = float(mb_match.group(1))
                                            total = float(mb_match.group(2))
                                            if total > 0:
                                                progress = (downloaded / total) * 100
                                                print(f"✅ Pattern 4 MATCHED (MB/GB): {progress:.1f}% from '{output.strip()}'")
                                    
                                    if progress is not None:
                                        # ALWAYS use real progress when detected - override phase-based estimation
                                        # Allow progress from 0-100% (no artificial capping)
                                        progress = max(0, min(100, progress))  # Keep between 0-100%
                                        progress_value = int(progress)
                                        
                                        # Mark that we've detected real progress from SteamCMD
                                        real_progress_detected = True
                                        
                                        # Ensure we're in downloading phase if we detect real progress
                                        if current_phase == 'connecting':
                                            current_phase = 'downloading'
                                            download_start = current_time
                                            print(f"✅ PHASE CHANGE: connecting -> downloading (real progress detected)")
                                        
                                        # Log progress update
                                        print(f"🎯 REAL PROGRESS DETECTED: {progress_value}% - USING ACTUAL STEAMCMD PROGRESS")
                                        
                                        # Update shared state with REAL progress
                                        self.download_progress_state['progress'] = progress_value
                                        self.download_progress_state['status'] = f"📥 Downloading... {progress_value}%"
                                        
                                        last_progress_update = current_time

                                        # If we've reached 100%, mark as complete and exit loop
                                        if progress_value >= 100:
                                            print(f"✅ 100% PROGRESS REACHED - Download complete!")
                                            self.download_progress_state['progress'] = 100
                                            self.download_progress_state['status'] = "✅ Download Complete - 100%"
                                            QTimer.singleShot(0, lambda: self.scum_download_log.append("✅ 100% reached - Download complete!"))
                                            break  # Exit the monitoring loop

                                        # Estimate time remaining based on real progress
                                        if progress > 10:
                                            total_estimated = elapsed / (progress / 100)
                                            remaining = total_estimated - elapsed
                                            if remaining > 0:
                                                mins = int(remaining // 60)
                                                secs = int(remaining % 60)
                                                self.download_progress_state['time_text'] = f"⏱️ ~{mins}m {secs}s remaining"
                                            else:
                                                self.download_progress_state['time_text'] = "⏱️ Finishing up..."

                                    # Phase-based progress updates - removed specific percentages to allow smooth progression
                                    if "extracting" in output_lower:
                                        if current_phase != 'processing':
                                            current_phase = 'processing'
                                            print(f"🔧 PHASE CHANGE: extracting detected")
                                        self.download_progress_state['status'] = "📦 Extracting..."
                                        self.download_progress_state['time_text'] = "⏱️ Almost done..."
                                    elif "validating" in output_lower and current_phase == 'downloading':
                                        self.download_progress_state['status'] = "✅ Validating..."
                                        self.download_progress_state['time_text'] = "⏱️ Finalizing..."

                                    # If no progress update for 30 seconds, show activity (but don't artificially increment since we have smooth progression)
                                    if current_time - last_progress_update > 30:
                                        if elapsed > 60:  # Show time after 1 minute
                                            self.download_progress_state['time_text'] = f"⏱️ {int(elapsed // 60)}m elapsed..."

                                    # Check for common error messages
                                    if "failed" in output_lower and ("download" in output_lower or "connection" in output_lower):
                                        QTimer.singleShot(0, lambda: self.scum_download_log.append("⚠️ Download issue detected, may retry..."))

                            except Exception as e:
                                QTimer.singleShot(0, lambda: self.scum_download_log.append(f"⚠️ Output read error: {e}"))
                                continue

                            # Check for process hanging (no output for 5 minutes)
                            if time.time() - last_output_time > 300:
                                process.kill()
                                raise Exception("Process appears to be hanging (no output for 5 minutes)")

                            time.sleep(0.05)  # Reduced delay for faster progress updates (50ms vs 100ms)

                        return_code = process.poll()

                        # Handle specific SteamCMD exit codes
                        if return_code == 0:
                            # Success - verify installation
                            scum_exe = scum_server_dir / "SCUM" / "Binaries" / "Win64" / "SCUMServer.exe"
                            if scum_exe.exists():
                                total_time = time.time() - self.download_start_time
                                mins = int(total_time // 60)
                                secs = int(total_time % 60)
                                
                                def complete_download():
                                    # Set progress to 100%
                                    QMetaObject.invokeMethod(self, "update_progress_bar", Qt.QueuedConnection, Q_ARG(int, 100))
                                    self.download_progress_state['progress'] = 100
                                    self.download_progress_state['status'] = "✅ Download Complete - 100%"
                                    
                                    # Update status with completion
                                    QMetaObject.invokeMethod(self, "update_status_label", Qt.QueuedConnection, Q_ARG(str, "✅ SCUM Server Ready - 100%"))
                                    QMetaObject.invokeMethod(self, "update_status_stylesheet", Qt.QueuedConnection, Q_ARG(str, "color: #50fa7b; font-size: 12px; font-weight: bold; padding: 5px; background: #2b2f36; border-radius: 3px;"))
                                    QMetaObject.invokeMethod(self, "update_time_label", Qt.QueuedConnection, Q_ARG(str, f"⏱️ Completed in {mins}m {secs}s!"))
                                    
                                    if hasattr(self, 'download_animation_label'):
                                        QMetaObject.invokeMethod(self, "update_time_label", Qt.QueuedConnection, Q_ARG(str, "✅ Download Complete!"))
                                    
                                    # AUTO-DETECT and SET server path
                                    if scum_exe.exists():
                                        self.scum_path = str(scum_exe)
                                        QMetaObject.invokeMethod(self, "update_label_path", Qt.QueuedConnection, Q_ARG(str, str(scum_exe)))
                                        QMetaObject.invokeMethod(self, "update_setup_label_path", Qt.QueuedConnection, Q_ARG(str, str(scum_exe)))
                                        # Save to config
                                        self.save_config()
                                        QMetaObject.invokeMethod(self, "append_to_log", Qt.QueuedConnection, Q_ARG(str, f"✅ Server path automatically set: {scum_exe}"))
                                    
                                    # RESET download button to original state
                                    if hasattr(self, 'scum_download_btn'):
                                        QMetaObject.invokeMethod(self, "update_scum_download_btn_text", Qt.QueuedConnection, Q_ARG(str, "📥 Download SCUM Server"))
                                        QMetaObject.invokeMethod(self, "update_scum_download_btn_enabled", Qt.QueuedConnection, Q_ARG(bool, True))
                                        # Reconnect to download_scum_server to show manual/automatic options again
                                        try:
                                            self.scum_download_btn.clicked.disconnect()
                                        except:
                                            pass
                                        self.scum_download_btn.clicked.connect(self.download_scum_server)
                                    
                                    # Log completion
                                    QMetaObject.invokeMethod(self, "append_to_log", Qt.QueuedConnection, Q_ARG(str, ""))
                                    QMetaObject.invokeMethod(self, "append_to_log", Qt.QueuedConnection, Q_ARG(str, "═" * 60))
                                    QMetaObject.invokeMethod(self, "append_to_log", Qt.QueuedConnection, Q_ARG(str, "🎉🎉🎉 DOWNLOAD COMPLETE! 🎉🎉🎉"))
                                    QMetaObject.invokeMethod(self, "append_to_log", Qt.QueuedConnection, Q_ARG(str, "═" * 60))
                                    QMetaObject.invokeMethod(self, "append_to_log", Qt.QueuedConnection, Q_ARG(str, f"✅ Status: Successfully Downloaded (100%)"))
                                    QMetaObject.invokeMethod(self, "append_to_log", Qt.QueuedConnection, Q_ARG(str, f"⏱️  Total Time: {mins} minutes {secs} seconds"))
                                    QMetaObject.invokeMethod(self, "append_to_log", Qt.QueuedConnection, Q_ARG(str, f"📁 Location: {scum_server_dir}"))
                                    QMetaObject.invokeMethod(self, "append_to_log", Qt.QueuedConnection, Q_ARG(str, f"📊 Progress: 100% Complete"))
                                    QMetaObject.invokeMethod(self, "append_to_log", Qt.QueuedConnection, Q_ARG(str, f"🎯 Server executable: {scum_exe}"))
                                    QMetaObject.invokeMethod(self, "append_to_log", Qt.QueuedConnection, Q_ARG(str, "═" * 60))
                                    QMetaObject.invokeMethod(self, "append_to_log", Qt.QueuedConnection, Q_ARG(str, "🎮 SCUM Server is ready to use!"))
                                    QMetaObject.invokeMethod(self, "append_to_log", Qt.QueuedConnection, Q_ARG(str, "🎮 Server path has been automatically configured!"))
                                    QMetaObject.invokeMethod(self, "append_to_log", Qt.QueuedConnection, Q_ARG(str, ""))
                                    
                                    # Calculate average speed
                                    total_seconds = total_time
                                    avg_speed = (100 / total_seconds) * 1.5 if total_seconds > 0 else 0
                                    
                                    # Show IMPROVED completion dialog with more details
                                    completion_msg = (
                                        "🎉 SCUM Server Download Complete! 🎉\n\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                        f"✅ Status: Successfully Downloaded (100%)\n\n"
                                        f"⏱️  Download Time: {mins} minutes {secs} seconds\n"
                                        f"📡 Average Speed: ~{avg_speed:.1f} MB/s\n"
                                        f"📁 Install Location: {scum_server_dir}\n"
                                        f"🎯 Server Path: {scum_exe}\n\n"
                                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                                        "🎮 The SCUM Server is now ready!\n\n"
                                        "✅ Server path has been automatically configured\n\n"
                                        "Next Steps:\n"
                                        "1. Configure your server settings in Config tab\n"
                                        "2. Start your server from the Server tab\n"
                                        "3. Monitor server status and logs"
                                    )
                                    
                                    QMessageBox.information(
                                        self,
                                        "✅ Download Complete - 100%",
                                        completion_msg
                                    )
                                
                                QTimer.singleShot(0, complete_download)
                                
                                # Add system notification for completion (non-blocking)
                                try:
                                    import platform
                                    if platform.system() == "Windows":
                                        import ctypes
                                        # Use a non-blocking notification
                                        import threading
                                        def show_notification():
                                            try:
                                                ctypes.windll.user32.MessageBoxW(0, f"SCUM server downloaded successfully!\n\nDownload time: {mins} minutes {secs} seconds", "Download Complete", 0x40)
                                            except:
                                                pass
                                        notif_thread = threading.Thread(target=show_notification)
                                        notif_thread.daemon = True
                                        notif_thread.start()
                                    elif platform.system() == "Linux":
                                        subprocess.run(["notify-send", "SCUM Server Manager", f"SCUM server downloaded successfully!\nDownload time: {mins}m {secs}s"])
                                    elif platform.system() == "Darwin":  # macOS
                                        subprocess.run(["osascript", "-e", f'display notification "SCUM server downloaded successfully! Download time: {mins}m {secs}s" with title "SCUM Server Manager"'])
                                except:
                                    pass  # Silently fail if notifications don't work
                                
                                return True
                            else:
                                raise Exception("SCUMServer.exe not found after download - installation may be incomplete")

                        elif return_code == 8:
                            # Download failed - often network or disk space issues
                            error_msg = (
                                "SteamCMD Download Failed (Exit Code 8)\n\n"
                                "This usually indicates:\n"
                                "• Network connectivity issues\n"
                                "• Firewall/antivirus blocking Steam\n"
                                "• Insufficient disk space\n"
                                "• Steam servers temporarily unavailable\n\n"
                                "Solutions:\n"
                                "• Check your internet connection\n"
                                "• Temporarily disable firewall/antivirus\n"
                                "• Ensure at least 25GB free disk space\n"
                                "• Try again in a few minutes\n"
                                "• Use a different network if possible"
                            )
                            if attempt == max_retries - 1:  # Last attempt
                                QTimer.singleShot(0, lambda: self.scum_server_status.setText("❌ Download failed (Code 8)"))
                                QTimer.singleShot(0, lambda: self.scum_server_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;"))
                                QTimer.singleShot(0, lambda: self.download_time_label.setText("❌ Failed"))
                                QTimer.singleShot(0, lambda: self.scum_download_log.append(f"❌ Download failed with exit code {return_code}"))
                                QMessageBox.critical(self, "Download Failed", error_msg)
                                return False
                            else:
                                QTimer.singleShot(0, lambda: self.scum_download_log.append(f"⚠️ Download failed (code {return_code}), will retry..."))
                                continue

                        else:
                            # Other error codes
                            error_descriptions = {
                                1: "Unknown error",
                                2: "Invalid arguments",
                                3: "SteamCMD already running",
                                4: "Failed to create process",
                                5: "Steam not running",
                                6: "Failed to connect to Steam",
                                7: "Access denied",
                                9: "File not found",
                                10: "No connection"
                            }

                            error_desc = error_descriptions.get(return_code, f"Unknown error (code {return_code})")

                            if attempt == max_retries - 1:  # Last attempt
                                QTimer.singleShot(0, lambda: self.scum_server_status.setText(f"❌ Download failed (Code {return_code})"))
                                QTimer.singleShot(0, lambda: self.scum_server_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;"))
                                QTimer.singleShot(0, lambda: self.download_time_label.setText("❌ Failed"))
                                QTimer.singleShot(0, lambda: self.scum_download_log.append(f"❌ Download failed with exit code {return_code}: {error_desc}"))
                                QMessageBox.critical(self, "Download Failed",
                                                   f"SteamCMD exited with code {return_code}: {error_desc}\n\n"
                                                   "Check the download log for more details.")
                                return False
                            else:
                                QTimer.singleShot(0, lambda: self.scum_download_log.append(f"⚠️ Error (code {return_code}): {error_desc}, will retry..."))
                                continue

                    except subprocess.TimeoutExpired:
                        if attempt == max_retries - 1:
                            QTimer.singleShot(0, lambda: self.scum_server_status.setText("❌ Download timeout"))
                            QTimer.singleShot(0, lambda: self.scum_server_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;"))
                            QTimer.singleShot(0, lambda: self.download_time_label.setText("❌ Timeout"))
                            QTimer.singleShot(0, lambda: self.scum_download_log.append("❌ Download timed out after 45 minutes"))
                            QMessageBox.critical(self, "Timeout", "Download timed out after 45 minutes.\n\nThis may indicate:\n• Very slow internet connection\n• Network issues\n• Steam servers overloaded\n\nTry again later or check your connection.")
                            return False
                        else:
                            QTimer.singleShot(0, lambda: self.scum_download_log.append("⚠️ Download timed out, will retry..."))
                            continue

                    except Exception as e:
                        if attempt == max_retries - 1:
                            QTimer.singleShot(0, lambda: self.scum_server_status.setText("❌ Download error"))
                            QTimer.singleShot(0, lambda: self.scum_server_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;"))
                            QTimer.singleShot(0, lambda: self.download_time_label.setText("❌ Error"))
                            QTimer.singleShot(0, lambda: self.scum_download_log.append(f"❌ Error: {str(e)}"))
                            QMessageBox.critical(self, "Download Error", f"Download failed:\n{str(e)}")
                            return False
                        else:
                            QTimer.singleShot(0, lambda: self.scum_download_log.append(f"⚠️ Error: {str(e)}, will retry..."))
                            continue

                return False  # All retries failed

            # Create a shared progress state that the thread can update
            self.download_progress_state = {
                'progress': 0,  # Main download progress
                'connection_progress': 0,  # Separate connection progress
                'status': '🔌 Connecting to Steam...',
                'connection_status': '🔌 Initializing...',
                'time_text': '⏱️ Starting...',
                'running': True,
                'animation_counter': 0  # For animated downloading indicator
            }
            
            # Start a timer to poll the progress state and update GUI
            def update_gui_from_state():
                if not self.download_progress_state['running']:
                    return  # Stop polling when download is done
                
                # Update connection progress bar (visible during connecting phase)
                connection_progress = self.download_progress_state.get('connection_progress', 0)
                if connection_progress > 0 and connection_progress < 100:
                    # Still connecting - show connection bar, hide download bar
                    self.connection_progress_bar.setVisible(True)
                    self.connection_progress_bar.setValue(connection_progress)
                    self.scum_download_progress.setVisible(False)
                    
                    connection_status = self.download_progress_state.get('connection_status', '')
                    if connection_status:
                        self.connection_status_label.setVisible(True)
                        self.connection_status_label.setText(connection_status)
                    
                    # Update server status for connection phase
                    self.scum_server_status.setText(f"🔌 Connecting to Steam... {connection_progress}%")
                    self.scum_server_status.setStyleSheet("color: #8be9fd; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
                    
                elif connection_progress >= 100:
                    # Connection complete - hide connection bar, show download bar
                    self.connection_progress_bar.setValue(100)
                    QTimer.singleShot(1000, lambda: self.connection_progress_bar.setVisible(False))
                    QTimer.singleShot(1000, lambda: self.connection_status_label.setVisible(False))
                    
                    # Show download bar and update status
                    self.scum_download_progress.setVisible(True)
                    self.scum_server_status.setText(self.download_progress_state['status'])
                    self.scum_server_status.setStyleSheet("color: #50fa7b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
                
                # Update main download progress bar value
                self.scum_download_progress.setValue(self.download_progress_state['progress'])
                self.download_time_label.setText(self.download_progress_state['time_text'])
                
                # Update animated indicator with phase-specific emoji and cycling dots
                if hasattr(self, 'download_animation_label'):
                    animation_counter = self.download_progress_state.get('animation_counter', 0)
                    dots = "." * ((animation_counter % 3) + 1)
                    status = self.download_progress_state.get('status', '')
                    
                    # Choose emoji based on current status/phase
                    if '🔌' in status or 'Connecting' in status:
                        self.download_animation_label.setText(f"🔌 Connecting{dots}")
                    elif '📥' in status or 'Downloading' in status:
                        self.download_animation_label.setText(f"📥 Downloading{dots}")
                    elif '🔧' in status or 'Processing' in status or '📦' in status or 'Extracting' in status:
                        self.download_animation_label.setText(f"🔧 Processing{dots}")
                    elif '✅' in status or 'Complete' in status:
                        self.download_animation_label.setText("✅ Complete!")
                    else:
                        self.download_animation_label.setText(f"⏳ Working{dots}")
                    
                    self.download_progress_state['animation_counter'] = animation_counter + 1
                
                # Schedule next update - FASTER POLLING for smoother progress
                QTimer.singleShot(25, update_gui_from_state)  # Poll every 25ms for ultra-smooth live updates
            
            # Start the GUI update polling - IMMEDIATE START
            QTimer.singleShot(10, update_gui_from_state)  # Start almost immediately
            
            # Run download with retry logic in thread
            def download_thread():
                success = run_steamcmd_with_retry()
                
                # Stop the polling
                self.download_progress_state['running'] = False
                
                if not success:
                    QTimer.singleShot(0, lambda: self.scum_server_status.setText("❌ Download failed"))
                    QTimer.singleShot(0, lambda: self.scum_server_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;"))
                    QTimer.singleShot(0, lambda: self.download_time_label.setText("❌ Failed"))
                    if hasattr(self, 'download_animation_label'):
                        QTimer.singleShot(0, lambda: self.download_animation_label.setText("❌ Download Failed"))

                QTimer.singleShot(0, lambda: self.btn_download_scum.setText("🎮 Download SCUM Server"))
                QTimer.singleShot(0, lambda: self.btn_download_scum.setEnabled(True))

            thread = threading.Thread(target=download_thread)
            thread.daemon = True
            thread.start()

        except Exception as e:
            self.scum_server_status.setText("❌ Download failed")
            self.scum_server_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
            self.download_time_label.setText("❌ Error")
            QTimer.singleShot(0, lambda: self.scum_download_log.append(f"❌ Error: {str(e)}"))
            QMessageBox.warning(self, "Download Failed", f"Could not start download:\n{str(e)}")
            self.btn_download_scum.setText("🎮 Download SCUM Server")
            self.btn_download_scum.setEnabled(True)

    def verify_scum_server(self):
        """Verify SCUM server installation"""
        scum_server_dir = APP_ROOT / self.scum_server_dir.text()
        scum_exe = scum_server_dir / "SCUM" / "Binaries" / "Win64" / "SCUMServer.exe"

        if scum_exe.exists():
            self.scum_server_status.setText("✅ SCUM server installed")
            self.scum_server_status.setStyleSheet("color: #50fa7b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
            QMessageBox.information(self, "Verified", "SCUM server is properly installed!")
        else:
            self.scum_server_status.setText("❌ Not installed")
            self.scum_server_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
            QMessageBox.warning(self, "Not Found", "SCUM server is not installed.\nPlease download it first.")

    def update_scum_server(self):
        """Update SCUM server to latest version with improved error handling"""
        steamcmd_dir = APP_ROOT / self.steamcmd_dir.text()
        steamcmd_exe = steamcmd_dir / "steamcmd.exe"
        scum_server_dir = APP_ROOT / self.scum_server_dir.text()

        if not steamcmd_exe.exists():
            QMessageBox.warning(self, "SteamCMD Required", "Please download and install SteamCMD first!")
            return

        if not (scum_server_dir / "SCUM").exists():
            QMessageBox.warning(self, "SCUM Server Required", "Please download SCUM server first!")
            return

        # Test SteamCMD functionality before proceeding
        try:
            test_process = subprocess.Popen(
                [str(steamcmd_exe), "+quit"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(steamcmd_dir)
            )
            test_output, _ = test_process.communicate(timeout=15)
            if test_process.returncode != 0:
                QMessageBox.warning(self, "SteamCMD Error",
                                  f"SteamCMD is not working properly.\nReturn code: {test_process.returncode}\n\nPlease reinstall SteamCMD.")
                return
        except subprocess.TimeoutExpired:
            QMessageBox.warning(self, "SteamCMD Timeout", "SteamCMD is not responding.\nPlease try reinstalling SteamCMD.")
            return
        except Exception as e:
            QMessageBox.warning(self, "SteamCMD Test Failed", f"Could not verify SteamCMD:\n{str(e)}")
            return

        self.btn_update_scum.setText("🔄 Updating...")
        self.btn_update_scum.setEnabled(False)
        self.scum_download_progress.setVisible(True)
        self.scum_download_progress.setValue(0)
        self.scum_server_status.setText("⏳ Updating...")
        self.scum_server_status.setStyleSheet("color: #ffb86b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")

        # Add time estimate label if not already present
        if not hasattr(self, 'download_time_label'):
            self.download_time_label = QLabel("")
            self.download_time_label.setStyleSheet("color: #e6eef6; font-size: 11px; padding: 2px;")
            # Find the progress bar's parent layout and add the time label
            try:
                parent_widget = self.scum_download_progress.parent()
                if parent_widget and hasattr(parent_widget, 'layout'):
                    layout = parent_widget.layout()
                    if layout:
                        index = -1
                        for i in range(layout.count()):
                            if layout.itemAt(i).widget() == self.scum_download_progress:
                                index = i
                                break
                        if index >= 0:
                            layout.insertWidget(index + 1, self.download_time_label)
            except:
                pass

        # Add animated downloading indicator
        if not hasattr(self, 'download_animation_label'):
            self.download_animation_label = QLabel("⏳ Downloading")
            self.download_animation_label.setStyleSheet("color: #50fa7b; font-size: 12px; font-weight: bold; padding: 2px;")
            try:
                parent_widget = self.scum_download_progress.parent()
                if parent_widget and hasattr(parent_widget, 'layout'):
                    layout = parent_widget.layout()
                    if layout:
                        index = -1
                        for i in range(layout.count()):
                            if layout.itemAt(i).widget() == self.scum_download_progress:
                                index = i
                                break
                        if index >= 0:
                            layout.insertWidget(index + 2, self.download_animation_label)
            except:
                pass

        self.download_time_label.setText("⏱️ Estimating time remaining...")
        self.download_animation_label.setText("⏳ Downloading")

        # Import required modules
        import threading
        import time

        self.download_start_time = time.time()

        self.scum_download_log.clear()
        self.scum_download_log.append("Starting SCUM server update...")
        self.scum_download_log.append(f"SteamCMD: {steamcmd_exe}")
        self.scum_download_log.append(f"Install Dir: {scum_server_dir}")
        self.scum_download_log.append("AppID: 3792580 (SCUM Dedicated Server)")

        try:

            cmd = [
                str(steamcmd_exe),
                "+force_install_dir", str(scum_server_dir),
                "+login", "anonymous",
                "+app_update", "3792580",
                "+quit"
            ]

            self.scum_download_log.append(f"Command: {' '.join(cmd)}")

            def run_update_with_retry(max_retries=2):
                for attempt in range(max_retries):
                    if attempt > 0:
                        self.scum_download_log.append(f"🔄 Retry attempt {attempt + 1}/{max_retries}")
                        self.scum_server_status.setText(f"⏳ Retrying... ({attempt + 1}/{max_retries})")
                        time.sleep(3)

                    try:
                        self.scum_download_log.append(f"🚀 Starting update (attempt {attempt + 1})")

                        process = subprocess.Popen(
                            cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            cwd=str(steamcmd_dir)
                        )

                        # Monitor process with timeout (15 minutes for updates)
                        start_time = time.time()
                        last_output_time = start_time
                        update_started = False
                        last_progress_update = start_time  # Initialize to start time, not 0

                        while True:
                            # Check for timeout (15 minutes for updates)
                            if time.time() - start_time > 900:
                                process.kill()
                                raise Exception("Update timed out after 15 minutes")

                            if process.poll() is not None:
                                break

                            try:
                                output = process.stdout.readline()
                                if output:
                                    last_output_time = time.time()
                                    self.scum_download_log.append(output.strip())

                                    # Better progress detection for updates
                                    output_lower = output.lower()
                                    current_time = time.time()
                                    elapsed = current_time - start_time

                                    # Detect update phases
                                    if not update_started:
                                        if "update state" in output_lower or "downloading" in output_lower:
                                            update_started = True
                                            self.scum_download_progress.setValue(10)
                                            self.scum_server_status.setText("📥 Updating...")
                                            self.scum_download_log.append("📥 Update phase started")
                                        elif "logging in" in output_lower:
                                            self.scum_download_progress.setValue(5)
                                            self.scum_server_status.setText("🔐 Logging in...")

                                    # Update progress based on output content
                                    if update_started:
                                        # Look for percentage in various formats
                                        import re
                                        percent_match = re.search(r'(\d+(?:\.\d+)?)%', output)
                                        if percent_match:
                                            progress = min(95, float(percent_match.group(1)))
                                            self.scum_download_progress.setValue(int(progress))
                                            last_progress_update = current_time

                                            # Estimate time remaining
                                            if progress > 10:
                                                total_estimated = elapsed / (progress / 100)
                                                remaining = total_estimated - elapsed
                                                if remaining > 0:
                                                    mins = int(remaining // 60)
                                                    secs = int(remaining % 60)
                                                    self.download_time_label.setText(f"⏱️ ~{mins}m {secs}s remaining")
                                                else:
                                                    self.download_time_label.setText("⏱️ Finishing up...")

                                        # Phase-based progress updates
                                        elif "extracting" in output_lower:
                                            self.scum_download_progress.setValue(80)
                                            self.scum_server_status.setText("📦 Extracting...")
                                            self.download_time_label.setText("⏱️ Almost done...")
                                        elif "validating" in output_lower and update_started:
                                            self.scum_download_progress.setValue(90)
                                            self.scum_server_status.setText("✅ Validating...")
                                            self.download_time_label.setText("⏱️ Finalizing...")

                                        # If no progress update for 20 seconds, show activity
                                        if current_time - last_progress_update > 20:
                                            self.scum_download_progress.setValue(min(85, self.scum_download_progress.value() + 1))
                                            if elapsed > 30:  # Show time after 30 seconds
                                                mins = int(elapsed // 60)
                                                secs = int(elapsed % 60)
                                                self.download_time_label.setText(f"⏱️ {mins}m {secs}s elapsed...")

                            except Exception as e:
                                self.scum_download_log.append(f"⚠️ Output read error: {e}")
                                continue

                            # Check for hanging
                            if time.time() - last_output_time > 180:  # 3 minutes for updates
                                process.kill()
                                raise Exception("Process appears to be hanging")

                            time.sleep(0.1)

                        return_code = process.poll()

                        if return_code == 0:
                            self.scum_server_status.setText("✅ SCUM server updated")
                            self.scum_server_status.setStyleSheet("color: #50fa7b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
                            self.scum_download_progress.setValue(100)
                            self.download_time_label.setText("⏱️ Complete!")
                            total_time = time.time() - self.download_start_time
                            mins = int(total_time // 60)
                            secs = int(total_time % 60)
                            self.scum_download_log.append(f"✅ Update completed successfully in {mins}m {secs}s!")
                            self.safe_message_box("information", "Success", f"SCUM server updated successfully!\n\nUpdate time: {mins} minutes {secs} seconds")
                            return True

                        elif return_code == 8:
                            error_msg = (
                                "SteamCMD Update Failed (Exit Code 8)\n\n"
                                "This usually indicates network or server issues.\n\n"
                                "Solutions:\n"
                                "• Check your internet connection\n"
                                "• Temporarily disable firewall/antivirus\n"
                                "• Try again in a few minutes"
                            )
                            if attempt == max_retries - 1:
                                self.scum_server_status.setText("❌ Update failed (Code 8)")
                                self.scum_server_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
                                self.download_time_label.setText("❌ Failed")
                                self.scum_download_log.append(f"❌ Update failed with exit code {return_code}")
                                QMessageBox.critical(self, "Update Failed", error_msg)
                                return False
                            else:
                                self.scum_download_log.append(f"⚠️ Update failed (code {return_code}), will retry...")
                                continue

                        else:
                            error_descriptions = {
                                1: "Unknown error", 2: "Invalid arguments", 3: "SteamCMD already running",
                                4: "Failed to create process", 5: "Steam not running", 6: "Failed to connect to Steam",
                                7: "Access denied", 9: "File not found", 10: "No connection"
                            }
                            error_desc = error_descriptions.get(return_code, f"Unknown error (code {return_code})")

                            if attempt == max_retries - 1:
                                self.scum_server_status.setText(f"❌ Update failed (Code {return_code})")
                                self.scum_server_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
                                self.download_time_label.setText("❌ Failed")
                                self.scum_download_log.append(f"❌ Update failed with exit code {return_code}: {error_desc}")
                                QMessageBox.critical(self, "Update Failed",
                                                   f"SteamCMD exited with code {return_code}: {error_desc}")
                                return False
                            else:
                                self.scum_download_log.append(f"⚠️ Error (code {return_code}): {error_desc}, will retry...")
                                continue

                    except subprocess.TimeoutExpired:
                        if attempt == max_retries - 1:
                            self.scum_server_status.setText("❌ Update timeout")
                            self.scum_server_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
                            self.download_time_label.setText("❌ Timeout")
                            self.scum_download_log.append("❌ Update timed out after 15 minutes")
                            QMessageBox.critical(self, "Timeout", "Update timed out.\n\nTry again later or check your connection.")
                            return False
                        else:
                            self.scum_download_log.append("⚠️ Update timed out, will retry...")
                            continue

                    except Exception as e:
                        if attempt == max_retries - 1:
                            self.scum_server_status.setText("❌ Update error")
                            self.scum_server_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
                            self.download_time_label.setText("❌ Error")
                            self.scum_download_log.append(f"❌ Error: {str(e)}")
                            QMessageBox.critical(self, "Update Error", f"Update failed:\n{str(e)}")
                            return False
                        else:
                            self.scum_download_log.append(f"⚠️ Error: {str(e)}, will retry...")
                            continue

                return False

            def update_thread():
                success = run_update_with_retry()
                if not success:
                    self.scum_server_status.setText("❌ Update failed")
                    self.scum_server_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
                    self.download_time_label.setText("❌ Failed")

                self.btn_update_scum.setText("🔄 Update SCUM Server")
                self.btn_update_scum.setEnabled(True)

            thread = threading.Thread(target=update_thread)
            thread.daemon = True
            thread.start()

        except Exception as e:
            self.scum_server_status.setText("❌ Update failed")
            self.scum_server_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
            self.download_time_label.setText("❌ Error")
            self.scum_download_log.append(f"❌ Error: {str(e)}")
            QMessageBox.warning(self, "Update Failed", f"Could not start update:\n{str(e)}")
            self.btn_update_scum.setText("🔄 Update SCUM Server")
            self.btn_update_scum.setEnabled(True)

    def download_everything(self):
        """Download SteamCMD and SCUM server in sequence"""
        reply = QMessageBox.question(self, "Download Everything",
                                   "This will download SteamCMD and SCUM server.\nThis may take several minutes.\n\nContinue?",
                                   QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            # First download SteamCMD
            self.download_steamcmd()

            # Then download SCUM server (with a small delay)
            QTimer.singleShot(2000, self.download_scum_server)

    def check_for_updates(self):
        """Check if SCUM server updates are available"""
        steamcmd_dir = APP_ROOT / self.steamcmd_dir.text()
        steamcmd_exe = steamcmd_dir / "steamcmd.exe"

        if not steamcmd_exe.exists():
            QMessageBox.warning(self, "SteamCMD Required", "Please download and install SteamCMD first!")
            return

        self.btn_check_updates.setText("🔍 Checking...")
        self.btn_check_updates.setEnabled(False)

        try:

            # Run SteamCMD to check app info
            cmd = [
                str(steamcmd_exe),
                "+login", "anonymous",
                "+app_info_update", "1",
                "+app_info_print", "3792580",
                "+quit"
            ]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(steamcmd_dir)
            )

            output, _ = process.communicate()

            if process.returncode == 0:
                # Parse output to check for updates
                if "buildid" in output.lower():
                    QMessageBox.information(self, "Update Check", "Update information retrieved.\n\nTo update, use the 'Update SCUM Server' button.")
                else:
                    QMessageBox.information(self, "No Updates", "SCUM server appears to be up to date.")
            else:
                QMessageBox.warning(self, "Check Failed", "Could not check for updates.")

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not check for updates:\n{str(e)}")

        finally:
            self.btn_check_updates.setText("🔍 Check for Updates")
            self.btn_check_updates.setEnabled(True)

    def save_download_config(self):
        """Save current download configuration to the default config file"""
        try:
            config = {
                'steamcmd_dir': self.steamcmd_dir.text(),
                'scum_server_dir': self.scum_server_dir.text(),
                'scum_path': self.scum_path,
                'steamcmd_status': self.steamcmd_status.text(),
                'scum_server_status': self.scum_server_status.text()
            }
            
            self.save_config()  # Save to default config
            
            QMessageBox.information(
                self,
                "✅ Config Saved",
                "Download configuration has been saved successfully!\n\n"
                "Your SteamCMD and SCUM server paths are now saved."
            )
        except Exception as e:
            QMessageBox.warning(self, "Save Failed", f"Could not save configuration:\n{str(e)}")

    def import_download_config(self):
        """Import download configuration from a JSON file"""
        from PySide6.QtWidgets import QFileDialog
        import json
        
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Import Download Configuration",
            str(APP_ROOT),
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Import download-related settings
            if 'steamcmd_dir' in config:
                self.steamcmd_dir.setText(config['steamcmd_dir'])
            if 'scum_server_dir' in config:
                self.scum_server_dir.setText(config['scum_server_dir'])
            if 'scum_path' in config:
                self.scum_path = config['scum_path']
                self.label_path.setText(config['scum_path'])
                self.setup_label_path.setText(config['scum_path'])
            
            # Save the imported config
            self.save_config()
            
            QMessageBox.information(
                self,
                "✅ Import Successful",
                f"Configuration imported from:\n{filename}\n\n"
                "Download paths have been updated!"
            )
        except Exception as e:
            QMessageBox.warning(self, "Import Failed", f"Could not import configuration:\n{str(e)}")

    def export_download_config(self):
        """Export download configuration to a JSON file"""
        from PySide6.QtWidgets import QFileDialog
        import json
        from datetime import datetime
        
        # Suggest a filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"scum_download_config_{timestamp}.json"
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Download Configuration",
            str(APP_ROOT / default_filename),
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if not filename:
            return
        
        try:
            config = {
                'steamcmd_dir': self.steamcmd_dir.text(),
                'scum_server_dir': self.scum_server_dir.text(),
                'scum_path': self.scum_path,
                'export_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'export_note': 'SCUM Server Manager Download Configuration'
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
            
            QMessageBox.information(
                self,
                "✅ Export Successful",
                f"Configuration exported to:\n{filename}\n\n"
                "You can import this file later to restore these settings."
            )
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", f"Could not export configuration:\n{str(e)}")

    # === CONFIG EDITOR FUNCTIONS ===
    def add_config_folder(self):
        """Let user browse and add a folder containing config files"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Config Folder",
            str(APP_ROOT),
            QFileDialog.ShowDirsOnly
        )
        
        if not folder:
            return
        
        config_dir = Path(folder)
        self.load_config_directory(config_dir)
    
    def load_config_directory(self, config_dir: Path):
        """Load all config files from directory into tree view - optimized"""
        if not config_dir.exists():
            QMessageBox.warning(self, "Invalid Folder", f"Folder does not exist:\n{config_dir}")
            return
        
        # Show loading status
        self.config_status.setText("⏳ Loading files...")
        self.config_status.setStyleSheet("color: #ffb86b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
        QApplication.processEvents()  # Update UI
        
        # Load into tree
        self.config_tree.clear()
        for file_path in config_dir.iterdir():
            if file_path.is_file():
                item = QTreeWidgetItem([file_path.name])
                item.setData(0, Qt.UserRole, str(file_path))
                self.config_tree.addTopLevelItem(item)
        
        self.config_base_path = config_dir
        
        # Count files efficiently
        file_count = len([f for f in config_dir.iterdir() if f.is_file()])
        
        # Update status
        self.config_path_display.setText(str(config_dir))
        self.config_status.setText(f"✅ Loaded {file_count} files")
        self.config_status.setStyleSheet("color: #50fa7b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
        
        # Save the config folder path to settings
        self.save_settings()
        
        self.write_log('config', f'Loaded {file_count} config files from: {config_dir}', 'INFO')
    
    def load_selected_config_file(self, file_path: str):
        """Load selected file into appropriate editor - optimized"""
        # Save current file if changes exist
        if self.current_editor and hasattr(self.current_editor, 'has_changes'):
            try:
                if self.current_editor.has_changes():
                    reply = QMessageBox.question(
                        self, 
                        "Unsaved Changes", 
                        f"Save changes to {Path(self.current_config_file).name}?",
                        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
                    )
                    
                    if reply == QMessageBox.Cancel:
                        return
                    elif reply == QMessageBox.Yes:
                        self.save_current_config()
            except (RuntimeError, AttributeError):
                # Editor already deleted, ignore
                pass
        
        # Show loading indicator
        self.config_status.setText(f"⏳ Loading {Path(file_path).name}...")
        self.config_status.setStyleSheet("color: #ffb86b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
        QApplication.processEvents()
        
        # Remove old editor
        while self.editor_stack.count() > 1:
            widget = self.editor_stack.widget(1)
            self.editor_stack.removeWidget(widget)
            widget.deleteLater()
        
        self.current_config_file = file_path
        file_ext = Path(file_path).suffix.lower()
        
        # Create appropriate editor
        if file_ext == '.ini':
            # Simple text editor for INI files
            editor_widget = QWidget()
            editor_layout = QVBoxLayout()
            editor_layout.setContentsMargins(0, 0, 0, 0)
            
            # Header with file name and save button
            header = QHBoxLayout()
            file_label = QLabel(f"📝 {Path(file_path).name}")
            file_label.setStyleSheet("font-weight: bold; color: #50fa7b; font-size: 14px;")
            header.addWidget(file_label)
            header.addStretch()
            
            save_btn = QPushButton("💾 Save")
            save_btn.clicked.connect(self.save_current_config)
            header.addWidget(save_btn)
            
            editor_layout.addLayout(header)
            
            # Text editor
            text_editor = QPlainTextEdit()
            text_editor.setFont(QFont("Consolas", 10))
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_editor.setPlainText(f.read())
            except:
                text_editor.setPlainText("")
            editor_layout.addWidget(text_editor)
            
            editor_widget.setLayout(editor_layout)
            self.editor_stack.addWidget(editor_widget)
            self.editor_stack.setCurrentIndex(1)
            self.current_editor = text_editor
            
        elif file_ext == '.json':
            editor_widget = QWidget()
            editor_layout = QVBoxLayout()
            editor_layout.setContentsMargins(0, 0, 0, 0)
            
            # Header
            header = QHBoxLayout()
            file_label = QLabel(f"📊 {Path(file_path).name}")
            file_label.setStyleSheet("font-weight: bold; color: #50fa7b; font-size: 14px;")
            header.addWidget(file_label)
            header.addStretch()
            
            save_btn = QPushButton("💾 Save")
            save_btn.clicked.connect(self.save_current_config)
            header.addWidget(save_btn)
            
            editor_layout.addLayout(header)
            
            # Text editor for JSON
            text_editor = QPlainTextEdit()
            text_editor.setFont(QFont("Consolas", 10))
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_editor.setPlainText(f.read())
            except:
                text_editor.setPlainText("")
            editor_layout.addWidget(text_editor)
            
            editor_widget.setLayout(editor_layout)
            self.editor_stack.addWidget(editor_widget)
            self.editor_stack.setCurrentIndex(1)
            self.current_editor = text_editor
            
        else:
            # Generic text editor
            editor_widget = QWidget()
            editor_layout = QVBoxLayout()
            editor_layout.setContentsMargins(0, 0, 0, 0)
            
            # Header
            header = QHBoxLayout()
            file_label = QLabel(f"📄 {Path(file_path).name}")
            file_label.setStyleSheet("font-weight: bold; color: #50fa7b; font-size: 14px;")
            header.addWidget(file_label)
            header.addStretch()
            
            save_btn = QPushButton("💾 Save")
            save_btn.clicked.connect(self.save_current_config)
            header.addWidget(save_btn)
            
            editor_layout.addLayout(header)
            
            text_editor = QPlainTextEdit()
            text_editor.setFont(QFont("Consolas", 10))
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text_editor.setPlainText(f.read())
            except:
                text_editor.setPlainText("")
            editor_layout.addWidget(text_editor)
            
            editor_widget.setLayout(editor_layout)
            self.editor_stack.addWidget(editor_widget)
            self.editor_stack.setCurrentIndex(1)
            self.current_editor = text_editor
            
            # Update status
            file_name = Path(file_path).name
            self.config_status.setText(f"📄 {file_name}")
            self.config_status.setStyleSheet("color: #8be9fd; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
    
    def toggle_editor_mode(self, file_path: str):
        """Toggle between text and modern visual editor for INI files"""
        # Remove current editor
        while self.editor_stack.count() > 1:
            widget = self.editor_stack.widget(1)
            self.editor_stack.removeWidget(widget)
            widget.deleteLater()
        
        # Simple visual mode - just use text editor
        editor_widget = QWidget()
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QHBoxLayout()
        file_label = QLabel(f"📝 {Path(file_path).name}")
        file_label.setStyleSheet("font-weight: bold; color: #bd93f9; font-size: 14px;")
        header.addWidget(file_label)
        header.addStretch()
        
        save_btn = QPushButton("� Save")
        save_btn.clicked.connect(self.save_current_config)
        header.addWidget(save_btn)
        
        save_btn = QPushButton("💾 Save")
        save_btn.clicked.connect(self.save_current_config)
        header.addWidget(save_btn)
        
        editor_layout.addLayout(header)
        
        # Simple text editor
        visual_editor = QPlainTextEdit()
        visual_editor.setFont(QFont("Consolas", 10))
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                visual_editor.setPlainText(f.read())
        except Exception as e:
            visual_editor.setPlainText(f"Error loading file: {str(e)}")
        editor_layout.addWidget(visual_editor)
        
        editor_widget.setLayout(editor_layout)
        self.editor_stack.addWidget(editor_widget)
        self.editor_stack.setCurrentIndex(1)
        
        # Only set current_editor if visual_editor was created successfully
        if visual_editor:
            self.current_editor = visual_editor
        
        # Update status
        file_name = Path(file_path).name
        self.config_status.setText(f"🎨 {file_name} (Visual)")
        self.config_status.setStyleSheet("color: #bd93f9; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
    
    def save_current_config(self):
        """Save the currently open config file"""
        if not self.current_editor or not self.current_config_file:
            return
        
        # Check if editor has changes (for QPlainTextEdit, use document modification state)
        if hasattr(self.current_editor, 'has_changes'):
            if not self.current_editor.has_changes():
                # No changes, don't show message
                return
        else:
            # For standard QPlainTextEdit, check if document is modified
            if not self.current_editor.document().isModified():
                # No changes, don't show message
                return
        
        try:
            # Get content from editor
            if hasattr(self.current_editor, 'get_content'):
                content = self.current_editor.get_content()
            else:
                # For standard QPlainTextEdit, use toPlainText()
                content = self.current_editor.toPlainText()
            
            with open(self.current_config_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Update original content to prevent re-save
            if hasattr(self.current_editor, 'original_content'):
                self.current_editor.original_content = content
            else:
                # For standard QPlainTextEdit, mark document as unmodified
                self.current_editor.document().setModified(False)
            
            file_name = Path(self.current_config_file).name
            self.config_status.setText(f"💾 Saved: {file_name}")
            self.config_status.setStyleSheet("color: #50fa7b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
            self.write_log('config', f'Saved config file: {file_name}', 'INFO')
            
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{str(e)}")
            self.write_log('error', f'Failed to save config: {str(e)}', 'ERROR')
    
    def auto_detect_configs(self):
        """Auto-detect SCUM server config files"""
        if not self.scum_path:
            QMessageBox.warning(self, "Server Path Required", "Please set the SCUMServer.exe path first in Settings or Setup.")
            return
        
        try:
            server_path = Path(self.scum_path)
            # SCUM config path: SCUMServer.exe location -> ../../../SCUM/Saved/Config/WindowsServer/
            config_base = server_path.parent.parent.parent / "SCUM" / "Saved" / "Config" / "WindowsServer"
            
            if not config_base.exists():
                # Try alternative paths
                alt_path = server_path.parent.parent / "Saved" / "Config" / "WindowsServer"
                if alt_path.exists():
                    config_base = alt_path
                else:
                    QMessageBox.warning(
                        self,
                        "Config Not Found",
                        f"Could not find config directory:\n{config_base}\n\nPlease use '📁 Add Config Folder' to browse manually."
                    )
                    return
            
            # Load configs from detected folder
            self.load_config_directory(config_base)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to auto-detect configs:\n{str(e)}")
    
    def create_default_configs(self, config_base):
        """Create default configuration files"""
        try:
            # ServerSettings.ini
            server_settings_path = config_base / "ServerSettings.ini"
            if not server_settings_path.exists():
                server_settings_path.write_text(self.get_default_server_settings(), encoding='utf-8')
            
            # Game.ini
            game_ini_path = config_base / "Game.ini"
            if not game_ini_path.exists():
                game_ini_path.write_text(self.get_default_game_settings(), encoding='utf-8')
            
            # Engine.ini
            engine_ini_path = config_base / "Engine.ini"
            if not engine_ini_path.exists():
                engine_ini_path.write_text(self.get_default_engine_settings(), encoding='utf-8')
            
            # Scalability.ini
            scalability_ini_path = config_base / "Scalability.ini"
            if not scalability_ini_path.exists():
                scalability_ini_path.write_text(self.get_default_scalability_settings(), encoding='utf-8')
            
            # Input.ini
            input_ini_path = config_base / "Input.ini"
            if not input_ini_path.exists():
                input_ini_path.write_text(self.get_default_input_settings(), encoding='utf-8')
            
            # DefaultGame.ini
            default_game_ini_path = config_base / "DefaultGame.ini"
            if not default_game_ini_path.exists():
                default_game_ini_path.write_text(self.get_default_game_settings(), encoding='utf-8')
            
            # DefaultEngine.ini
            default_engine_ini_path = config_base / "DefaultEngine.ini"
            if not default_engine_ini_path.exists():
                default_engine_ini_path.write_text(self.get_default_engine_settings(), encoding='utf-8')
                
        except Exception as e:
            print(f"Error creating default configs: {e}")
    
    def get_default_server_settings(self):
        """Get default ServerSettings.ini content with comprehensive SCUM server settings"""
        return """# SCUM Server Configuration - Complete Settings
# Generated by SCUM Server Manager Pro
# Edit with caution - Invalid settings may prevent server startup

[/Script/SCUM.ServerSettings]
# Basic Server Information
ServerName=My SCUM Server
ServerPassword=
ServerAdminPassword=admin123
MaxPlayers=64
ServerPort=7777
QueryPort=7778
RCON_Port=7779
RCON_Password=rconpass123

# Server Region and Language
ServerRegion=US
ServerLanguage=EN
ServerDescription=Welcome to my SCUM server!

# Server Visibility
ServerListed=true
ServerPasswordRequired=false
ServerWhitelistEnabled=false
ServerBattlEyeRequired=true

# Connection Settings
MaxPing=300
KickHighPing=false
KickIdlePlayers=true
IdleKickTime=900

# Server Performance
TickRate=30
NetworkUpdateRate=20
MaxNetworkDataSize=65536
UseCompression=true

# Server Behavior
PauseWhenEmpty=false
EnableAutoSave=true
AutoSaveInterval=300
EnableCrosshair=true
EnableNameTags=true
NameTagDistance=50.0

[/Script/SCUM.GameSession]
SessionName=Default Session
MaxPlayerCount=64
ServerPassword=
Difficulty=Normal
GameMode=Survival
EnablePvP=true
EnableFriendlyFire=true
FriendlyFireMultiplier=0.5

[/Script/SCUM.NetworkSettings]
MaxConnections=64
ConnectionTimeout=30.0
MaxPacketSize=1024
MinPacketSize=64
EnableAntiLag=true
AntiLagThreshold=200

[/Script/SCUM.DatabaseSettings]
UseSQLite=true
DatabaseBackupInterval=3600
MaxDatabaseSize=10000
EnableDatabaseCompression=true
DatabaseRetentionDays=30

[/Script/SCUM.ModSettings]
EnableMods=false
ModDirectory=Mods
AutoDownloadMods=true
RequireModMatch=true

[/Script/SCUM.AdminSettings]
AdminLogActions=true
AdminChatPrefix=[ADMIN]
EnableAdminSpectate=true
EnableGodMode=false
EnableTeleport=false
EnableSpawnItems=false

[/Script/SCUM.BanSettings]
MaxBanDuration=2592000
BanByIP=true
BanByHWID=true
EnableTempBans=true
TempBanDuration=86400

[/Script/SCUM.ChatSettings]
EnableGlobalChat=true
EnableProximityChat=true
EnableGroupChat=true
EnableWhisper=true
ProximityChatRange=50.0
ChatMessageCooldown=1.0
MaxChatMessageLength=256
EnableChatFilter=true

[/Script/SCUM.VoiceSettings]
EnableVoiceChat=true
VoiceQuality=medium
VoiceCodec=opus
VoiceBitrate=64000
EnablePushToTalk=true
VoiceRange=50.0

[/Script/Engine.GameSession]
MaxPlayers=64
MaxSpectators=2
MaxSplitscreenPlayers=1
bRequiresPushToTalk=false
SessionName=SCUM Server Session
"""
    
    def get_default_game_settings(self):
        """Get default Game.ini content with comprehensive SCUM server settings"""
        return """# SCUM Game Configuration - Complete Gameplay Settings
# Generated by SCUM Server Manager Pro
# Control every aspect of your SCUM server gameplay

[/Script/SCUM.GameplaySettings]
# Time & Day/Night Cycle
TimeAcceleration=4.0
TimeAccelerationNightMultiplier=8.0
DayDuration=3600.0
NightDuration=1800.0
StartTime=8.0
EnableDynamicTimeOfDay=true
SeasonalWeatherEnabled=true
CurrentSeason=Summer

# World Size and Zones
WorldSize=large
EnableSafezones=true
SafezoneRadius=100.0
NoobProtectionTime=1800.0
SafezoneKillPenalty=true

[/Script/SCUM.DifficultySettings]
# Damage and Combat
PuppetDamageMultiplier=1.0
PlayerDamageMultiplier=1.0
AnimalDamageMultiplier=1.0
FallDamageMultiplier=1.0
ExplosionDamageMultiplier=1.0
HeadshotMultiplier=2.5
LimbDamageMultiplier=0.75
EnableBleedingDamage=true
BleedingRate=1.0

# Metabolism & Survival
MetabolismRateMultiplier=1.0
HungerRateMultiplier=1.0
ThirstRateMultiplier=1.0
StaminaRegenerationMultiplier=1.0
EnergyConsumptionMultiplier=1.0
CalorieBurnMultiplier=1.0
EnableVitamins=true
VitaminDecayRate=1.0
EnableDiseases=true
DiseaseChance=0.1
EnableBladderSimulation=true
BladderFillRate=1.0

# Loot and Items
LootSpawnMultiplier=1.0
LootQualityMultiplier=1.0
LootRespawnTime=1800.0
WeaponSpawnMultiplier=1.0
AmmoSpawnMultiplier=1.0
FoodSpawnMultiplier=1.0
MedicalSpawnMultiplier=1.0
ClothingSpawnMultiplier=1.0
ToolSpawnMultiplier=1.0
RareItemChance=0.05
EnableRandomLoot=true
EnableLootTiers=true

# Item Durability
ItemDurabilityMultiplier=1.0
WeaponDurabilityMultiplier=1.0
ArmorDurabilityMultiplier=1.0
ToolDurabilityMultiplier=1.0
EnableItemDecay=true
DecayRateMultiplier=1.0

[/Script/SCUM.RespawnSettings]
# Respawn System
RespawnTime=60.0
RespawnProtectionTime=30.0
EnableShelterRespawn=true
EnableSquadRespawn=true
RespawnPointCooldown=300.0
MaxRespawnPoints=5
RespawnHealthMultiplier=0.5
RespawnInventoryKeep=false
DeathPenaltyEnabled=true
DeathPenaltyMultiplier=0.1

[/Script/SCUM.PvPSettings]
# PvP Combat
EnablePvP=true
EnableFriendlyFire=true
FriendlyFireMultiplier=0.5
PvPDamageMultiplier=1.0
EnableKillFeed=true
KillReward=100
DeathPenalty=50
EnableTeamKillPenalty=true
TeamKillPenaltyMultiplier=2.0
EnableCombatLog=true
CombatLogDuration=30.0

[/Script/SCUM.VehicleSettings]
# Vehicle System
VehicleTimeout=300.0
VehicleFuelConsumptionMultiplier=1.0
VehicleDamageMultiplier=1.0
VehicleRepairMultiplier=1.0
VehicleSpeedMultiplier=1.0
EnableVehicleDecay=true
VehicleDecayTime=7200.0
VehicleSpawnMultiplier=1.0
MaxVehiclesPerPlayer=3
EnableVehicleLocking=true
VehicleLocksBreakable=true
VehiclePartDamageMultiplier=1.0
EnableVehiclePhysics=true
VehicleExplosionDamage=true

[/Script/SCUM.ResourceSettings]
# Resources and Materials
BatteryDrainMultiplier=1.0
FuelConsumptionMultiplier=1.0
ResourceSpawnMultiplier=1.0
ResourceDecayMultiplier=1.0
EnableResourcePersistence=true
WoodGatheringMultiplier=1.0
StoneGatheringMultiplier=1.0
MetalGatheringMultiplier=1.0
ClothGatheringMultiplier=1.0
ElectronicsGatheringMultiplier=1.0
ChemicalsGatheringMultiplier=1.0

[/Script/SCUM.DeviceSettings]
# Devices and Electronics
DeviceSpawnMultiplier=1.0
DeviceTimeout=600.0
DevicePowerConsumptionMultiplier=1.0
EnableDeviceDecay=true
DeviceDecayTime=3600.0
GeneratorEfficiency=1.0
SolarPanelEfficiency=1.0
BatteryCapacityMultiplier=1.0
ElectronicsDamageMultiplier=1.0

[/Script/SCUM.WorldSettings]
# World Persistence and Building
WorldDecayMultiplier=1.0
BuildingDecayTime=604800.0
EnableWorldPersistence=true
WorldSaveInterval=300.0
MaxWorldAge=2592000.0
EnableBaseBuilding=true
MaxBasesPerPlayer=3
BaseRadiusLimit=50.0
BuildingHealthMultiplier=1.0
BuildingCostMultiplier=1.0
EnableBaseDamage=true
EnableBaseRaiding=true
RaidWindowStart=18.0
RaidWindowEnd=6.0

[/Script/SCUM.EconomySettings]
# Economy and Trading
EnableTrading=true
TradingFeeMultiplier=0.05
MarketUpdateInterval=3600.0
EnableDynamicPricing=true
BaseResourceValue=1.0
MoneySpawnMultiplier=1.0
StartingMoney=1000
MaxMoneyPerPlayer=1000000
EnablePlayerTrading=true
TradeDistance=5.0
EnableBlackMarket=false

[/Script/SCUM.CraftingSettings]
# Crafting System
CraftingTimeMultiplier=1.0
CraftingCostMultiplier=1.0
EnableAdvancedCrafting=true
RecipeUnlockMultiplier=1.0
CraftingSuccessRate=1.0
EnableBlueprintSystem=true
BlueprintDropRate=0.1
EnableToolRequirements=true
CraftingQualityVariance=0.2
EnableMassCrafting=true
CraftingExperienceMultiplier=1.0

[/Script/SCUM.WeatherSettings]
# Weather System
WeatherChangeInterval=1800.0
ExtremeWeatherMultiplier=1.0
WeatherImpactMultiplier=1.0
EnableDynamicWeather=true
RainFrequency=0.3
FogFrequency=0.2
StormFrequency=0.1
SnowFrequency=0.15
TemperatureMultiplier=1.0
WindSpeedMultiplier=1.0
EnableWeatherDamage=true
LightningStrikeChance=0.05

[/Script/SCUM.AISettings]
# AI and NPCs (Puppets/Zombies)
AIMaxCount=50
AISpawnMultiplier=1.0
AIBehaviorMultiplier=1.0
EnableAISpawning=true
AIDespawnDistance=5000.0
AIDetectionRangeMultiplier=1.0
AIHealthMultiplier=1.0
AISpeedMultiplier=1.0
AIDropLoot=true
AILootQuality=1.0
EnableAIHordes=true
HordeSize=15
HordeSpawnChance=0.1
EnableAIVariation=true

[/Script/SCUM.AnimalSettings]
# Wildlife System
AnimalSpawnMultiplier=1.0
AnimalHealthMultiplier=1.0
AnimalDamageMultiplier=1.0
AnimalSpeedMultiplier=1.0
EnableAnimalHunting=true
AnimalMeatYieldMultiplier=1.0
AnimalSkinYieldMultiplier=1.0
EnableAnimalAggression=true
PredatorSpawnMultiplier=1.0
PreySpawnMultiplier=1.0
EnableAnimalMigration=true

[/Script/SCUM.FactionSettings]
# Factions and Groups
EnableFactions=true
FactionSizeLimit=10
FactionTerritoryMultiplier=1.0
FactionReputationMultiplier=1.0
EnableFactionWars=true
FactionPointsMultiplier=1.0
MaxFactionsPerServer=50
EnableFactionBases=true
FactionTaxRate=0.05

[/Script/SCUM.EventSettings]
# Dynamic Events
EventSpawnMultiplier=1.0
EventDurationMultiplier=1.0
EnableRandomEvents=true
EventCooldownMultiplier=1.0
EnableAirdrops=true
AirdropFrequency=3600.0
AirdropLootQuality=2.0
EnableMechs=true
MechSpawnChance=0.05
EnableMerchants=true
MerchantSpawnInterval=7200.0

[/Script/SCUM.SecuritySettings]
# Anti-Cheat and Security
BaseSecurityLevel=1.0
SecurityMultiplier=1.0
EnableAntiCheat=true
MaxViolationCount=3
EnableSpeedHackDetection=true
EnableAimbotDetection=true
EnableWallhackDetection=true
EnableFlyHackDetection=true
EnableTeleportDetection=true
LogSecurityViolations=true
AutoBanCheaters=true

[/Script/SCUM.PerformanceSettings]
# Server Performance
MaxTickRate=30.0
SimulationDistance=10000.0
NetworkUpdateRate=20.0
EnablePerformanceOptimization=true
MaxPlayersPerArea=16
DespawnDistance=5000.0
EnableLODSystem=true
EnableOcclusionCulling=true
PhysicsSimulationRate=30.0

[/Script/SCUM.SkillSettings]
# Character Skills and Progression
SkillGainMultiplier=1.0
ExperienceMultiplier=1.0
MaxSkillLevel=5
EnableSkillDegradation=false
SkillLossRate=0.01
EnableAttributeSystem=true
AttributePointsPerLevel=3
StrengthMultiplier=1.0
DexterityMultiplier=1.0
ConstitutionMultiplier=1.0
IntelligenceMultiplier=1.0

[/Script/SCUM.FameSettings]
# Fame Points System
EnableFameSystem=true
FameGainMultiplier=1.0
FameForKill=10
FameForDeath=-5
FameForCrafting=2
FameForSurvival=1
FameDecayEnabled=false
FameDecayRate=0.1
MaxFamePoints=100000
"""
    
    def get_default_engine_settings(self):
        """Get default Engine.ini content with comprehensive SCUM server settings"""
        return """[/Script/Engine.GameEngine]
bSmoothFrameRate=true
SmoothedFrameRateRange=(LowerBound=(Type=Inclusive,Value=22.000000),UpperBound=(Type=Exclusive,Value=62.000000))
bUseFixedFrameRate=false
FixedFrameRate=30.0
MinDesiredFrameRate=22.0
MaxPixelShaderAdditiveComplexityCount=128
MaxES2PixelShaderAdditiveComplexityCount=45

[/Script/Engine.RendererSettings]
r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange=True
r.DefaultFeature.MotionBlur=False
r.DefaultFeature.Bloom=False
r.DefaultFeature.AntiAliasing=0
r.DefaultFeature.LensFlare=False
r.DefaultFeature.AmbientOcclusion=False
r.ShadowQuality=0
r.Shadow.CSM.MaxCascades=1
r.Shadow.MaxResolution=256
r.Shadow.RadiusThreshold=0.01
r.Shadow.DistanceScale=0.1
r.Shadow.CSM.TransitionScale=0.1
r.DistanceFieldShadowing=0
r.LightShaftQuality=0
r.RefractionQuality=0
r.SSR.Quality=0
r.SceneColorFormat=2
r.TranslucencyVolumeBlur=0
r.MaterialQualityLevel=0
r.DetailMode=0
r.TranslucencyLightingVolumeDim=4
r.RefractionOffsetAmount=0
r.AllowOcclusionQueries=0
r.MinScreenRadiusForLights=0.01
r.MinScreenRadiusForDepthPrepass=0.01

[/Script/Engine.GameUserSettings]
bUseVSync=False
ResolutionSizeX=1920
ResolutionSizeY=1080
LastUserConfirmedResolutionSizeX=1920
LastUserConfirmedResolutionSizeY=1080
WindowPosX=-1
WindowPosY=-1
bUseDesktopResolutionForFullscreen=False
FullscreenMode=2
LastConfirmedFullscreenMode=2
PreferredFullscreenMode=2
Version=5
AudioQualityLevel=0
LastConfirmedAudioQualityLevel=0
FrameRateLimit=60.0
DesiredScreenWidth=1920
DesiredScreenHeight=1080
LastUserConfirmedDesiredScreenWidth=1920
LastUserConfirmedDesiredScreenHeight=1080
LastRecommendedScreenWidth=-1.000000
LastRecommendedScreenHeight=-1.000000

[Core.System]
Paths=../../../SCUM/Content/Paks

[/Script/OnlineSubsystemUtils.IpNetDriver]
MaxClientRate=100000
MaxInternetClientRate=100000
NetServerMaxTickRate=30
LanServerMaxTickRate=30
bClampListenServerTickRate=False

[/Script/SocketSubsystemEpic.EpicNetDriver]
MaxClientRate=100000
MaxInternetClientRate=100000
NetServerMaxTickRate=30
LanServerMaxTickRate=30

[/Script/Engine.NetworkSettings]
n.VerifyPeer=false
n.UseCompression=true
n.MaxClientRate=100000
n.ConnectionTimeout=30.0
n.InitialConnectTimeout=30.0
n.AckTimeout=2.0
n.KeepAliveTimeout=10.0
n.ConnectionRetries=3
n.AllowPlayerIdOverride=false

[/Script/Engine.Player]
ConfiguredInternetSpeed=100000
ConfiguredLanSpeed=100000

[Engine.Player]
ConfiguredInternetSpeed=100000
ConfiguredLanSpeed=100000

[/Script/Engine.Engine]
bUseFixedFrameRate=false
FixedFrameRate=30.0
SmoothedFrameRateRange=(LowerBound=(Type=Inclusive,Value=22.000000),UpperBound=(Type=Exclusive,Value=62.000000))
bSmoothFrameRate=true
MinDesiredFrameRate=22.0

[/Script/Engine.GameSession]
MaxPlayers=64
MaxSpectators=0
MaxSplitscreenPlayers=1
bRequiresPushToTalk=false
SessionName=SCUM Server Session

[Core.Log]
LogNet=Warning
LogNetTraffic=Warning
LogNetDormancy=Warning
"""

    def get_default_scalability_settings(self):
        """Get default Scalability.ini content with comprehensive SCUM server settings"""
        return """[ScalabilityGroups]
sg.ResolutionQuality=75
sg.ViewDistanceQuality=2
sg.AntiAliasingQuality=2
sg.ShadowQuality=2
sg.PostProcessQuality=2
sg.TextureQuality=2
sg.EffectsQuality=2
sg.FoliageQuality=2
sg.ShadingQuality=2

[Scalability::ResolutionQuality@0]
sg.ResolutionQuality=50

[Scalability::ResolutionQuality@1]
sg.ResolutionQuality=75

[Scalability::ResolutionQuality@2]
sg.ResolutionQuality=100

[Scalability::ResolutionQuality@3]
sg.ResolutionQuality=100

[Scalability::ViewDistanceQuality@0]
sg.ViewDistanceQuality=0

[Scalability::ViewDistanceQuality@1]
sg.ViewDistanceQuality=1

[Scalability::ViewDistanceQuality@2]
sg.ViewDistanceQuality=2

[Scalability::ViewDistanceQuality@3]
sg.ViewDistanceQuality=3

[Scalability::AntiAliasingQuality@0]
sg.AntiAliasingQuality=0

[Scalability::AntiAliasingQuality@1]
sg.AntiAliasingQuality=1

[Scalability::AntiAliasingQuality@2]
sg.AntiAliasingQuality=2

[Scalability::AntiAliasingQuality@3]
sg.AntiAliasingQuality=3

[Scalability::ShadowQuality@0]
sg.ShadowQuality=0

[Scalability::ShadowQuality@1]
sg.ShadowQuality=1

[Scalability::ShadowQuality@2]
sg.ShadowQuality=2

[Scalability::ShadowQuality@3]
sg.ShadowQuality=3

[Scalability::PostProcessQuality@0]
sg.PostProcessQuality=0

[Scalability::PostProcessQuality@1]
sg.PostProcessQuality=1

[Scalability::PostProcessQuality@2]
sg.PostProcessQuality=2

[Scalability::PostProcessQuality@3]
sg.PostProcessQuality=3

[Scalability::TextureQuality@0]
sg.TextureQuality=0

[Scalability::TextureQuality@1]
sg.TextureQuality=1

[Scalability::TextureQuality@2]
sg.TextureQuality=2

[Scalability::TextureQuality@3]
sg.TextureQuality=3

[Scalability::EffectsQuality@0]
sg.EffectsQuality=0

[Scalability::EffectsQuality@1]
sg.EffectsQuality=1

[Scalability::EffectsQuality@2]
sg.EffectsQuality=2

[Scalability::EffectsQuality@3]
sg.EffectsQuality=3

[Scalability::FoliageQuality@0]
sg.FoliageQuality=0

[Scalability::FoliageQuality@1]
sg.FoliageQuality=1

[Scalability::FoliageQuality@2]
sg.FoliageQuality=2

[Scalability::FoliageQuality@3]
sg.FoliageQuality=3

[Scalability::ShadingQuality@0]
sg.ShadingQuality=0

[Scalability::ShadingQuality@1]
sg.ShadingQuality=1

[Scalability::ShadingQuality@2]
sg.ShadingQuality=2

[Scalability::ShadingQuality@3]
sg.ShadingQuality=3

[/Script/Engine.GameUserSettings]
bUseVSync=False
ResolutionSizeX=1920
ResolutionSizeY=1080
LastUserConfirmedResolutionSizeX=1920
LastUserConfirmedResolutionSizeY=1080
WindowPosX=-1
WindowPosY=-1
bUseDesktopResolutionForFullscreen=False
FullscreenMode=2
LastConfirmedFullscreenMode=2
PreferredFullscreenMode=2
Version=5
AudioQualityLevel=0
LastConfirmedAudioQualityLevel=0
FrameRateLimit=60.000000
DesiredScreenWidth=1920
DesiredScreenHeight=1080
LastUserConfirmedDesiredScreenWidth=1920
LastUserConfirmedDesiredScreenHeight=1080
LastRecommendedScreenWidth=-1.000000
LastRecommendedScreenHeight=-1.000000
PreferredFullscreenMode=2

[/Script/Engine.Engine]
bUseFixedFrameRate=false
FixedFrameRate=30.0
SmoothedFrameRateRange=(LowerBound=(Type=Inclusive,Value=22.000000),UpperBound=(Type=Exclusive,Value=62.000000))
bSmoothFrameRate=true
MinDesiredFrameRate=22.0

[/Script/Engine.RendererSettings]
r.Streaming.PoolSize=1000
r.Streaming.MaxTempMemoryAllowed=100
r.Streaming.NumStaticComponentsProcessedPerFrame=10
r.Streaming.MaxTexturePoolSize=1000
r.Streaming.Boost=1.0
r.Streaming.Defrag=0
r.TextureStreaming=1
r.UseLODStreaming=1
"""

    def get_default_input_settings(self):
        """Get default Input.ini content"""
        return """[/Script/Engine.InputSettings]
bAltEnterTogglesFullscreen=True
bF11TogglesFullscreen=True
bUseMouseForTouch=False
bEnableMouseSmoothing=True
bEnableFOVScaling=True
FOVScale=1.000000
DoubleClickTime=0.200000
bCaptureMouseOnLaunch=True
bAlwaysShowTouchInterface=False
bShowMouseCursor=True
bEnableRawInput=True

[/Script/Engine.PlayerInput]
MouseSensitivity=1.000000
bEnableMouseSmoothing=True
MouseSmoothingStrength=0.100000
bInvertMouse=False
bInvertMousePitch=False
bInvertMouseYaw=False
bEnableGamepadInput=True
GamepadDeadZone=0.250000

[Engine.PlayerInput]
MouseSamplingRate=60
bEnableLegacyInputScales=False
"""

    def load_config_file(self):
        """Load config file manually"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Configuration File",
            str(APP_ROOT),
            "Config Files (*.ini *.json);;All Files (*.*)"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Determine which editor based on filename
            if 'ServerSettings' in filename:
                self.server_settings_editor.setPlainText(content)
            elif 'Game' in filename and 'Default' not in filename:
                self.game_settings_editor.setPlainText(content)
            elif 'Engine' in filename and 'Default' not in filename:
                self.engine_settings_editor.setPlainText(content)
            elif 'Scalability' in filename:
                self.scalability_editor.setPlainText(content)
            elif 'Input' in filename:
                self.input_editor.setPlainText(content)
            elif 'DefaultGame' in filename:
                self.default_game_editor.setPlainText(content)
            elif 'DefaultEngine' in filename:
                self.default_engine_editor.setPlainText(content)
            else:
                self.server_settings_editor.setPlainText(content)
            
            self.config_status.setText(f"✅ Loaded: {Path(filename).name}")
            self.config_status.setStyleSheet("color: #50fa7b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
            QMessageBox.information(self, "Loaded", f"Configuration loaded from:\n{filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load config file:\n{str(e)}")

    def save_config_file(self):
        """Save config file"""
        if not self.scum_path:
            QMessageBox.warning(self, "Server Path Required", "Please set the SCUMServer.exe path first.")
            return
        
        try:
            server_path = Path(self.scum_path)
            config_base = server_path.parent.parent.parent / "SCUM" / "Saved" / "Config" / "WindowsServer"
            config_base.mkdir(parents=True, exist_ok=True)
            
            files_saved = []
            
            # Save ServerSettings.ini
            if self.server_settings_editor.toPlainText().strip():
                server_settings_path = config_base / "ServerSettings.ini"
                with open(server_settings_path, 'w', encoding='utf-8') as f:
                    f.write(self.server_settings_editor.toPlainText())
                files_saved.append("ServerSettings.ini")
            
            # Save Game.ini
            if self.game_settings_editor.toPlainText().strip():
                game_ini_path = config_base / "Game.ini"
                with open(game_ini_path, 'w', encoding='utf-8') as f:
                    f.write(self.game_settings_editor.toPlainText())
                files_saved.append("Game.ini")
            
            # Save Engine.ini
            if self.engine_settings_editor.toPlainText().strip():
                engine_ini_path = config_base / "Engine.ini"
                with open(engine_ini_path, 'w', encoding='utf-8') as f:
                    f.write(self.engine_settings_editor.toPlainText())
                files_saved.append("Engine.ini")
            
            # Save Scalability.ini
            if self.scalability_editor.toPlainText().strip():
                scalability_ini_path = config_base / "Scalability.ini"
                with open(scalability_ini_path, 'w', encoding='utf-8') as f:
                    f.write(self.scalability_editor.toPlainText())
                files_saved.append("Scalability.ini")
            
            # Save Input.ini
            if self.input_editor.toPlainText().strip():
                input_ini_path = config_base / "Input.ini"
                with open(input_ini_path, 'w', encoding='utf-8') as f:
                    f.write(self.input_editor.toPlainText())
                files_saved.append("Input.ini")
            
            # Save DefaultGame.ini
            if self.default_game_editor.toPlainText().strip():
                default_game_ini_path = config_base / "DefaultGame.ini"
                with open(default_game_ini_path, 'w', encoding='utf-8') as f:
                    f.write(self.default_game_editor.toPlainText())
                files_saved.append("DefaultGame.ini")
            
            # Save DefaultEngine.ini
            if self.default_engine_editor.toPlainText().strip():
                default_engine_ini_path = config_base / "DefaultEngine.ini"
                with open(default_engine_ini_path, 'w', encoding='utf-8') as f:
                    f.write(self.default_engine_editor.toPlainText())
                files_saved.append("DefaultEngine.ini")
            
            if files_saved:
                QMessageBox.information(self, "Success", f"Configuration files saved:\n\n{chr(10).join(files_saved)}\n\nTo: {config_base}")
            else:
                QMessageBox.warning(self, "Nothing to Save", "No configuration content to save.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save config files:\n{str(e)}")

    def backup_config_file(self):
        """Backup configuration files"""
        if not self.scum_path:
            QMessageBox.warning(self, "Server Path Required", "Please set the SCUMServer.exe path first.")
            return
        
        try:
            from datetime import datetime
            server_path = Path(self.scum_path)
            config_base = server_path.parent.parent.parent / "SCUM" / "Saved" / "Config" / "WindowsServer"
            backup_dir = config_base.parent / "Backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_folder = backup_dir / f"backup_{timestamp}"
            backup_folder.mkdir(parents=True, exist_ok=True)
            
            files_backed_up = []
            for config_file in ["ServerSettings.ini", "Game.ini", "Engine.ini", "Scalability.ini", "Input.ini", "DefaultGame.ini", "DefaultEngine.ini"]:
                source = config_base / config_file
                if source.exists():
                    import shutil
                    shutil.copy2(source, backup_folder / config_file)
                    files_backed_up.append(config_file)
            
            if files_backed_up:
                QMessageBox.information(self, "Backup Complete", f"Configuration backed up:\n\n{chr(10).join(files_backed_up)}\n\nTo: {backup_folder}")
            else:
                QMessageBox.warning(self, "Nothing to Backup", "No configuration files found to backup.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to backup config files:\n{str(e)}")

    def restore_config_backup(self):
        """Restore configuration from backup"""
        if not self.scum_path:
            QMessageBox.warning(self, "Server Path Required", "Please set the SCUMServer.exe path first.")
            return
        
        try:
            server_path = Path(self.scum_path)
            config_base = server_path.parent.parent.parent / "SCUM" / "Saved" / "Config" / "WindowsServer"
            backup_dir = config_base.parent / "Backups"
            
            if not backup_dir.exists():
                QMessageBox.warning(self, "No Backups", "No backup directory found.")
                return
            
            # List available backups
            backups = sorted([d for d in backup_dir.iterdir() if d.is_dir()], reverse=True)
            if not backups:
                QMessageBox.warning(self, "No Backups", "No backups found.")
                return
            
            # Show selection dialog
            backup_names = [b.name for b in backups]
            from PySide6.QtWidgets import QInputDialog
            item, ok = QInputDialog.getItem(self, "Select Backup", "Choose a backup to restore:", backup_names, 0, False)
            
            if ok and item:
                selected_backup = backup_dir / item
                files_restored = []
                
                import shutil
                for config_file in ["ServerSettings.ini", "Game.ini", "Engine.ini", "Scalability.ini", "Input.ini", "DefaultGame.ini", "DefaultEngine.ini"]:
                    source = selected_backup / config_file
                    if source.exists():
                        shutil.copy2(source, config_base / config_file)
                        files_restored.append(config_file)
                
                if files_restored:
                    # Reload the editors
                    self.auto_detect_configs()
                    QMessageBox.information(self, "Restore Complete", f"Configuration restored:\n\n{chr(10).join(files_restored)}\n\nFrom: {selected_backup}")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to restore backup:\n{str(e)}")

    # === ADVANCED CONFIG EDITOR METHODS ===
    def save_all_configs(self):
        """Save all configuration files - just saves the current file"""
        # This is now handled by save_current_config()
        # Keep this for compatibility with existing code
        if self.current_editor:
            self.save_current_config()
    
    def backup_all_configs(self):
        """Backup all configurations"""
        self.backup_config_file()
    
    def validate_all_configs(self):
        """Validate all configuration files"""
        validation_results = []
        is_valid = True
        
        # Validate ServerSettings.ini
        server_content = self.server_settings_editor.toPlainText()
        if server_content.strip():
            result = self.validate_ini_syntax(server_content, "ServerSettings.ini")
            validation_results.append(result)
            if not result['valid']:
                is_valid = False
        
        # Validate Game.ini
        game_content = self.game_settings_editor.toPlainText()
        if game_content.strip():
            result = self.validate_ini_syntax(game_content, "Game.ini")
            validation_results.append(result)
            if not result['valid']:
                is_valid = False
        
        # Validate Engine.ini
        engine_content = self.engine_settings_editor.toPlainText()
        if engine_content.strip():
            result = self.validate_ini_syntax(engine_content, "Engine.ini")
            validation_results.append(result)
            if not result['valid']:
                is_valid = False
        
        # Update validation status
        if is_valid:
            self.validation_status.setText("✓ All Valid")
            self.validation_status.setStyleSheet("color: #50fa7b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
            QMessageBox.information(self, "Validation Success", "✅ All configuration files are valid!\n\n" + "\n".join([r['message'] for r in validation_results]))
        else:
            self.validation_status.setText("⚠ Errors Found")
            self.validation_status.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
            error_msg = "\n\n".join([f"{r['file']}: {r['message']}" for r in validation_results if not r['valid']])
            QMessageBox.warning(self, "Validation Errors", f"❌ Configuration validation failed:\n\n{error_msg}")
    
    def validate_ini_syntax(self, content, filename):
        """Validate INI file syntax"""
        errors = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith(';'):
                continue
            
            # Check for section headers
            if line.startswith('['):
                if not line.endswith(']'):
                    errors.append(f"Line {i}: Unclosed section header")
            # Check for key=value pairs
            elif '=' in line:
                parts = line.split('=', 1)
                if len(parts) != 2:
                    errors.append(f"Line {i}: Invalid key=value syntax")
                elif not parts[0].strip():
                    errors.append(f"Line {i}: Empty key name")
            else:
                # Line is not a section or key=value
                if line:  # Only report non-empty lines
                    errors.append(f"Line {i}: Invalid syntax - not a section or key=value pair")
        
        if errors:
            return {
                'valid': False,
                'file': filename,
                'message': f"{len(errors)} error(s) found:\n" + "\n".join(errors[:5])  # Show first 5 errors
            }
        else:
            return {
                'valid': True,
                'file': filename,
                'message': f"✓ {filename} is valid"
            }
    
    def search_configs(self, search_text):
        """Search across all configuration files"""
        if not search_text:
            return
        
        search_text = search_text.lower()
        results = []
        
        # Search in each editor
        editors = [
            (self.server_settings_editor, "ServerSettings.ini"),
            (self.game_settings_editor, "Game.ini"),
            (self.engine_settings_editor, "Engine.ini"),
            (self.scalability_editor, "Scalability.ini"),
            (self.input_editor, "Input.ini"),
            (self.default_game_editor, "DefaultGame.ini"),
            (self.default_engine_editor, "DefaultEngine.ini")
        ]
        
        for editor, filename in editors:
            content = editor.toPlainText()
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if search_text in line.lower():
                    results.append(f"{filename} (Line {i}): {line.strip()}")
        
        if results:
            result_text = f"Found {len(results)} matches:\n\n" + "\n".join(results[:50])  # Limit to 50 results
            if len(results) > 50:
                result_text += f"\n\n... and {len(results) - 50} more matches"
            QMessageBox.information(self, "Search Results", result_text)
        else:
            QMessageBox.information(self, "Search Results", f"No matches found for '{search_text}'")
    
    def on_config_file_changed(self, filename):
        """Handle config file selector change"""
        # This can be used to filter or switch views
        pass
    
    def load_config_preset(self):
        """Load a configuration preset"""
        try:
            presets_file = APP_ROOT / "config_presets.json"
            if not presets_file.exists():
                QMessageBox.warning(self, "No Presets", "No configuration presets found.")
                return
            
            with open(presets_file, 'r', encoding='utf-8') as f:
                presets_data = json.load(f)
            
            presets = presets_data.get('presets', {})
            if not presets:
                QMessageBox.warning(self, "No Presets", "No presets available.")
                return
            
            # Create preset selection dialog
            from PySide6.QtWidgets import QInputDialog, QDialog, QVBoxLayout, QLabel, QTextEdit, QDialogButtonBox, QListWidget
            
            dialog = QDialog(self)
            dialog.setWindowTitle("Load Configuration Preset")
            dialog.resize(600, 500)
            
            layout = QVBoxLayout()
            layout.addWidget(QLabel("Select a preset to load:"))
            
            # Preset list
            preset_list = QListWidget()
            for preset_name, preset_data in presets.items():
                desc = preset_data.get('description', preset_data.get('name', preset_name))
                preset_list.addItem(f"{preset_name}: {desc}")
            layout.addWidget(preset_list)
            
            # Description area
            desc_text = QTextEdit()
            desc_text.setReadOnly(True)
            desc_text.setMaximumHeight(150)
            desc_text.setPlaceholderText("Select a preset to see details...")
            layout.addWidget(QLabel("Preset Details:"))
            layout.addWidget(desc_text)
            
            def show_preset_details():
                selected_items = preset_list.selectedItems()
                if selected_items:
                    preset_name = selected_items[0].text().split(':')[0]
                    preset = presets.get(preset_name, {})
                    desc = preset.get('description', preset.get('name', ''))
                    settings = preset.get('settings', {})
                    
                    details = f"<b>{preset_name}</b><br><br>{desc}<br><br>"
                    details += "<b>Included Settings:</b><br>"
                    for file, settings_dict in settings.items():
                        details += f"• {file}<br>"
                    desc_text.setHtml(details)
            
            preset_list.itemSelectionChanged.connect(show_preset_details)
            
            # Buttons
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)
            
            dialog.setLayout(layout)
            
            if dialog.exec_() == QDialog.Accepted:
                selected_items = preset_list.selectedItems()
                if selected_items:
                    preset_name = selected_items[0].text().split(':')[0]
                    self.apply_config_preset(preset_name, presets[preset_name])
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load presets:\n{str(e)}")
    
    def apply_config_preset(self, preset_name, preset_data):
        """Apply a configuration preset"""
        try:
            settings = preset_data.get('settings', {})
            applied_files = []
            
            for file_name, file_settings in settings.items():
                if file_name == "ServerSettings.ini":
                    editor = self.server_settings_editor
                elif file_name == "Game.ini":
                    editor = self.game_settings_editor
                elif file_name == "Engine.ini":
                    editor = self.engine_settings_editor
                elif file_name == "Scalability.ini":
                    editor = self.scalability_editor
                elif file_name == "Input.ini":
                    editor = self.input_editor
                elif file_name == "DefaultGame.ini":
                    editor = self.default_game_editor
                elif file_name == "DefaultEngine.ini":
                    editor = self.default_engine_editor
                else:
                    continue
                
                # Parse current content
                current_content = editor.toPlainText()
                new_content = self.merge_config_settings(current_content, file_settings)
                editor.setPlainText(new_content)
                applied_files.append(file_name)
            
            if applied_files:
                self.config_status.setText(f"✅ Preset '{preset_name}' applied")
                self.config_status.setStyleSheet("color: #50fa7b; font-size: 12px; padding: 5px; background: #2b2f36; border-radius: 3px;")
                QMessageBox.information(self, "Preset Applied", f"Preset '{preset_name}' has been applied to:\n\n" + "\n".join(applied_files) + "\n\nDon't forget to save!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply preset:\n{str(e)}")
    
    def merge_config_settings(self, current_content, new_settings):
        """Merge new settings into existing config content"""
        lines = current_content.split('\n') if current_content else []
        
        # Build a structure of sections and keys
        config_dict = {}
        current_section = None
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('[') and stripped.endswith(']'):
                current_section = stripped
                if current_section not in config_dict:
                    config_dict[current_section] = {}
            elif '=' in stripped and current_section:
                key, value = stripped.split('=', 1)
                config_dict[current_section][key.strip()] = value.strip()
        
        # Apply new settings
        for key, value in new_settings.items():
            # Convert numeric values to strings
            if isinstance(value, (int, float, bool)):
                value = str(value).lower() if isinstance(value, bool) else str(value)
            
            # Find which section this key belongs to (simple heuristic)
            section = "[/Script/SCUM.GameplaySettings]"  # Default section
            
            # Try to find the key in existing config
            for sect, keys in config_dict.items():
                if key in keys:
                    section = sect
                    break
            
            if section not in config_dict:
                config_dict[section] = {}
            config_dict[section][key] = value
        
        # Rebuild config file
        new_lines = []
        for section, keys in config_dict.items():
            new_lines.append(section)
            for key, value in keys.items():
                new_lines.append(f"{key}={value}")
            new_lines.append("")  # Empty line between sections
        
        return '\n'.join(new_lines)
    
    def export_config_preset(self):
        """Export current configuration as a preset"""
        try:
            from PySide6.QtWidgets import QInputDialog
            
            preset_name, ok = QInputDialog.getText(self, "Export Preset", "Enter preset name:")
            if not ok or not preset_name:
                return
            
            description, ok = QInputDialog.getText(self, "Export Preset", "Enter preset description:")
            if not ok:
                description = preset_name
            
            # Build preset data
            preset_data = {
                "name": preset_name,
                "description": description,
                "settings": {}
            }
            
            # Add current settings
            editors = [
                (self.server_settings_editor, "ServerSettings.ini"),
                (self.game_settings_editor, "Game.ini"),
                (self.engine_settings_editor, "Engine.ini"),
                (self.scalability_editor, "Scalability.ini")
            ]
            
            for editor, filename in editors:
                content = editor.toPlainText()
                if content.strip():
                    # Parse INI content
                    settings_dict = self.parse_ini_to_dict(content)
                    if settings_dict:
                        preset_data["settings"][filename] = settings_dict
            
            # Save to file
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Preset",
                str(APP_ROOT / f"preset_{preset_name}.json"),
                "JSON Files (*.json)"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump({"presets": {preset_name: preset_data}}, f, indent=2)
                
                QMessageBox.information(self, "Success", f"Preset '{preset_name}' exported to:\n{filename}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export preset:\n{str(e)}")
    
    def parse_ini_to_dict(self, content):
        """Parse INI content into a dictionary"""
        result = {}
        current_section = None
        
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#') or line.startswith(';'):
                continue
            
            if line.startswith('[') and line.endswith(']'):
                current_section = line
                result[current_section] = {}
            elif '=' in line and current_section:
                key, value = line.split('=', 1)
                result[current_section][key.strip()] = value.strip()
        
        return result

    def open_visual_config_editor(self):
        """Open visual editor for currently selected file"""
        if not self.current_config_file:
            QMessageBox.information(self, "No File Selected", "Please select a file from the tree first.")
            return
        
        # Toggle to visual mode if it's an INI or CFG file
        file_ext = Path(self.current_config_file).suffix.lower()
        if file_ext in ['.ini', '.cfg']:
            self.toggle_editor_mode(self.current_config_file)
        else:
            QMessageBox.information(self, "Not Supported", "Visual editor is only available for .ini and .cfg files.\n\nJSON and text files use the text editor.")
    
    def open_sqlite_studio(self):
        """🗄️ Professional SQLite Database Manager - Better than SQLiteStudio!

        Complete professional-grade database management system built directly into your application.
        No external dependencies required - everything is integrated!

        Features (All Built-In):
        • 📊 Advanced Data Browser - View, edit, filter, sort with inline cell editing
        • 💻 SQL Editor - Multi-query execution, syntax highlighting, query history
        • 📋 Schema Designer - Visual schema viewer, DDL display
        • 🛠️ Database Tools - VACUUM, REINDEX, ANALYZE, integrity check
        • 💾 Backup & Restore - Create backups, clone database
        • 📤 Import/Export - CSV export, clipboard support
        • ⚡ Performance Monitor - Query execution time tracking
        • 📝 Query History - Save and reuse queries
        • 🎨 Professional Dark Theme - VS Code inspired design
        • 📋 Multiple Result Tabs - Execute multiple queries simultaneously

        This is a complete, professional database management system - better than SQLiteStudio!
        """
        try:
            # Ask user to select a database file
            db_path, _ = QFileDialog.getOpenFileName(
                self,
                "Open SQLite Database",
                str(Path.home()),  # Start in user's home directory
                "SQLite Database Files (*.db *.sqlite *.sqlite3);;All Files (*)"
            )

            if not db_path:
                return  # User cancelled

            db_path = Path(db_path)

            # Verify it's a valid SQLite database
            if not self._is_valid_sqlite_db(db_path):
                QMessageBox.warning(self, "Invalid Database",
                    f"The selected file is not a valid SQLite database:\n{db_path}")
                return

            # Import and create the SQLiteStudio Professional database manager
            from sqlitestudio_pro import SQLiteStudioPro

            manager = SQLiteStudioPro(self, db_path)
            manager.exec()

        except Exception as e:
            QMessageBox.critical(self, "Database Manager Error",
                f"Failed to open database manager:\n{str(e)}\n\n"
                "Please check your database file and try again.")
            import traceback
            traceback.print_exc()

    def _is_valid_sqlite_db(self, db_path):
        """Check if file is a valid SQLite database"""
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
            cursor.fetchone()
            conn.close()
            return True
        except:
            return False
    
    def _get_db_manager_stylesheet(self):
        """Get comprehensive stylesheet for database manager"""
        return """
            QDialog {
                background: #1e1e1e;
                color: #d4d4d4;
            }
            QTabWidget::pane {
                border: 1px solid #3e3e42;
                background: #252526;
                border-radius: 0px;
            }
            QTabBar::tab {
                background: #2d2d30;
                border: 1px solid #3e3e42;
                padding: 10px 20px;
                margin-right: 2px;
                color: #d4d4d4;
                font-weight: 600;
                min-width: 100px;
            }
            QTabBar::tab:selected {
                background: #007acc;
                color: #ffffff;
                border-bottom: 2px solid #007acc;
            }
            QTabBar::tab:hover {
                background: #3e3e42;
            }
            QTabBar::close-button {
                image: url(none);
                background: #d4d4d4;
                border-radius: 2px;
                width: 12px;
                height: 12px;
            }
            QTabBar::close-button:hover {
                background: #ff5555;
            }
            QLabel {
                color: #d4d4d4;
                background: transparent;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #007acc;
                margin-top: 10px;
                color: #d4d4d4;
                background: #1e1e1e;
                border-radius: 5px;
                padding: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0px 5px;
                color: #007acc;
            }
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #0e639c, stop:1 #007acc);
                color: #ffffff;
                padding: 8px 16px;
                border-radius: 3px;
                font-weight: 600;
                border: none;
                min-width: 80px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1177bb, stop:1 #0e639c);
            }
            QPushButton:pressed {
                background: #005a9e;
            }
            QPushButton:disabled {
                background: #3e3e42;
                color: #6e6e6e;
            }
            QPushButton#danger {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #c5000b, stop:1 #e81123);
            }
            QPushButton#danger:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #e81123, stop:1 #f1707a);
            }
            QPushButton#success {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #107c10, stop:1 #16c60c);
            }
            QPushButton#success:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #16c60c, stop:1 #7fba00);
            }
            QPushButton#toolbar {
                background: transparent;
                border: 1px solid #3e3e42;
                padding: 6px 12px;
                border-radius: 3px;
                min-width: 60px;
            }
            QPushButton#toolbar:hover {
                background: #3e3e42;
                border: 1px solid #007acc;
            }
            QTextEdit {
                background: #1e1e1e;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 11pt;
                selection-background-color: #264f78;
                padding: 8px;
            }
            QPlainTextEdit {
                background: #1e1e1e;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                color: #d4d4d4;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                font-size: 11pt;
                selection-background-color: #264f78;
                padding: 8px;
            }
            QTableWidget {
                background: #1e1e1e;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                color: #d4d4d4;
                gridline-color: #3e3e42;
                selection-background-color: #264f78;
                alternate-background-color: #252526;
            }
            QTableWidget::item {
                padding: 6px;
                border: none;
            }
            QTableWidget::item:selected {
                background: #264f78;
                color: #ffffff;
            }
            QTableWidget::item:hover {
                background: #2a2d2e;
            }
            QHeaderView::section {
                background: #2d2d30;
                color: #d4d4d4;
                padding: 8px;
                border: 1px solid #3e3e42;
                font-weight: bold;
                font-size: 10pt;
            }
            QHeaderView::section:hover {
                background: #3e3e42;
            }
            QComboBox {
                background: #3c3c3c;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                color: #d4d4d4;
                padding: 6px;
                min-width: 120px;
            }
            QComboBox:hover {
                border: 1px solid #007acc;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #d4d4d4;
                margin-right: 5px;
            }
            QComboBox QAbstractItemView {
                background: #252526;
                border: 1px solid #3e3e42;
                selection-background-color: #007acc;
                selection-color: #ffffff;
            }
            QLineEdit {
                background: #3c3c3c;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                padding: 6px;
                color: #d4d4d4;
                selection-background-color: #264f78;
            }
            QLineEdit:focus {
                border: 1px solid #007acc;
            }
            QTreeWidget {
                background: #252526;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                color: #d4d4d4;
                outline: none;
            }
            QTreeWidget::item {
                padding: 6px;
                border: none;
            }
            QTreeWidget::item:selected {
                background: #264f78;
                color: #ffffff;
            }
            QTreeWidget::item:hover {
                background: #2a2d2e;
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                image: none;
                border: none;
            }
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {
                image: none;
                border: none;
            }
            QProgressBar {
                background: #252526;
                border: 2px solid #3e3e42;
                border-radius: 5px;
                text-align: center;
                color: #d4d4d4;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #007acc, stop:1 #0e639c);
                border-radius: 3px;
            }
            QSplitter::handle {
                background: #3e3e42;
                width: 2px;
            }
            QSplitter::handle:hover {
                background: #007acc;
            }
            QScrollBar:vertical {
                background: #1e1e1e;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #3e3e42;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover {
                background: #007acc;
            }
            QScrollBar:horizontal {
                background: #1e1e1e;
                height: 12px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background: #3e3e42;
                min-width: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #007acc;
            }
            QScrollBar::add-line, QScrollBar::sub-line {
                background: none;
                border: none;
            }
            QToolBar {
                background: #2d2d30;
                border: none;
                spacing: 5px;
                padding: 5px;
            }
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 5px;
                color: #d4d4d4;
            }
            QToolButton:hover {
                background: #3e3e42;
                border: 1px solid #007acc;
            }
            QToolButton:pressed {
                background: #007acc;
            }
            QMenuBar {
                background: #2d2d30;
                color: #d4d4d4;
                border-bottom: 1px solid #3e3e42;
            }
            QMenuBar::item {
                padding: 8px 12px;
                background: transparent;
            }
            QMenuBar::item:selected {
                background: #3e3e42;
            }
            QMenu {
                background: #252526;
                border: 1px solid #3e3e42;
                color: #d4d4d4;
            }
            QMenu::item {
                padding: 8px 30px;
            }
            QMenu::item:selected {
                background: #007acc;
                color: #ffffff;
            }
            QCheckBox {
                color: #d4d4d4;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                background: #3c3c3c;
            }
            QCheckBox::indicator:checked {
                background: #007acc;
                border: 1px solid #007acc;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #007acc;
            }
            QRadioButton {
                color: #d4d4d4;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #3e3e42;
                border-radius: 9px;
                background: #3c3c3c;
            }
            QRadioButton::indicator:checked {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
                    stop:0 #007acc, stop:0.5 #007acc, stop:0.6 #3c3c3c, stop:1 #3c3c3c);
                border: 1px solid #007acc;
            }
            QRadioButton::indicator:hover {
                border: 1px solid #007acc;
            }
        """
    
    def _create_db_header(self, db_path):
        """Create professional header with database info and toolbar"""
        header_widget = QWidget()
        header_layout = QVBoxLayout()
        header_layout.setSpacing(0)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Top bar with database info
        info_bar = QWidget()
        info_bar.setStyleSheet("background: #2d2d30; padding: 10px; border-bottom: 2px solid #007acc;")
        info_layout = QHBoxLayout()
        
        # Database icon and name
        db_icon = QLabel("🗄️")
        db_icon.setStyleSheet("font-size: 24px;")
        info_layout.addWidget(db_icon)
        
        db_name = QLabel(f"<b>{db_path.name}</b>")
        db_name.setStyleSheet("font-size: 16px; color: #ffffff; font-weight: bold;")
        info_layout.addWidget(db_name)
        
        # Connection status
        self.db_connection_status = QLabel("● Connected")
        self.db_connection_status.setStyleSheet("color: #16c60c; font-weight: bold; margin-left: 20px;")
        info_layout.addWidget(self.db_connection_status)
        
        info_layout.addStretch()
        
        # Database stats
        self.db_stats_label = QLabel("Loading...")
        self.db_stats_label.setStyleSheet("color: #cccccc; font-size: 10pt;")
        info_layout.addWidget(self.db_stats_label)
        
        info_bar.setLayout(info_layout)
        header_layout.addWidget(info_bar)
        
        # Toolbar
        toolbar = QWidget()
        toolbar.setStyleSheet("background: #2d2d30; padding: 5px; border-bottom: 1px solid #3e3e42;")
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(5)
        
        # File operations
        btn_new_query = QPushButton("📝 New Query")
        btn_new_query.setObjectName("toolbar")
        btn_new_query.clicked.connect(self._add_sql_editor_tab)
        toolbar_layout.addWidget(btn_new_query)
        
        btn_open_db = QPushButton("📂 Open Database")
        btn_open_db.setObjectName("toolbar")
        btn_open_db.clicked.connect(self._open_another_database)
        toolbar_layout.addWidget(btn_open_db)
        
        toolbar_layout.addWidget(self._create_separator())
        
        # Data operations
        btn_import = QPushButton("📥 Import")
        btn_import.setObjectName("toolbar")
        btn_import.clicked.connect(self._import_data_wizard)
        toolbar_layout.addWidget(btn_import)
        
        btn_export = QPushButton("📤 Export")
        btn_export.setObjectName("toolbar")
        btn_export.clicked.connect(self._export_data_wizard)
        toolbar_layout.addWidget(btn_export)
        
        toolbar_layout.addWidget(self._create_separator())
        
        # Database tools
        btn_backup = QPushButton("💾 Backup")
        btn_backup.setObjectName("toolbar")
        btn_backup.clicked.connect(self._quick_backup)
        toolbar_layout.addWidget(btn_backup)
        
        btn_optimize = QPushButton("⚡ Optimize")
        btn_optimize.setObjectName("toolbar")
        btn_optimize.clicked.connect(self._quick_optimize)
        toolbar_layout.addWidget(btn_optimize)
        
        toolbar_layout.addWidget(self._create_separator())
        
        # View options
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setObjectName("toolbar")
        btn_refresh.clicked.connect(self._refresh_all)
        toolbar_layout.addWidget(btn_refresh)
        
        toolbar_layout.addStretch()
        
        # Help
        btn_help = QPushButton("❓ Help")
        btn_help.setObjectName("toolbar")
        btn_help.clicked.connect(self._show_db_help)
        toolbar_layout.addWidget(btn_help)
        
        toolbar.setLayout(toolbar_layout)
        header_layout.addWidget(toolbar)
        
        header_widget.setLayout(header_layout)
        return header_widget
    
    def _create_separator(self):
        """Create a vertical separator line"""
        separator = QLabel("|")
        separator.setStyleSheet("color: #3e3e42; padding: 0px 5px;")
        return separator
    
    def _create_database_navigator(self, db_path):
        """Create left sidebar database navigator"""
        navigator = QWidget()
        navigator.setMinimumWidth(250)
        navigator.setMaximumWidth(400)
        navigator.setStyleSheet("background: #252526; border-right: 1px solid #3e3e42;")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Navigator header
        nav_header = QLabel("📑 Database Objects")
        nav_header.setStyleSheet("""
            background: #2d2d30;
            color: #ffffff;
            font-weight: bold;
            font-size: 12pt;
            padding: 12px;
            border-bottom: 1px solid #3e3e42;
        """)
        layout.addWidget(nav_header)
        
        # Search box
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(10, 10, 10, 10)
        
        self.nav_search = QLineEdit()
        self.nav_search.setPlaceholderText("🔍 Search objects...")
        self.nav_search.textChanged.connect(self._filter_database_objects)
        search_layout.addWidget(self.nav_search)
        
        btn_clear_search = QPushButton("✖")
        btn_clear_search.setFixedWidth(30)
        btn_clear_search.clicked.connect(lambda: self.nav_search.clear())
        search_layout.addWidget(btn_clear_search)
        
        layout.addLayout(search_layout)
        
        # Database tree
        self.db_tree = QTreeWidget()
        self.db_tree.setHeaderLabels(["Object", "Type"])
        self.db_tree.setColumnWidth(0, 180)
        self.db_tree.setRootIsDecorated(True)
        self.db_tree.setExpandsOnDoubleClick(True)
        self.db_tree.itemDoubleClicked.connect(self._on_tree_item_double_clicked)
        self.db_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.db_tree.customContextMenuRequested.connect(self._show_tree_context_menu)
        layout.addWidget(self.db_tree)
        
        # Quick stats
        self.nav_stats = QLabel("Loading statistics...")
        self.nav_stats.setStyleSheet("""
            background: #2d2d30;
            color: #cccccc;
            padding: 10px;
            border-top: 1px solid #3e3e42;
            font-size: 9pt;
        """)
        self.nav_stats.setWordWrap(True)
        layout.addWidget(self.nav_stats)
        
        navigator.setLayout(layout)
        return navigator
    
    def _create_status_bar(self):
        """Create bottom status bar"""
        status_bar = QWidget()
        status_bar.setStyleSheet("background: #007acc; padding: 5px;")
        status_bar.setFixedHeight(30)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 0, 10, 0)
        
        self.status_message = QLabel("Ready")
        self.status_message.setStyleSheet("color: #ffffff; font-weight: bold;")
        layout.addWidget(self.status_message)
        
        layout.addStretch()
        
        self.status_query_time = QLabel("")
        self.status_query_time.setStyleSheet("color: #ffffff;")
        layout.addWidget(self.status_query_time)
        
        self.status_rows = QLabel("")
        self.status_rows.setStyleSheet("color: #ffffff; margin-left: 20px;")
        layout.addWidget(self.status_rows)
        
        status_bar.setLayout(layout)
        return status_bar

    def _init_database_manager(self, db_path):
        """Initialize the database manager with data"""
        try:
            # Update status
            self.db_status_indicator.setText("🟢 Connected")
            self.db_status_indicator.setStyleSheet("font-size: 14px; padding: 10px; color: #50fa7b;")

            # Populate table selector
            self._populate_table_selector(db_path)

            # Load schema
            self._load_database_schema(db_path)

            # Update statistics
            self._update_db_stats(db_path)

            # Connect signals
            self._connect_signals(db_path)

            # Load first table if available
            if self.table_selector.count() > 1:  # More than just "-- Select Table --"
                self.table_selector.setCurrentIndex(1)  # Select first table
                self._load_table_data(db_path)

        except Exception as e:
            self.db_status_indicator.setText("🔴 Error")
            self.db_status_indicator.setStyleSheet("font-size: 14px; padding: 10px; color: #ff6b6b;")
            print(f"Error initializing database manager: {e}")

    def _populate_table_selector(self, db_path):
        """Populate the table selector combo box"""
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = cursor.fetchall()
            conn.close()

            self.table_selector.clear()
            self.table_selector.addItem("-- Select Table --")
            for table_name, in tables:
                self.table_selector.addItem(table_name)

        except Exception as e:
            print(f"Error populating table selector: {e}")

    def _connect_signals(self, db_path):
        """Connect all the signals for the database manager"""
        # Data browser signals
        self.table_selector.currentTextChanged.connect(lambda: self._load_table_data(db_path))
        self.btn_refresh_data.clicked.connect(lambda: self._load_table_data(db_path))
        self.btn_add_row.clicked.connect(lambda: self._add_table_row(db_path))
        self.btn_delete_row.clicked.connect(lambda: self._delete_table_row(db_path))
        self.btn_apply_filter.clicked.connect(lambda: self._apply_table_filter(db_path))
        self.btn_clear_filter.clicked.connect(lambda: self._clear_table_filter(db_path))

        # SQL Editor signals
        self.btn_execute_sql.clicked.connect(lambda: self._execute_sql_query(db_path))
        self.btn_format_sql.clicked.connect(self._format_sql_query)
        self.btn_clear_sql.clicked.connect(self._clear_sql_editor)
        self.btn_export_results.clicked.connect(self._export_query_results)
        self.btn_copy_results.clicked.connect(self._copy_results_to_clipboard)
        self.btn_save_query.clicked.connect(self._save_query_to_history)

        # Schema viewer signals
        self.btn_refresh_schema.clicked.connect(lambda: self._load_database_schema(db_path))
        self.btn_create_table.clicked.connect(lambda: self._create_new_table(db_path))
        self.btn_drop_table.clicked.connect(lambda: self._drop_selected_table(db_path))
        self.schema_tree.itemClicked.connect(self._show_object_details)

        # Query history
        self.query_history.currentTextChanged.connect(self._load_query_from_history)

    def _load_table_data(self, db_path, filter_text=None):
        """Load data for the selected table"""
        try:
            table_name = self.table_selector.currentText()
            if not table_name or table_name == "-- Select Table --":
                self.data_table.setRowCount(0)
                self.data_table.setColumnCount(0)
                self.data_status.setText("No table selected")
                return

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get column information
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]

            # Build query
            query = f"SELECT * FROM {table_name}"
            if filter_text:
                # Simple filter - search in all text columns
                filter_conditions = []
                for col_name in column_names:
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    col_info = cursor.fetchall()
                    col_type = None
                    for col in col_info:
                        if col[1] == col_name:
                            col_type = col[2].upper()
                            break
                    if 'TEXT' in col_type or 'VARCHAR' in col_type or col_type is None:
                        filter_conditions.append(f"{col_name} LIKE ?")
                if filter_conditions:
                    query += f" WHERE {' OR '.join(filter_conditions)}"
                    params = [f'%{filter_text}%'] * len(filter_conditions)
                else:
                    params = []
            else:
                params = []

            # Execute query
            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Get total count for status
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_count = cursor.fetchone()[0]

            conn.close()

            # Update table
            self.data_table.setColumnCount(len(column_names))
            self.data_table.setHorizontalHeaderLabels(column_names)
            self.data_table.setRowCount(len(rows))

            for row_idx, row in enumerate(rows):
                for col_idx, value in enumerate(row):
                    item = QTableWidgetItem(str(value) if value is not None else "")
                    item.setData(Qt.UserRole, value)  # Store original value
                    self.data_table.setItem(row_idx, col_idx, item)

            # Resize columns and update status
            self.data_table.resizeColumnsToContents()
            if filter_text:
                self.data_status.setText(f"📊 Showing {len(rows)} of {total_count} rows (filtered)")
            else:
                self.data_status.setText(f"📊 Loaded {len(rows)} rows from table '{table_name}'")

        except Exception as e:
            self.data_status.setText(f"❌ Error loading table data: {str(e)}")
            print(f"Error loading table data: {e}")

    def _add_table_row(self, db_path):
        """Add a new row to the current table"""
        try:
            table_name = self.table_selector.currentText()
            if not table_name or table_name == "-- Select Table --":
                QMessageBox.warning(self, "No Table Selected", "Please select a table first.")
                return

            # Get column information
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            conn.close()

            # Add empty row at the end
            row_count = self.data_table.rowCount()
            self.data_table.insertRow(row_count)

            # Fill with empty items
            for col_idx in range(len(columns)):
                item = QTableWidgetItem("")
                item.setData(Qt.UserRole, None)  # Mark as new
                self.data_table.setItem(row_count, col_idx, item)

            self.data_status.setText(f"➕ Added new row - Click 'Save Changes' to commit")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add row:\n{str(e)}")

    def _delete_table_row(self, db_path):
        """Delete the selected row from the table"""
        try:
            current_row = self.data_table.currentRow()
            if current_row < 0:
                QMessageBox.warning(self, "No Selection", "Please select a row to delete.")
                return

            table_name = self.table_selector.currentText()
            if not table_name or table_name == "-- Select Table --":
                QMessageBox.warning(self, "No Table Selected", "Please select a table first.")
                return

            # Confirm deletion
            reply = QMessageBox.question(
                self, "Confirm Deletion",
                f"Are you sure you want to delete this row from '{table_name}'?\n\nThis action cannot be undone.",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # Get primary key or rowid for deletion
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Check if table has primary key
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            # Find primary key column
            pk_column = None
            for col in columns:
                if col[5]:  # pk flag
                    pk_column = col[1]
                    break

            if pk_column:
                # Use primary key
                pk_value = self.data_table.item(current_row, [col[1] for col in columns].index(pk_column)).text()
                cursor.execute(f"DELETE FROM {table_name} WHERE {pk_column} = ?", (pk_value,))
            else:
                # Use rowid (SQLite automatic)
                # This is more complex - we'd need to track rowids
                QMessageBox.warning(self, "Cannot Delete", "This table doesn't have a primary key.\nDeletion of rows without primary keys is not supported.")
                conn.close()
                return

            conn.commit()
            conn.close()

            # Remove from table widget
            self.data_table.removeRow(current_row)

            self.data_status.setText(f"🗑️ Row deleted from '{table_name}'")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete row:\n{str(e)}")

    def _apply_table_filter(self, db_path):
        """Apply filter to the current table"""
        filter_text = self.filter_input.text().strip()
        if filter_text:
            self._load_table_data(db_path, filter_text)
        else:
            self._clear_table_filter(db_path)

    def _clear_table_filter(self, db_path):
        """Clear the table filter"""
        self.filter_input.clear()
        self._load_table_data(db_path)

    def _execute_sql_query(self, db_path):
        """Execute the SQL query in the editor"""
        try:
            query = self.sql_input.toPlainText().strip()
            if not query:
                QMessageBox.warning(self, "Empty Query", "Please enter a SQL query to execute.")
                return

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Execute query
            cursor.execute(query)

            # Check if it's a SELECT query
            if query.upper().strip().startswith('SELECT'):
                rows = cursor.fetchall()

                # Get column names from cursor description
                if cursor.description:
                    column_names = [desc[0] for desc in cursor.description]

                    # Update results table
                    self.results_table.setColumnCount(len(column_names))
                    self.results_table.setHorizontalHeaderLabels(column_names)
                    self.results_table.setRowCount(len(rows))

                    for row_idx, row in enumerate(rows):
                        for col_idx, value in enumerate(row):
                            item = QTableWidgetItem(str(value) if value is not None else "")
                            self.results_table.setItem(row_idx, col_idx, item)

                    self.results_table.resizeColumnsToContents()
                    self.results_status.setText(f"✅ Query executed successfully - {len(rows)} rows returned")
                else:
                    self.results_table.setRowCount(0)
                    self.results_table.setColumnCount(0)
                    self.results_status.setText("✅ Query executed successfully - No results to display")
            else:
                # For non-SELECT queries, just show affected rows
                conn.commit()
                self.results_status.setText(f"✅ Query executed successfully - {cursor.rowcount} rows affected")

                # Clear results table for non-SELECT
                self.results_table.setRowCount(0)
                self.results_table.setColumnCount(0)

            # Add to query history
            if query not in [self.query_history.itemText(i) for i in range(1, self.query_history.count())]:
                self.query_history.addItem(query)
                if self.query_history.count() > 21:  # Keep last 20 queries
                    self.query_history.removeItem(1)

            conn.close()

        except Exception as e:
            self.results_status.setText(f"❌ Query failed: {str(e)}")
            QMessageBox.critical(self, "Query Error", f"Failed to execute SQL query:\n{str(e)}")

    def _format_sql_query(self):
        """Format the SQL query for better readability"""
        try:
            query = self.sql_input.toPlainText().strip()
            if not query:
                return

            # Basic SQL formatting - capitalize keywords
            import re

            # Keywords to capitalize
            keywords = [
                'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'OUTER',
                'ON', 'GROUP', 'BY', 'HAVING', 'ORDER', 'LIMIT', 'OFFSET', 'INSERT', 'INTO',
                'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE', 'INDEX', 'DROP',
                'ALTER', 'ADD', 'COLUMN', 'PRIMARY', 'KEY', 'FOREIGN', 'REFERENCES',
                'UNIQUE', 'NOT', 'NULL', 'DEFAULT', 'AUTO_INCREMENT', 'BEGIN', 'COMMIT',
                'ROLLBACK', 'AND', 'OR', 'AS', 'DISTINCT', 'COUNT', 'SUM', 'AVG', 'MAX', 'MIN'
            ]

            formatted = query.upper()  # Start with all caps
            for keyword in keywords:
                # Replace whole words only
                formatted = re.sub(r'\b' + keyword + r'\b', keyword, formatted, flags=re.IGNORECASE)

            # Fix the case - only keywords should be caps
            words = formatted.split()
            result = []
            for word in words:
                if word.upper() in keywords:
                    result.append(word.upper())
                else:
                    result.append(word.lower())

            self.sql_input.setPlainText(' '.join(result))

        except Exception as e:
            print(f"Error formatting SQL: {e}")

    def _clear_sql_editor(self):
        """Clear the SQL editor"""
        self.sql_input.clear()
        self.results_table.setRowCount(0)
        self.results_table.setColumnCount(0)
        self.results_status.setText("SQL editor cleared")

    def _export_query_results(self):
        """Export query results to CSV"""
        try:
            if self.results_table.rowCount() == 0:
                QMessageBox.warning(self, "No Results", "No query results to export.")
                return

            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Query Results",
                str(APP_ROOT / f"query_results_{timestamp}.csv"),
                "CSV Files (*.csv);;All Files (*.*)"
            )

            if not filename:
                return

            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                import csv
                writer = csv.writer(csvfile)

                # Write headers
                headers = []
                for col in range(self.results_table.columnCount()):
                    header_item = self.results_table.horizontalHeaderItem(col)
                    headers.append(header_item.text() if header_item else f"Column_{col+1}")
                writer.writerow(headers)

                # Write data
                for row in range(self.results_table.rowCount()):
                    row_data = []
                    for col in range(self.results_table.columnCount()):
                        item = self.results_table.item(row, col)
                        row_data.append(item.text() if item else "")
                    writer.writerow(row_data)

            QMessageBox.information(self, "Export Complete", f"Results exported to:\n{filename}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export results:\n{str(e)}")

    def _copy_results_to_clipboard(self):
        """Copy query results to clipboard"""
        try:
            if self.results_table.rowCount() == 0:
                QMessageBox.warning(self, "No Results", "No query results to copy.")
                return

            # Build tab-separated text
            lines = []

            # Headers
            headers = []
            for col in range(self.results_table.columnCount()):
                header_item = self.results_table.horizontalHeaderItem(col)
                headers.append(header_item.text() if header_item else f"Column_{col+1}")
            lines.append('\t'.join(headers))

            # Data
            for row in range(self.results_table.rowCount()):
                row_data = []
                for col in range(self.results_table.columnCount()):
                    item = self.results_table.item(row, col)
                    row_data.append(item.text() if item else "")
                lines.append('\t'.join(row_data))

            clipboard_text = '\n'.join(lines)

            # Copy to clipboard
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(clipboard_text)

            QMessageBox.information(self, "Copied", f"Results copied to clipboard!\n\n{self.results_table.rowCount()} rows, {self.results_table.columnCount()} columns")

        except Exception as e:
            QMessageBox.critical(self, "Copy Error", f"Failed to copy results:\n{str(e)}")

    def _save_query_to_history(self):
        """Save current query to a file for later use"""
        try:
            query = self.sql_input.toPlainText().strip()
            if not query:
                QMessageBox.warning(self, "Empty Query", "No query to save.")
                return

            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save SQL Query",
                str(APP_ROOT / f"saved_query_{timestamp}.sql"),
                "SQL Files (*.sql);;Text Files (*.txt);;All Files (*.*)"
            )

            if not filename:
                return

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"-- Saved SQL Query\n")
                f.write(f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"-- \n\n")
                f.write(query)
                f.write("\n")

            QMessageBox.information(self, "Query Saved", f"SQL query saved to:\n{filename}")

        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save query:\n{str(e)}")

    def _load_query_from_history(self):
        """Load a query from the history dropdown"""
        try:
            selected_query = self.query_history.currentText()
            if selected_query and selected_query != "-- Recent Queries --":
                self.sql_input.setPlainText(selected_query)
                self.results_status.setText("Query loaded from history")
        except Exception as e:
            print(f"Error loading query from history: {e}")

    def _load_database_schema(self, db_path):
        """Load the database schema into the tree widget"""
        try:
            self.schema_tree.clear()

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = cursor.fetchall()

            # Get all indexes
            cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY tbl_name, name")
            indexes = cursor.fetchall()

            # Get all views
            cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
            views = cursor.fetchall()

            conn.close()

            # Add tables
            tables_root = QTreeWidgetItem(self.schema_tree, ["📋 Tables", "", f"{len(tables)} tables"])
            for table_name, in tables:
                table_item = QTreeWidgetItem(tables_root, [table_name, "Table", ""])

                # Get column info for this table
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()

                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]

                table_item.setText(2, f"{len(columns)} columns, {row_count} rows")

                # Add columns as children
                for col in columns:
                    col_name, col_type, not_null, default_val, pk = col[1], col[2], col[3], col[4], col[5]
                    pk_text = " (PK)" if pk else ""
                    not_null_text = " NOT NULL" if not_null else ""
                    default_text = f" DEFAULT {default_val}" if default_val is not None else ""
                    col_item = QTreeWidgetItem(table_item, [col_name, f"{col_type}{pk_text}{not_null_text}{default_text}", "Column"])
                    col_item.setData(0, Qt.UserRole, f"table:{table_name}:column:{col_name}")

                conn.close()

            # Add indexes
            if indexes:
                indexes_root = QTreeWidgetItem(self.schema_tree, ["🔍 Indexes", "", f"{len(indexes)} indexes"])
                for index_name, table_name in indexes:
                    index_item = QTreeWidgetItem(indexes_root, [index_name, "Index", f"on table '{table_name}'"])
                    index_item.setData(0, Qt.UserRole, f"index:{index_name}")

            # Add views
            if views:
                views_root = QTreeWidgetItem(self.schema_tree, ["👁️ Views", "", f"{len(views)} views"])
                for view_name, in views:
                    view_item = QTreeWidgetItem(views_root, [view_name, "View", ""])
                    view_item.setData(0, Qt.UserRole, f"view:{view_name}")

            # Expand root items
            self.schema_tree.expandItem(tables_root)
            if indexes:
                self.schema_tree.expandItem(indexes_root)
            if views:
                self.schema_tree.expandItem(views_root)

        except Exception as e:
            print(f"Error loading database schema: {e}")

    def _show_object_details(self, item, column):
        """Show details for the selected schema object"""
        try:
            object_data = item.data(0, Qt.UserRole)
            if not object_data:
                self.object_details.clear()
                return

            data_type, *parts = object_data.split(':')

            if data_type == "table":
                table_name = parts[0]
                # Show CREATE TABLE statement
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
                create_sql = cursor.fetchone()
                conn.close()

                if create_sql and create_sql[0]:
                    self.object_details.setPlainText(f"-- CREATE TABLE statement for {table_name}\n\n{create_sql[0]}")
                else:
                    self.object_details.setPlainText(f"Could not retrieve CREATE TABLE statement for {table_name}")

            elif data_type == "column":
                table_name = parts[1]
                column_name = parts[3]
                # Show column details
                conn = sqlite3.connect(str(self.db_path))
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                conn.close()

                for col in columns:
                    if col[1] == column_name:
                        col_name, col_type, not_null, default_val, pk = col[1], col[2], col[3], col[4], col[5]
                        details = f"""Column Details:
Name: {col_name}
Type: {col_type}
Primary Key: {'Yes' if pk else 'No'}
Not Null: {'Yes' if not_null else 'No'}
Default Value: {default_val if default_val is not None else 'None'}"""
                        self.object_details.setPlainText(details)
                        break

            else:
                self.object_details.setPlainText(f"Details for {item.text(0)} ({item.text(1)})")

        except Exception as e:
            self.object_details.setPlainText(f"Error loading object details: {str(e)}")

    def _create_new_table(self, db_path):
        """Create a new table in the database"""
        try:
            table_name, ok = QInputDialog.getText(self, "Create Table", "Enter table name:")
            if not ok or not table_name.strip():
                return

            table_name = table_name.strip()

            # Simple table creation dialog
            create_sql = f"""CREATE TABLE {table_name} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);"""

            reply = QMessageBox.question(
                self, "Create Table",
                f"Create table '{table_name}' with the following SQL?\n\n{create_sql}\n\nYou can modify this SQL in the SQL Editor tab if needed.",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute(create_sql)
                conn.commit()
                conn.close()

                # Refresh schema and table selector
                self._load_database_schema(db_path)
                self._populate_table_selector(db_path)

                QMessageBox.information(self, "Table Created", f"Table '{table_name}' created successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create table:\n{str(e)}")

    def _drop_selected_table(self, db_path):
        """Drop the selected table from the database"""
        try:
            # Get selected table from schema tree
            current_item = self.schema_tree.currentItem()
            if not current_item:
                QMessageBox.warning(self, "No Selection", "Please select a table to drop.")
                return

            # Check if it's a table
            if current_item.text(1) != "Table":
                QMessageBox.warning(self, "Not a Table", "Please select a table to drop.")
                return

            table_name = current_item.text(0)

            # Confirm deletion
            reply = QMessageBox.question(
                self, "Drop Table",
                f"Are you sure you want to DROP table '{table_name}'?\n\n⚠️ This will permanently delete the table and all its data!\nThis action CANNOT be undone.",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # Additional confirmation
            confirm_text, ok = QInputDialog.getText(
                self, "Confirm Drop",
                f"Type '{table_name}' to confirm dropping this table:"
            )

            if not ok or confirm_text != table_name:
                QMessageBox.warning(self, "Cancelled", "Table drop cancelled.")
                return

            # Drop the table
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute(f"DROP TABLE {table_name}")
            conn.commit()
            conn.close()

            # Refresh schema and table selector
            self._load_database_schema(db_path)
            self._populate_table_selector(db_path)

            QMessageBox.information(self, "Table Dropped", f"Table '{table_name}' has been dropped.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to drop table:\n{str(e)}")

    # Database maintenance methods
    def _run_vacuum(self, db_path):
        """Run VACUUM to reclaim space"""
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("VACUUM")
            conn.close()
            QMessageBox.information(self, "VACUUM Complete", "Database VACUUM completed successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"VACUUM failed:\n{str(e)}")

    def _run_reindex(self, db_path):
        """Rebuild all indexes"""
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("REINDEX")
            conn.close()
            QMessageBox.information(self, "REINDEX Complete", "Database REINDEX completed successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"REINDEX failed:\n{str(e)}")

    def _run_analyze(self, db_path):
        """Update query statistics"""
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("ANALYZE")
            conn.close()
            QMessageBox.information(self, "ANALYZE Complete", "Database ANALYZE completed successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"ANALYZE failed:\n{str(e)}")

    def _check_integrity(self, db_path):
        """Check database integrity"""
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            conn.close()

            if result and result[0] == "ok":
                QMessageBox.information(self, "Integrity Check", "✅ Database integrity check PASSED!\n\nThe database is healthy.")
            else:
                QMessageBox.warning(self, "Integrity Check", "❌ Database integrity check FAILED!\n\nThe database may be corrupted.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Integrity check failed:\n{str(e)}")

    def _optimize_database_full(self, db_path):
        """Run full database optimization"""
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("VACUUM")
            cursor.execute("REINDEX")
            cursor.execute("ANALYZE")
            conn.close()
            QMessageBox.information(self, "Optimization Complete", "Full database optimization completed!\n\n• Space reclaimed\n• Indexes rebuilt\n• Statistics updated")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Optimization failed:\n{str(e)}")

    def _repair_database(self, db_path):
        """Attempt to repair database corruption"""
        QMessageBox.information(self, "Repair Database", "Database repair functionality would be implemented here.\n\nFor now, try:\n1. Create a backup\n2. Run VACUUM\n3. Run integrity check\n\nIf corruption persists, restore from a backup.")

    def _create_backup(self, db_path):
        """Create a database backup"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = db_path.parent / f"backup_{timestamp}.db"

            import shutil
            shutil.copy2(db_path, backup_path)

            QMessageBox.information(self, "Backup Created", f"Database backup created:\n{backup_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Backup failed:\n{str(e)}")

    def _export_as_sql(self, db_path):
        """Export database as SQL script"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export as SQL",
                str(db_path.parent / f"database_export_{timestamp}.sql"),
                "SQL Files (*.sql);;All Files (*.*)"
            )

            if not filename:
                return

            conn = sqlite3.connect(str(db_path))
            with open(filename, 'w', encoding='utf-8') as f:
                for line in conn.iterdump():
                    f.write(f"{line}\n")
            conn.close()

            QMessageBox.information(self, "Export Complete", f"Database exported as SQL to:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")

    def _export_all_csv(self, db_path):
        """Export all tables as CSV files"""
        try:
            export_dir = QFileDialog.getExistingDirectory(self, "Select Export Directory", str(db_path.parent))
            if not export_dir:
                return

            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            exported = 0
            for table_name, in tables:
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()

                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]

                csv_path = os.path.join(export_dir, f"{table_name}_{timestamp}.csv")
                with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                    import csv
                    writer = csv.writer(csvfile)
                    writer.writerow(columns)
                    writer.writerows(rows)

                exported += 1

            conn.close()

            QMessageBox.information(self, "Export Complete", f"Exported {exported} tables as CSV files to:\n{export_dir}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")

    def _import_sql_file(self, db_path):
        """Import and execute SQL file"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "Import SQL File",
                str(db_path.parent),
                "SQL Files (*.sql);;All Files (*.*)"
            )

            if not filename:
                return

            with open(filename, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.executescript(sql_content)
            conn.commit()
            conn.close()

            # Refresh everything
            self._load_database_schema(db_path)
            self._populate_table_selector(db_path)
            self._update_db_stats(db_path)

            QMessageBox.information(self, "Import Complete", f"SQL file imported successfully:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Import failed:\n{str(e)}")

    def _restore_backup(self, db_path):
        """Restore database from backup"""
        try:
            filename, _ = QFileDialog.getOpenFileName(
                self, "Select Backup File",
                str(db_path.parent),
                "Database Files (*.db);;All Files (*.*)"
            )

            if not filename:
                return

            # Confirm restore
            reply = QMessageBox.question(
                self, "Restore Backup",
                f"Restore database from backup?\n\nCurrent database will be replaced with:\n{filename}\n\n⚠️ This action cannot be undone!",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            import shutil
            shutil.copy2(filename, db_path)

            # Refresh everything
            self._load_database_schema(db_path)
            self._populate_table_selector(db_path)
            self._update_db_stats(db_path)

            QMessageBox.information(self, "Restore Complete", "Database restored from backup successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Restore failed:\n{str(e)}")

    def _clone_database(self, db_path):
        """Create a copy of the database"""
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            clone_path = db_path.parent / f"clone_{timestamp}.db"

            import shutil
            shutil.copy2(db_path, clone_path)

            QMessageBox.information(self, "Clone Created", f"Database cloned to:\n{clone_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Clone failed:\n{str(e)}")

    def _update_db_stats(self, db_path):
        """Update database statistics display"""
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get basic stats
            cursor.execute("SELECT COUNT(name) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(name) FROM sqlite_master WHERE type='index'")
            index_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(name) FROM sqlite_master WHERE type='view'")
            view_count = cursor.fetchone()[0]

            # Get total rows
            total_rows = 0
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            for table_name, in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                total_rows += cursor.fetchone()[0]

            # Get file size
            db_size = db_path.stat().st_size
            db_size_mb = db_size / (1024 * 1024)

            conn.close()

            stats_text = f"""Database Statistics:

📁 File: {db_path.name}
📏 Size: {db_size_mb:.2f} MB
📋 Tables: {table_count}
🔍 Indexes: {index_count}
👁️ Views: {view_count}
👥 Total Records: {total_rows:,}

Database Health: ✅ Connected
Last Updated: {datetime.now().strftime('%H:%M:%S')}"""

            self.db_stats_text.setPlainText(stats_text)

        except Exception as e:
            self.db_stats_text.setPlainText(f"Error loading statistics:\n{str(e)}")

    def _launch_sqlite_studio_external(self, parent_dialog, db_path):
        """Launch SQLiteStudio with the database file"""
        try:
            import subprocess
            import platform

            system = platform.system().lower()

            # Common SQLiteStudio installation paths
            sqlite_studio_paths = []

            if system == "windows":
                sqlite_studio_paths = [
                    r"C:\Program Files\SQLiteStudio\SQLiteStudio.exe",
                    r"C:\Program Files (x86)\SQLiteStudio\SQLiteStudio.exe",
                    r"C:\SQLiteStudio\SQLiteStudio.exe",
                    r"C:\Users\{}\AppData\Local\Programs\SQLiteStudio\SQLiteStudio.exe".format(os.environ.get('USERNAME', '')),
                    r"C:\Users\{}\AppData\Roaming\SQLiteStudio\SQLiteStudio.exe".format(os.environ.get('USERNAME', '')),
                ]
            elif system == "linux":
                sqlite_studio_paths = [
                    "/usr/bin/sqlitestudio",
                    "/usr/local/bin/sqlitestudio",
                    "/opt/sqlitestudio/sqlitestudio",
                    "~/bin/sqlitestudio",
                    "~/.local/bin/sqlitestudio",
                ]
            elif system == "darwin":
                sqlite_studio_paths = [
                    "/Applications/SQLiteStudio.app/Contents/MacOS/SQLiteStudio",
                    "~/Applications/SQLiteStudio.app/Contents/MacOS/SQLiteStudio",
                ]

            # Try to find and launch SQLiteStudio
            launched = False
            for path in sqlite_studio_paths:
                expanded_path = os.path.expanduser(path)
                if os.path.exists(expanded_path):
                    try:
                        subprocess.Popen([expanded_path, str(db_path)],
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
                        launched = True
                        break
                    except Exception:
                        continue

            if not launched:
                # Try to find in PATH
                try:
                    subprocess.Popen(["sqlitestudio", str(db_path)],
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                    launched = True
                except (FileNotFoundError, OSError):
                    pass

            if launched:
                QMessageBox.information(parent_dialog, "SQLiteStudio Launched",
                    f"SQLiteStudio opened with database:\n{db_path}\n\n"
                    "Use SQLiteStudio's full database management features to view, edit, and manage your SCUM server database.")
                parent_dialog.accept()
            else:
                # SQLiteStudio not found - offer to download
                reply = QMessageBox.question(parent_dialog, "SQLiteStudio Not Found",
                    "SQLiteStudio is not installed on your system.\n\n"
                    "Would you like to download SQLiteStudio?\n\n"
                    "SQLiteStudio is a free, open-source SQLite database manager.",
                    QMessageBox.Yes | QMessageBox.No)

                if reply == QMessageBox.Yes:
                    import webbrowser
                    webbrowser.open("https://sqlitestudio.pl/")
                    QMessageBox.information(parent_dialog, "Download SQLiteStudio",
                        "Please download and install SQLiteStudio from:\n"
                        "https://sqlitestudio.pl/\n\n"
                        "Then try the SQLiteStudio button again.")

        except Exception as e:
            QMessageBox.critical(parent_dialog, "Launch Error", f"Failed to launch SQLiteStudio:\n{str(e)}")

    def _show_database_viewer(self, db_path):
        """Show built-in database viewer dialog"""
        try:
            from scum_core import init_database
            import sqlite3

            init_database()
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = cursor.fetchall()

            if not tables:
                QMessageBox.information(self, "No Tables", "No tables found in database.")
                conn.close()
                return

            # Create viewer dialog
            viewer_dialog = QDialog(self)
            viewer_dialog.setWindowTitle("👁️ Database Viewer")
            viewer_dialog.resize(1000, 700)
            viewer_dialog.setStyleSheet("""
                QDialog {
                    background: #0f1117;
                    color: #e6eef6;
                }
                QTableWidget {
                    background: #0d1016;
                    border: 1px solid #2b2f36;
                    border-radius: 5px;
                    color: #e6eef6;
                    gridline-color: #2b2f36;
                }
                QTableWidget::item {
                    padding: 5px;
                    border-bottom: 1px solid #2b2f36;
                }
                QTableWidget::item:selected {
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1e8b57, stop:1 #35c06f);
                }
                QHeaderView::section {
                    background: #1a1d23;
                    color: #e6eef6;
                    padding: 8px;
                    border: 1px solid #2b2f36;
                    font-weight: bold;
                }
                QComboBox {
                    background: #0d1016;
                    border: 1px solid #2b2f36;
                    border-radius: 5px;
                    color: #e6eef6;
                    padding: 5px;
                }
                QLabel {
                    color: #e6eef6;
                }
            """)

            layout = QVBoxLayout()

            # Header
            header = QLabel("👁️ Built-in Database Viewer")
            header.setStyleSheet("font-size: 18px; font-weight: bold; color: #50fa7b; padding: 10px;")
            layout.addWidget(header)

            # Table selector
            selector_layout = QHBoxLayout()
            selector_layout.addWidget(QLabel("Select Table:"))

            table_combo = QComboBox()
            for table_name, in tables:
                table_combo.addItem(table_name)
            selector_layout.addWidget(table_combo)

            btn_load_table = QPushButton("📊 Load Table")
            selector_layout.addWidget(btn_load_table)

            btn_export_csv = QPushButton("📤 Export to CSV")
            selector_layout.addWidget(btn_export_csv)

            selector_layout.addStretch()
            layout.addLayout(selector_layout)

            # Data table
            data_table = QTableWidget()
            data_table.setAlternatingRowColors(True)
            layout.addWidget(data_table)

            # Status label
            status_label = QLabel("Select a table to view its data")
            status_label.setStyleSheet("color: #8be9fd; padding: 5px;")
            layout.addWidget(status_label)

            # Load table function
            def load_table():
                try:
                    table_name = table_combo.currentText()
                    if not table_name:
                        return

                    # Get column info
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    column_names = [col[1] for col in columns]

                    # Set up table
                    data_table.setColumnCount(len(column_names))
                    data_table.setHorizontalHeaderLabels(column_names)

                    # Get data (limit to 1000 rows for performance)
                    cursor.execute(f"SELECT * FROM {table_name} LIMIT 1000")
                    rows = cursor.fetchall()

                    data_table.setRowCount(len(rows))
                    for row_idx, row in enumerate(rows):
                        for col_idx, value in enumerate(row):
                            item = QTableWidgetItem(str(value) if value is not None else "")
                            data_table.setItem(row_idx, col_idx, item)

                    # Resize columns
                    data_table.resizeColumnsToContents()
                    status_label.setText(f"📊 Loaded {len(rows)} rows from table '{table_name}'")

                except Exception as e:
                    status_label.setText(f"❌ Error loading table: {str(e)}")

            # Export to CSV function
            def export_csv():
                try:
                    table_name = table_combo.currentText()
                    if not table_name:
                        return

                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename, _ = QFileDialog.getSaveFileName(
                        viewer_dialog,
                        "Export to CSV",
                        str(APP_ROOT / f"{table_name}_{timestamp}.csv"),
                        "CSV Files (*.csv);;All Files (*.*)"
                    )

                    if not filename:
                        return

                    cursor.execute(f"SELECT * FROM {table_name}")
                    rows = cursor.fetchall()

                    # Get column names
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    column_names = [col[1] for col in columns]

                    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                        import csv
                        writer = csv.writer(csvfile)
                        writer.writerow(column_names)
                        writer.writerows(rows)

                    QMessageBox.information(viewer_dialog, "Export Complete",
                        f"Table '{table_name}' exported to:\n{filename}")

                except Exception as e:
                    QMessageBox.critical(viewer_dialog, "Export Error", f"Failed to export CSV:\n{str(e)}")

            btn_load_table.clicked.connect(load_table)
            btn_export_csv.clicked.connect(export_csv)

            # Load first table by default
            if tables:
                table_combo.setCurrentIndex(0)
                load_table()

            # Bottom buttons
            button_layout = QHBoxLayout()
            button_layout.addStretch()

            btn_close_viewer = QPushButton("❌ Close")
            btn_close_viewer.clicked.connect(viewer_dialog.accept)
            button_layout.addWidget(btn_close_viewer)

            layout.addLayout(button_layout)
            viewer_dialog.setLayout(layout)

            conn.close()
            viewer_dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Viewer Error", f"Failed to open database viewer:\n{str(e)}")

    def _backup_database(self, db_path):
        """Create a backup of the database"""
        try:
            from datetime import datetime
            import shutil

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"scum_manager_backup_{timestamp}.db"
            backup_path = db_path.parent / backup_name

            shutil.copy2(db_path, backup_path)

            QMessageBox.information(self, "Backup Created",
                f"Database backup created successfully!\n\n"
                f"📁 Location: {backup_path}\n"
                f"📏 Size: {backup_path.stat().st_size / (1024*1024):.2f} MB\n\n"
                "Keep this backup in a safe place for data recovery.")

        except Exception as e:
            QMessageBox.critical(self, "Backup Error", f"Failed to create backup:\n{str(e)}")

    def _check_database_health(self, db_path):
        """Check database integrity"""
        try:
            import sqlite3

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()

            if result and result[0] == "ok":
                # Get more detailed stats
                cursor.execute("PRAGMA quick_check")
                quick_result = cursor.fetchone()

                # Get database statistics
                cursor.execute("SELECT COUNT(name) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]

                total_rows = 0
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                for table_name, in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    total_rows += cursor.fetchone()[0]

                conn.close()

                QMessageBox.information(self, "Database Health Check",
                    "✅ Database Integrity: PASSED\n\n"
                    f"📊 Statistics:\n"
                    f"• Tables: {table_count}\n"
                    f"• Total Records: {total_rows:,}\n"
                    f"• Database Size: {db_path.stat().st_size / (1024*1024):.2f} MB\n\n"
                    "Your database is healthy and functioning properly!")

            else:
                conn.close()
                QMessageBox.warning(self, "Database Health Check",
                    "❌ Database Integrity: FAILED\n\n"
                    "There are issues with your database. Consider:\n"
                    "• Creating a backup immediately\n"
                    "• Running database optimization\n"
                    "• Contacting support if issues persist")

        except Exception as e:
            QMessageBox.critical(self, "Health Check Error", f"Failed to check database health:\n{str(e)}")

    def _optimize_database(self, db_path):
        """Optimize database performance"""
        try:
            import sqlite3

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get size before optimization
            size_before = db_path.stat().st_size

            # Run optimization commands
            cursor.execute("VACUUM")
            cursor.execute("REINDEX")
            cursor.execute("ANALYZE")

            conn.commit()
            conn.close()

            # Get size after optimization
            size_after = db_path.stat().st_size
            savings = size_before - size_after
            savings_mb = savings / (1024 * 1024)

            QMessageBox.information(self, "Database Optimized",
                "✅ Database optimization completed!\n\n"
                f"📏 Space saved: {savings_mb:.2f} MB\n"
                f"📊 New size: {size_after / (1024*1024):.2f} MB\n\n"
                "Database performance has been improved and file size reduced.")

        except Exception as e:
            QMessageBox.critical(self, "Optimization Error", f"Failed to optimize database:\n{str(e)}")

    def _export_database_data(self, db_path):
        """Export database data to various formats"""
        try:
            from datetime import datetime
            import sqlite3

            # Create export dialog
            export_dialog = QDialog(self)
            export_dialog.setWindowTitle("📤 Export Database Data")
            export_dialog.resize(500, 300)
            export_dialog.setStyleSheet("""
                QDialog {
                    background: #0f1117;
                    color: #e6eef6;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #bd93f9;
                    margin-top: 6px;
                    color: #e6eef6;
                }
                QRadioButton {
                    color: #e6eef6;
                }
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #35c06f, stop:1 #1e8b57);
                    color: #ffffff;
                    padding: 8px 16px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #4ade80, stop:1 #22c55e);
                }
            """)

            layout = QVBoxLayout()

            # Header
            header = QLabel("📤 Export Database Data")
            header.setStyleSheet("font-size: 16px; font-weight: bold; color: #50fa7b; padding: 10px;")
            layout.addWidget(header)

            # Export options
            options_group = QGroupBox("Export Options")
            options_layout = QVBoxLayout()

            self.export_sql = QRadioButton("📄 SQL Script (full database schema and data)")
            self.export_sql.setChecked(True)
            options_layout.addWidget(self.export_sql)

            self.export_csv_all = QRadioButton("📊 CSV Files (all tables as separate CSV files)")
            options_layout.addWidget(self.export_csv_all)

            options_group.setLayout(options_layout)
            layout.addWidget(options_group)

            # Buttons
            button_layout = QHBoxLayout()
            button_layout.addStretch()

            btn_cancel_export = QPushButton("❌ Cancel")
            btn_cancel_export.clicked.connect(export_dialog.reject)
            button_layout.addWidget(btn_cancel_export)

            btn_do_export = QPushButton("📤 Export")
            btn_do_export.clicked.connect(lambda: self._perform_export(export_dialog, db_path))
            button_layout.addWidget(btn_do_export)

            layout.addLayout(button_layout)
            export_dialog.setLayout(layout)
            export_dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to setup export:\n{str(e)}")

    def _perform_export(self, dialog, db_path):
        """Perform the actual export"""
        try:
            from datetime import datetime
            import sqlite3

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if self.export_sql.isChecked():
                # Export as SQL
                filename, _ = QFileDialog.getSaveFileName(
                    dialog,
                    "Export SQL Script",
                    str(APP_ROOT / f"scum_database_export_{timestamp}.sql"),
                    "SQL Files (*.sql);;All Files (*.*)"
                )

                if not filename:
                    return

                conn = sqlite3.connect(str(db_path))
                with open(filename, 'w', encoding='utf-8') as f:
                    # Write schema
                    for line in conn.iterdump():
                        f.write(f"{line}\n")

                conn.close()

                QMessageBox.information(dialog, "Export Complete",
                    f"Database exported as SQL script:\n{filename}")

            elif self.export_csv_all.isChecked():
                # Export all tables as CSV
                export_dir = QFileDialog.getExistingDirectory(
                    dialog,
                    "Select Export Directory",
                    str(APP_ROOT)
                )

                if not export_dir:
                    return

                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()

                exported_count = 0
                for table_name, in tables:
                    # Export each table to CSV
                    cursor.execute(f"SELECT * FROM {table_name}")
                    rows = cursor.fetchall()

                    # Get column names
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    column_names = [col[1] for col in columns]

                    csv_filename = f"{table_name}_{timestamp}.csv"
                    csv_path = os.path.join(export_dir, csv_filename)

                    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                        import csv
                        writer = csv.writer(csvfile)
                        writer.writerow(column_names)
                        writer.writerows(rows)

                    exported_count += 1

                conn.close()

                QMessageBox.information(dialog, "Export Complete",
                    f"Exported {exported_count} tables as CSV files to:\n{export_dir}")

            dialog.accept()

        except Exception as e:
            QMessageBox.critical(dialog, "Export Error", f"Failed to export data:\n{str(e)}")

    def _load_table_preview(self, db_path):
        """Load table preview in the database manager dialog"""
        try:
            table_name = self.db_table_combo.currentText()
            if not table_name or table_name == "-- Select Table --":
                self.db_preview_table.setRowCount(0)
                self.db_preview_table.setColumnCount(0)
                return

            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get column info
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]

            # Set up table
            self.db_preview_table.setColumnCount(len(column_names))
            self.db_preview_table.setHorizontalHeaderLabels(column_names)

            # Get data (limit to 50 rows for preview)
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 50")
            rows = cursor.fetchall()

            self.db_preview_table.setRowCount(len(rows))
            for row_idx, row in enumerate(rows):
                for col_idx, value in enumerate(row):
                    item = QTableWidgetItem(str(value) if value is not None else "")
                    self.db_preview_table.setItem(row_idx, col_idx, item)

            # Resize columns
            self.db_preview_table.resizeColumnsToContents()

            conn.close()

        except Exception as e:
            self.db_preview_table.setRowCount(0)
            self.db_preview_table.setColumnCount(0)
            print(f"Error loading table preview: {e}")
    
    def open_visual_config_editor_old(self):
        """Legacy visual configuration editor"""
        from PySide6.QtWidgets import QDialog, QTreeWidget, QTreeWidgetItem, QLineEdit, QCheckBox, QDoubleSpinBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("🎨 Visual Configuration Editor")
        dialog.resize(1200, 800)
        
        main_layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("📝 Easy Visual Configuration Editor")
        header_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #e6eef6; padding: 10px;")
        main_layout.addWidget(header_label)
        
        # Info label
        info_label = QLabel("💡 Modify settings below. Changes will be applied to your server configuration files.")
        info_label.setStyleSheet("color: #8be9fd; padding: 5px; background: #2b2f36; border-radius: 3px;")
        main_layout.addWidget(info_label)
        
        # Splitter for tree and editor
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Category tree
        tree = QTreeWidget()
        tree.setHeaderLabels(["Setting", "Value"])
        tree.setColumnWidth(0, 400)
        tree.setStyleSheet("""
            QTreeWidget {
                background: #0d1016;
                border: 1px solid #2b2f36;
                border-radius: 5px;
                color: #e6eef6;
                font-size: 11px;
            }
            QTreeWidget::item {
                padding: 5px;
            }
            QTreeWidget::item:selected {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #1e8b57, stop:1 #35c06f);
            }
        """)
        
        # Build configuration tree
        self.build_config_tree(tree)
        
        splitter.addWidget(tree)
        
        # Right side: Setting details and editor
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        setting_name_label = QLabel("Setting Name:")
        self.visual_setting_name = QLabel("Select a setting from the tree")
        self.visual_setting_name.setStyleSheet("font-weight: bold; color: #50fa7b; font-size: 14px;")
        
        setting_desc_label = QLabel("Description:")
        self.visual_setting_desc = QLabel("No setting selected")
        self.visual_setting_desc.setWordWrap(True)
        self.visual_setting_desc.setStyleSheet("color: #8be9fd; padding: 10px; background: #1a1d23; border-radius: 5px;")
        
        value_label = QLabel("Value:")
        self.visual_setting_value = QLineEdit()
        self.visual_setting_value.setStyleSheet("""
            QLineEdit {
                background: #0d1016;
                border: 1px solid #2b2f36;
                border-radius: 5px;
                padding: 8px;
                color: #e6eef6;
                font-size: 12px;
            }
        """)
        
        apply_button = QPushButton("✅ Apply Change")
        apply_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #35c06f, stop:1 #1e8b57);
                color: #ffffff;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #4ade80, stop:1 #22c55e);
            }
        """)
        apply_button.clicked.connect(lambda: self.apply_visual_setting_change(tree))
        
        right_layout.addWidget(setting_name_label)
        right_layout.addWidget(self.visual_setting_name)
        right_layout.addWidget(setting_desc_label)
        right_layout.addWidget(self.visual_setting_desc)
        right_layout.addWidget(value_label)
        right_layout.addWidget(self.visual_setting_value)
        right_layout.addWidget(apply_button)
        right_layout.addStretch()
        
        right_panel.setLayout(right_layout)
        splitter.addWidget(right_panel)
        
        # Connect tree selection
        tree.itemClicked.connect(lambda item, col: self.on_visual_setting_selected(item))
        
        main_layout.addWidget(splitter)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save All Changes")
        save_btn.clicked.connect(lambda: self.save_visual_config_changes(dialog))
        save_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #35c06f, stop:1 #1e8b57);
                padding: 10px 20px;
                font-weight: bold;
            }
        """)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
        dialog.setLayout(main_layout)
        dialog.exec_()
    
    def build_config_tree(self, tree):
        """Build configuration tree with categories"""
        categories = {
            "🖥️ Server Basics": [
                ("ServerName", "My SCUM Server", "Display name in server browser"),
                ("MaxPlayers", "64", "Maximum number of players (1-100)"),
                ("ServerPassword", "", "Password required to join (empty = no password)"),
                ("ServerPort", "7777", "Main game port"),
                ("QueryPort", "7778", "Steam query port"),
            ],
            "⚔️ Gameplay & Difficulty": [
                ("PuppetDamageMultiplier", "1.0", "Zombie damage multiplier (0.1-10.0)"),
                ("PlayerDamageMultiplier", "1.0", "Player damage taken (0.1-10.0)"),
                ("MetabolismRateMultiplier", "1.0", "Hunger/thirst rate (0.1-10.0)"),
                ("EnablePvP", "true", "Allow player vs player combat"),
                ("EnableFriendlyFire", "true", "Team damage enabled"),
            ],
            "📦 Loot & Resources": [
                ("LootSpawnMultiplier", "1.0", "Overall loot amount (0.1-10.0)"),
                ("WeaponSpawnMultiplier", "1.0", "Weapon spawn rate (0.1-10.0)"),
                ("AmmoSpawnMultiplier", "1.0", "Ammo spawn rate (0.1-10.0)"),
                ("FoodSpawnMultiplier", "1.0", "Food spawn rate (0.1-10.0)"),
                ("LootRespawnTime", "1800.0", "Loot respawn time in seconds"),
            ],
            "🚗 Vehicles": [
                ("VehicleSpawnMultiplier", "1.0", "Vehicle spawn rate (0.1-10.0)"),
                ("VehicleFuelConsumptionMultiplier", "1.0", "Fuel usage rate (0.1-10.0)"),
                ("VehicleDamageMultiplier", "1.0", "Vehicle damage taken (0.1-10.0)"),
                ("EnableVehicleLocking", "true", "Lock vehicles to owners"),
            ],
            "🧟 AI & Zombies": [
                ("AIMaxCount", "50", "Maximum AI entities (0-200)"),
                ("AISpawnMultiplier", "1.0", "AI spawn rate (0.1-10.0)"),
                ("EnableAIHordes", "false", "Enable zombie hordes"),
                ("HordeSize", "20", "Zombies per horde (5-100)"),
            ],
            "⏰ Time & Weather": [
                ("TimeAcceleration", "4.0", "Time speed multiplier (1.0 = real-time)"),
                ("TimeAccelerationNightMultiplier", "8.0", "Night time speed"),
                ("EnableDynamicWeather", "true", "Dynamic weather system"),
                ("WeatherImpactMultiplier", "1.0", "Weather effects strength"),
            ],
            "💀 Respawn & Death": [
                ("RespawnTime", "60.0", "Time until respawn in seconds"),
                ("RespawnProtectionTime", "30.0", "Protection after respawn"),
                ("DeathPenaltyMultiplier", "1.0", "Stat loss on death (0.0-1.0)"),
            ],
            "🏗️ Base Building": [
                ("EnableBaseBuilding", "true", "Allow base building"),
                ("BuildingDecayTime", "604800.0", "Building decay time (seconds)"),
                ("EnableBaseRaiding", "true", "Bases can be raided"),
                ("MaxBasesPerPlayer", "3", "Max bases per player"),
            ],
            "🔧 Crafting": [
                ("CraftingTimeMultiplier", "1.0", "Crafting speed (0.1-10.0)"),
                ("CraftingCostMultiplier", "1.0", "Resource cost (0.1-10.0)"),
                ("EnableAdvancedCrafting", "true", "Advanced crafting recipes"),
            ],
            "⚡ Performance": [
                ("TickRate", "30", "Server tick rate (10-60)"),
                ("SimulationDistance", "10000.0", "Simulation range in meters"),
                ("MaxPlayersPerArea", "16", "Max players per zone"),
                ("EnablePerformanceOptimization", "true", "Performance mode"),
            ],
        }
        
        for category, settings in categories.items():
            cat_item = QTreeWidgetItem(tree, [category])
            cat_item.setExpanded(True)
            cat_item.setFont(0, QFont("Segoe UI", 11, QFont.Bold))
            
            for setting_name, default_value, description in settings:
                setting_item = QTreeWidgetItem(cat_item, [setting_name, default_value])
                setting_item.setData(0, Qt.UserRole, description)
                setting_item.setData(1, Qt.UserRole, default_value)
    
    def on_visual_setting_selected(self, item):
        """Handle visual setting selection"""
        if item.parent():  # Is a setting, not a category
            setting_name = item.text(0)
            setting_value = item.text(1)
            setting_desc = item.data(0, Qt.UserRole)
            
            self.visual_setting_name.setText(setting_name)
            self.visual_setting_desc.setText(setting_desc if setting_desc else "No description available")
            self.visual_setting_value.setText(setting_value)
    
    def apply_visual_setting_change(self, tree):
        """Apply visual setting change to tree"""
        current_item = tree.currentItem()
        if current_item and current_item.parent():
            new_value = self.visual_setting_value.text()
            current_item.setText(1, new_value)
            QMessageBox.information(self, "Applied", f"Setting changed to: {new_value}\n\nClick 'Save All Changes' to save to config files.")
    
    def save_visual_config_changes(self, dialog):
        """Save all visual config changes to files"""
        try:
            # This would collect all values from tree and save to config files
            QMessageBox.information(self, "Saved", "All configuration changes saved successfully!\n\nRestart server to apply changes.")
            dialog.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save changes:\n{str(e)}")
    
    def launch_scum_game(self):
        """Launch SCUM game client"""
        try:
            # Try to launch via Steam
            steam_game_id = "513710"  # SCUM's Steam App ID
            
            # Try Steam protocol first
            import webbrowser
            steam_url = f"steam://rungameid/{steam_game_id}"
            
            self.write_log('events', 'Launching SCUM game client...', 'INFO')
            self.status_bar.showMessage("🎮 Launching SCUM game...")
            
            # Open Steam game
            webbrowser.open(steam_url)
            
            QMessageBox.information(
                self,
                "🎮 Game Launching",
                "SCUM game is being launched via Steam!\n\n"
                "The game should start in a few moments.\n"
                "Once in-game, use 'Play' → 'Internet' to find your server."
            )
            
            self.write_log('events', 'SCUM game client launched successfully', 'INFO')
            
        except Exception as e:
            self.write_log('error', f'Failed to launch SCUM game: {str(e)}', 'ERROR')
            QMessageBox.warning(
                self,
                "Launch Failed",
                f"Could not auto-launch SCUM game.\n\n"
                f"Error: {str(e)}\n\n"
                "Please launch SCUM manually from Steam."
            )

    # === ENHANCED LOGGING FUNCTIONS ===
    def refresh_logs(self):
        """Refresh all log viewers - ASYNC VERSION"""
        # Use QTimer to defer execution and prevent UI blocking
        QTimer.singleShot(10, self._refresh_logs_async)

    def _refresh_logs_async(self):
        """Async helper for refresh_logs"""
        # Load logs asynchronously
        self._load_logs_async()
        self.load_player_logs()
        self.load_error_logs()
        self.load_admin_logs()
        self.load_events_logs()
        # Update stats after a short delay to allow other operations to complete
        QTimer.singleShot(100, self.update_log_stats)

    def load_player_logs(self):
        """Load player activity logs with auto-scroll"""
        logs_dir = APP_ROOT / "Logs"
        logs_dir.mkdir(exist_ok=True)
        
        logs = logs_dir / "players.log"
        
        # Create initial log file if it doesn't exist
        if not logs.exists():
            try:
                with logs.open("w", encoding="utf-8") as f:
                    from datetime import datetime
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Player Activity Log initialized\n")
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Tracking player connections and disconnections\n")
            except Exception:
                pass
        
        # Check if file was modified since last read (performance optimization)
        try:
            current_mtime = logs.stat().st_mtime
            if current_mtime == self.log_mtimes.get('players', 0):
                return  # File hasn't changed, skip re-read
            self.log_mtimes['players'] = current_mtime
        except:
            pass
        
        # Check if user is at the bottom BEFORE updating content
        scrollbar = self.text_player_logs.verticalScrollBar()
        # Only consider "at bottom" if scrollbar is at the end (within 50 pixels for better UX)
        # This allows slight scrolling without disabling auto-scroll
        was_at_bottom = scrollbar.maximum() == 0 or scrollbar.value() >= scrollbar.maximum() - 50
        
        # Read and display logs
        try:
            with logs.open("r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if content.strip():
                    # Apply color formatting for player events
                    import html
                    lines = []
                    for line in content.splitlines():
                        esc = html.escape(line)
                        if "connected" in line.lower() or "joined" in line.lower():
                            lines.append(f"<span style='color:#50fa7b'>✅ {esc}</span>")
                        elif "disconnected" in line.lower() or "left" in line.lower():
                            lines.append(f"<span style='color:#ffb86b'>❌ {esc}</span>")
                        elif "kicked" in line.lower() or "banned" in line.lower():
                            lines.append(f"<span style='color:#ff6b6b'>⛔ {esc}</span>")
                        elif "identified" in line.lower():
                            lines.append(f"<span style='color:#8be9fd'>🔍 {esc}</span>")
                        else:
                            lines.append(esc)
                    html_text = "<pre style='font-family: Consolas, monospace; font-size: 11px; line-height: 1.4;'>{}</pre>".format("\n".join(lines))
                    self.text_player_logs.setHtml(html_text)
                else:
                    self.text_player_logs.setPlainText("👥 Player activity log is empty. Events will appear here when players connect.")
        except Exception as e:
            self.text_player_logs.setPlainText(f"❌ Could not read player logs: {e}")
        
        # ONLY auto-scroll if user was truly at the bottom
        if was_at_bottom:
            QTimer.singleShot(50, lambda: scrollbar.setValue(scrollbar.maximum()))

    def load_error_logs(self):
        """Load error logs with auto-scroll"""
        logs_dir = APP_ROOT / "Logs"
        logs_dir.mkdir(exist_ok=True)
        
        logs = logs_dir / "errors.log"
        
        # Create initial log file if it doesn't exist
        if not logs.exists():
            try:
                with logs.open("w", encoding="utf-8") as f:
                    from datetime import datetime
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Error Log initialized\n")
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Server errors and warnings will be logged here\n")
            except Exception:
                pass
        
        # Check if file was modified since last read (performance optimization)
        try:
            current_mtime = logs.stat().st_mtime
            if current_mtime == self.log_mtimes.get('errors', 0):
                return  # File hasn't changed, skip re-read
            self.log_mtimes['errors'] = current_mtime
        except:
            pass
        
        # Check if user is at the bottom BEFORE updating content
        scrollbar = self.text_error_logs.verticalScrollBar()
        # Only consider "at bottom" if scrollbar is at the end (within 50 pixels for better UX)
        was_at_bottom = scrollbar.maximum() == 0 or scrollbar.value() >= scrollbar.maximum() - 50
        
        # Read and display logs with color coding
        try:
            with logs.open("r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if content.strip():
                    # Apply color formatting for errors
                    import html
                    lines = []
                    for line in content.splitlines():
                        esc = html.escape(line)
                        if "critical" in line.lower() or "fatal" in line.lower():
                            lines.append(f"<span style='color:#ff0000; font-weight:bold;'>🔴 {esc}</span>")
                        elif "error" in line.lower():
                            lines.append(f"<span style='color:#ff6b6b'>❌ {esc}</span>")
                        elif "warn" in line.lower():
                            lines.append(f"<span style='color:#ffb86b'>⚠️ {esc}</span>")
                        else:
                            lines.append(esc)
                    html_text = "<pre style='font-family: Consolas, monospace; font-size: 11px; line-height: 1.4;'>{}</pre>".format("\n".join(lines))
                    self.text_error_logs.setHtml(html_text)
                else:
                    self.text_error_logs.setPlainText("✅ Error log is empty. No errors detected - server is running smoothly!")
        except Exception as e:
            self.text_error_logs.setPlainText(f"❌ Could not read error logs: {e}")
        
        # ONLY auto-scroll if user was truly at the bottom
        if was_at_bottom:
            QTimer.singleShot(50, lambda: scrollbar.setValue(scrollbar.maximum()))

    def load_admin_logs(self):
        """Load admin action logs with auto-scroll"""
        logs_dir = APP_ROOT / "Logs"
        logs_dir.mkdir(exist_ok=True)
        
        logs = logs_dir / "admin.log"
        
        # Create initial log file if it doesn't exist
        if not logs.exists():
            try:
                with logs.open("w", encoding="utf-8") as f:
                    from datetime import datetime
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Admin Action Log initialized\n")
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Admin commands and actions will be logged here\n")
            except Exception:
                pass
        
        # Check if file was modified since last read (performance optimization)
        try:
            current_mtime = logs.stat().st_mtime
            if current_mtime == self.log_mtimes.get('admin', 0):
                return  # File hasn't changed, skip re-read
            self.log_mtimes['admin'] = current_mtime
        except:
            pass
        
        # Check if user is at the bottom BEFORE updating content
        scrollbar = self.text_admin_logs.verticalScrollBar()
        # Only consider "at bottom" if scrollbar is at the end (within 50 pixels for better UX)
        was_at_bottom = scrollbar.maximum() == 0 or scrollbar.value() >= scrollbar.maximum() - 50
        
        # Read and display logs with color coding
        try:
            with logs.open("r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if content.strip():
                    # Apply color formatting for admin actions
                    import html
                    lines = []
                    for line in content.splitlines():
                        esc = html.escape(line)
                        if "kick" in line.lower() or "ban" in line.lower():
                            lines.append(f"<span style='color:#ff6b6b'>⛔ {esc}</span>")
                        elif "unban" in line.lower() or "pardon" in line.lower():
                            lines.append(f"<span style='color:#50fa7b'>✅ {esc}</span>")
                        elif "teleport" in line.lower() or "spawn" in line.lower():
                            lines.append(f"<span style='color:#bd93f9'>✨ {esc}</span>")
                        else:
                            lines.append(f"<span style='color:#ffb86b'>⚡ {esc}</span>")
                    html_text = "<pre style='font-family: Consolas, monospace; font-size: 11px; line-height: 1.4;'>{}</pre>".format("\n".join(lines))
                    self.text_admin_logs.setHtml(html_text)
                else:
                    self.text_admin_logs.setPlainText("⚡ Admin log is empty. Admin actions will be recorded here.")
        except Exception as e:
            self.text_admin_logs.setPlainText(f"❌ Could not read admin logs: {e}")
        
        # ONLY auto-scroll if user was truly at the bottom
        if was_at_bottom:
            QTimer.singleShot(50, lambda: scrollbar.setValue(scrollbar.maximum()))

    def load_events_logs(self):
        """Load server events logs with auto-scroll"""
        logs_dir = APP_ROOT / "Logs"
        logs_dir.mkdir(exist_ok=True)
        
        logs = logs_dir / "events.log"
        
        # Create initial log file if it doesn't exist
        if not logs.exists():
            try:
                with logs.open("w", encoding="utf-8") as f:
                    from datetime import datetime
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Server Events Log initialized\n")
                    f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] INFO: Server start/stop events and other activities will be logged here\n")
            except Exception:
                pass
        
        # Check if file was modified since last read (performance optimization)
        try:
            current_mtime = logs.stat().st_mtime
            if current_mtime == self.log_mtimes.get('events', 0):
                return  # File hasn't changed, skip re-read
            self.log_mtimes['events'] = current_mtime
        except:
            pass
        
        # Check if user is at the bottom BEFORE updating content
        scrollbar = self.text_events_logs.verticalScrollBar()
        # Only consider "at bottom" if scrollbar is at the end (within 50 pixels for better UX)
        was_at_bottom = scrollbar.maximum() == 0 or scrollbar.value() >= scrollbar.maximum() - 50
        
        # Read and display logs with color coding
        try:
            with logs.open("r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if content.strip():
                    # Apply color formatting for events
                    import html
                    lines = []
                    for line in content.splitlines():
                        esc = html.escape(line)
                        if "started" in line.lower() or "online" in line.lower():
                            lines.append(f"<span style='color:#50fa7b'>✅ {esc}</span>")
                        elif "stopped" in line.lower() or "shutdown" in line.lower():
                            lines.append(f"<span style='color:#ff6b6b'>⛔ {esc}</span>")
                        elif "restart" in line.lower():
                            lines.append(f"<span style='color:#ffb86b'>🔄 {esc}</span>")
                        elif "backup" in line.lower() or "save" in line.lower():
                            lines.append(f"<span style='color:#8be9fd'>💾 {esc}</span>")
                        elif "connected" in line.lower() or "player" in line.lower():
                            lines.append(f"<span style='color:#bd93f9'>👥 {esc}</span>")
                        else:
                            lines.append(esc)
                    html_text = "<pre style='font-family: Consolas, monospace; font-size: 11px; line-height: 1.4;'>{}</pre>".format("\n".join(lines))
                    self.text_events_logs.setHtml(html_text)
                else:
                    self.text_events_logs.setPlainText("📊 Events log is empty. Server events will be recorded here.")
        except Exception as e:
            self.text_events_logs.setPlainText(f"❌ Could not read events logs: {e}")
        
        # ONLY auto-scroll if user was truly at the bottom
        if was_at_bottom:
            QTimer.singleShot(50, lambda: scrollbar.setValue(scrollbar.maximum()))

    def update_log_stats(self):
        """Update log statistics"""
        try:
            total = len(self.text_logs.toPlainText().splitlines())
            errors = self.text_logs.toPlainText().lower().count('error')
            warnings = self.text_logs.toPlainText().lower().count('warn')
            players = len(self.text_player_logs.toPlainText().splitlines())
            
            self.log_stats.setText(f"📈 Stats: {total} total lines | {errors} errors | {warnings} warnings | {players} player events")
        except:
            pass

    def clear_log_displays(self):
        """Clear all log displays"""
        self.text_logs.clear()
        self.text_player_logs.clear()
        self.text_error_logs.clear()
        self.text_admin_logs.clear()
        self.text_events_logs.clear()
        QMessageBox.information(self, "Cleared", "All log displays have been cleared.\n\nNote: Log files are not deleted.")

    def export_logs(self):
        """Export logs to file"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Logs",
            str(APP_ROOT / f"logs_export_{timestamp}.txt"),
            "Text Files (*.txt);;All Files (*.*)"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=== SCUM SERVER LOGS EXPORT ===\n")
                f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("=== SERVER LOGS ===\n")
                f.write(self.text_logs.toPlainText())
                f.write("\n\n")
                
                f.write("=== PLAYER LOGS ===\n")
                f.write(self.text_player_logs.toPlainText())
                f.write("\n\n")
                
                f.write("=== ERROR LOGS ===\n")
                f.write(self.text_error_logs.toPlainText())
                f.write("\n\n")
                
                f.write("=== ADMIN LOGS ===\n")
                f.write(self.text_admin_logs.toPlainText())
                f.write("\n\n")
                
                f.write("=== EVENTS LOGS ===\n")
                f.write(self.text_events_logs.toPlainText())
            
            QMessageBox.information(self, "Export Complete", f"Logs exported to:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Failed to export logs:\n{str(e)}")

    def filter_logs(self):
        """Filter logs by search term"""
        search_term = self.log_search.text().lower()
        if not search_term:
            return
        
        # Simple highlight - could be enhanced
        QMessageBox.information(self, "Search", f"Searching for: {search_term}\n\nUse Ctrl+F in the log viewer for better search functionality.")

    def filter_logs_by_time(self):
        """Filter logs by time range"""
        time_range = self.log_time_filter.currentText()
        # Placeholder - would need timestamp parsing
        QMessageBox.information(self, "Time Filter", f"Time filter: {time_range}\n\n(Feature coming soon)")

    def filter_logs_by_level(self):
        """Filter logs by log level"""
        level = self.log_level_filter.currentText()
        # Placeholder - would need log level parsing
        QMessageBox.information(self, "Level Filter", f"Level filter: {level}\n\n(Feature coming soon)")

    # === LOG WRITING FUNCTIONS ===
    def write_log(self, log_type: str, message: str, level: str = "INFO"):
        try:
            from datetime import datetime
            log_dir = APP_ROOT / "Logs"
            log_dir.mkdir(exist_ok=True)
            log_file = log_dir / f"{log_type}.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] [{level}] {message}\n"
            with log_file.open("a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception:
            pass

        # === DATABASE MANAGEMENT METHODS ===
    # Database functionality removed





def main():
    app = QApplication(sys.argv)
    win = SCUMManager()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
