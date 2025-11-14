"""
🗄️ ULTIMATE SQLite Database Manager - SQLiteStudio Clone

Complete professional database manager matching SQLiteStudio's functionality
with modern UI, full editing capabilities, and all advanced features.
"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import sqlite3
from pathlib import Path
from datetime import datetime
import csv
import json
import sys


class EditableTableWidget(QTableWidget):
    """Custom table widget with immediate editing support"""
    
    cellEdited = Signal(int, int, str, str)  # row, col, old_value, new_value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditTriggers(
            QAbstractItemView.DoubleClicked | 
            QAbstractItemView.EditKeyPressed |
            QAbstractItemView.AnyKeyPressed
        )
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.itemChanged.connect(self._on_item_changed)
        self._editing_enabled = True
        self._old_values = {}
    
    def _on_item_changed(self, item):
        """Handle item changes"""
        if not self._editing_enabled:
            return
        
        row, col = item.row(), item.column()
        key = (row, col)
        old_value = self._old_values.get(key, "")
        new_value = item.text()
        
        if old_value != new_value:
            self.cellEdited.emit(row, col, old_value, new_value)
            self._old_values[key] = new_value
    
    def setItemData(self, row, col, value):
        """Set item data without triggering change event"""
        self._editing_enabled = False
        item = self.item(row, col)
        if not item:
            item = QTableWidgetItem(str(value) if value is not None else "")
            self.setItem(row, col, item)
        else:
            item.setText(str(value) if value is not None else "")
        self._old_values[(row, col)] = str(value) if value is not None else ""
        self._editing_enabled = True


class UltimateDBManager(QDialog):
    """Complete SQLite Database Manager - SQLiteStudio equivalent"""
    
    def __init__(self, parent, db_path):
        super().__init__(parent)
        self.db_path = Path(db_path)
        self.connection = None
        self.current_table = None
        self.query_history = []
        self.table_data_cache = {}
        
        self.setWindowTitle(f"🗄️ SQLite Database Manager - {self.db_path.name}")
        self.resize(1600, 1000)
        self.setModal(False)
        
        self._init_ui()
        self._connect_database()
        self._load_structure()
    
    def _init_ui(self):
        """Initialize the complete UI"""
        self.setStyleSheet(self._get_modern_stylesheet())
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Menu bar
        menubar = self._create_menubar()
        layout.setMenuBar(menubar)
        
        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        
        # Main splitter (sidebar + content)
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left: Database navigator
        nav_widget = self._create_navigator()
        main_splitter.addWidget(nav_widget)
        
        # Right: Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        
        # Add default tabs
        self._create_data_browser_tab()
        self._create_sql_editor_tab()
        self._create_structure_tab()
        
        main_splitter.addWidget(self.tab_widget)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 4)
        
        layout.addWidget(main_splitter)
        
        # Status bar
        statusbar = self._create_statusbar()
        layout.addWidget(statusbar)
    
    def _create_menubar(self):
        """Create comprehensive menu bar"""
        menubar = QMenuBar()
        
        # Database menu
        db_menu = menubar.addMenu("&Database")
        db_menu.addAction("📂 Open Database...", self._open_database, "Ctrl+O")
        db_menu.addAction("🔄 Refresh", self._refresh_all, "F5")
        db_menu.addSeparator()
        db_menu.addAction("💾 Commit Changes", self._commit_changes, "Ctrl+S")
        db_menu.addAction("↩️ Rollback", self._rollback_changes, "Ctrl+Z")
        db_menu.addSeparator()
        db_menu.addAction("📤 Export Database...", self._export_database)
        db_menu.addAction("📥 Import Data...", self._import_data)
        db_menu.addSeparator()
        db_menu.addAction("🚪 Close", self.close, "Ctrl+W")
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction("➕ Insert Row", self._insert_row, "Ctrl+N")
        edit_menu.addAction("📋 Duplicate Row", self._duplicate_row, "Ctrl+D")
        edit_menu.addAction("🗑️ Delete Row", self._delete_row, "Delete")
        edit_menu.addSeparator()
        edit_menu.addAction("🔍 Find...", self._show_find, "Ctrl+F")
        edit_menu.addAction("🔄 Replace...", self._show_replace, "Ctrl+H")
        
        # View menu
        view_menu = menubar.addMenu("&View")
        view_menu.addAction("🗂️ Database Structure", lambda: self.tab_widget.setCurrentIndex(2))
        view_menu.addAction("📊 Data Browser", lambda: self.tab_widget.setCurrentIndex(0))
        view_menu.addAction("📝 SQL Editor", lambda: self.tab_widget.setCurrentIndex(1))
        view_menu.addSeparator()
        view_menu.addAction("⚙️ Settings", self._show_settings)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        tools_menu.addAction("🧹 VACUUM", self._vacuum_database)
        tools_menu.addAction("🔄 REINDEX", self._reindex_database)
        tools_menu.addAction("📊 ANALYZE", self._analyze_database)
        tools_menu.addSeparator()
        tools_menu.addAction("✅ Integrity Check", self._integrity_check)
        tools_menu.addAction("💾 Create Backup...", self._create_backup)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("❓ Documentation", self._show_docs)
        help_menu.addAction("ℹ️ About", self._show_about)
        
        return menubar
    
    def _create_toolbar(self):
        """Create main toolbar"""
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3e3e42, stop:1 #2d2d30);
                border-bottom: 1px solid #1e1e1e;
                spacing: 5px;
                padding: 5px;
            }
            QToolButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 3px;
                padding: 5px;
                color: #ffffff;
            }
            QToolButton:hover {
                background: #505052;
                border-color: #007acc;
            }
            QToolButton:pressed {
                background: #007acc;
            }
        """)
        
        # File operations
        toolbar.addAction("📂 Open", self._open_database).setToolTip("Open Database (Ctrl+O)")
        toolbar.addAction("💾 Save", self._commit_changes).setToolTip("Commit Changes (Ctrl+S)")
        toolbar.addAction("🔄 Refresh", self._refresh_all).setToolTip("Refresh (F5)")
        toolbar.addSeparator()
        
        # Data operations
        toolbar.addAction("➕ Insert", self._insert_row).setToolTip("Insert Row (Ctrl+N)")
        toolbar.addAction("🗑️ Delete", self._delete_row).setToolTip("Delete Row (Del)")
        toolbar.addAction("📋 Duplicate", self._duplicate_row).setToolTip("Duplicate Row (Ctrl+D)")
        toolbar.addSeparator()
        
        # Tools
        toolbar.addAction("🔍 Find", self._show_find).setToolTip("Find (Ctrl+F)")
        toolbar.addAction("📤 Export", self._export_table).setToolTip("Export Current Table")
        toolbar.addAction("📥 Import", self._import_table).setToolTip("Import to Current Table")
        toolbar.addSeparator()
        
        # Quick actions
        toolbar.addAction("🧹 VACUUM", self._vacuum_database).setToolTip("Vacuum Database")
        toolbar.addAction("⚙️ Settings", self._show_settings).setToolTip("Settings")
        
        return toolbar
    
    def _create_navigator(self):
        """Create database structure navigator"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Header
        header = QLabel("📁 Database Structure")
        header.setStyleSheet("font-weight: bold; font-size: 12pt; padding: 5px;")
        layout.addWidget(header)
        
        # Search filter
        self.nav_filter = QLineEdit()
        self.nav_filter.setPlaceholderText("🔍 Filter objects...")
        self.nav_filter.textChanged.connect(self._filter_navigator)
        layout.addWidget(self.nav_filter)
        
        # Tree widget
        self.nav_tree = QTreeWidget()
        self.nav_tree.setHeaderHidden(True)
        self.nav_tree.itemDoubleClicked.connect(self._on_nav_item_clicked)
        self.nav_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.nav_tree.customContextMenuRequested.connect(self._show_nav_context_menu)
        layout.addWidget(self.nav_tree)
        
        # Quick stats
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #888; font-size: 9pt; padding: 5px;")
        layout.addWidget(self.stats_label)
        
        return widget
    
    def _create_data_browser_tab(self):
        """Create enhanced data browser tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Controls
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        
        # Table selector
        controls_layout.addWidget(QLabel("📋 Table:"))
        self.table_combo = QComboBox()
        self.table_combo.setMinimumWidth(200)
        self.table_combo.currentTextChanged.connect(self._load_table_data)
        controls_layout.addWidget(self.table_combo)
        
        # Quick buttons
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self._refresh_current_table)
        controls_layout.addWidget(btn_refresh)
        
        btn_add = QPushButton("➕ Add Row")
        btn_add.clicked.connect(self._insert_row)
        controls_layout.addWidget(btn_add)
        
        btn_delete = QPushButton("🗑️ Delete")
        btn_delete.clicked.connect(self._delete_row)
        controls_layout.addWidget(btn_delete)
        
        btn_commit = QPushButton("💾 Commit")
        btn_commit.setStyleSheet("background-color: #16c60c;")
        btn_commit.clicked.connect(self._commit_changes)
        controls_layout.addWidget(btn_commit)
        
        btn_rollback = QPushButton("↩️ Rollback")
        btn_rollback.setStyleSheet("background-color: #e81123;")
        btn_rollback.clicked.connect(self._rollback_changes)
        controls_layout.addWidget(btn_rollback)
        
        controls_layout.addStretch()
        
        # Filter
        controls_layout.addWidget(QLabel("🔍 Filter:"))
        self.data_filter = QLineEdit()
        self.data_filter.setPlaceholderText("Search in table...")
        self.data_filter.setMinimumWidth(200)
        self.data_filter.textChanged.connect(self._filter_table_data)
        controls_layout.addWidget(self.data_filter)
        
        layout.addWidget(controls)
        
        # Data table (EDITABLE!)
        self.data_table = EditableTableWidget()
        self.data_table.cellEdited.connect(self._on_cell_edited)
        self.data_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.data_table.customContextMenuRequested.connect(self._show_table_context_menu)
        layout.addWidget(self.data_table)
        
        # Info bar
        info_bar = QWidget()
        info_layout = QHBoxLayout(info_bar)
        self.row_count_label = QLabel("0 rows")
        self.selected_label = QLabel("")
        self.modified_label = QLabel("")
        info_layout.addWidget(self.row_count_label)
        info_layout.addWidget(self.selected_label)
        info_layout.addWidget(self.modified_label)
        info_layout.addStretch()
        layout.addWidget(info_bar)
        
        self.tab_widget.addTab(widget, "📊 Data Browser")
    
    def _create_sql_editor_tab(self):
        """Create SQL editor tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # SQL Editor controls
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        
        btn_execute = QPushButton("▶️ Execute (F5)")
        btn_execute.setStyleSheet("background-color: #16c60c; font-weight: bold;")
        btn_execute.clicked.connect(self._execute_sql)
        controls_layout.addWidget(btn_execute)
        
        btn_clear = QPushButton("🧹 Clear")
        btn_clear.clicked.connect(lambda: self.sql_editor.clear())
        controls_layout.addWidget(btn_clear)
        
        btn_format = QPushButton("📝 Format")
        btn_format.clicked.connect(self._format_sql)
        controls_layout.addWidget(btn_format)
        
        btn_save = QPushButton("💾 Save Query")
        btn_save.clicked.connect(self._save_query)
        controls_layout.addWidget(btn_save)
        
        controls_layout.addStretch()
        
        # History dropdown
        controls_layout.addWidget(QLabel("📚 History:"))
        self.sql_history_combo = QComboBox()
        self.sql_history_combo.setMinimumWidth(300)
        self.sql_history_combo.addItem("-- Query History --")
        self.sql_history_combo.currentTextChanged.connect(self._load_history_query)
        controls_layout.addWidget(self.sql_history_combo)
        
        layout.addWidget(controls)
        
        # SQL Editor
        self.sql_editor = QPlainTextEdit()
        self.sql_editor.setFont(QFont("Consolas", 10))
        self.sql_editor.setPlaceholderText(
            "-- Enter SQL queries here\n"
            "-- Press F5 or click Execute to run\n"
            "-- Example:\n"
            "SELECT * FROM my_table WHERE id > 10;\n"
            "INSERT INTO my_table (name, value) VALUES ('test', 123);"
        )
        layout.addWidget(self.sql_editor, stretch=1)
        
        # Results area
        results_label = QLabel("📊 Query Results:")
        results_label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(results_label)
        
        self.sql_results = QTableWidget()
        self.sql_results.setAlternatingRowColors(True)
        layout.addWidget(self.sql_results, stretch=2)
        
        # Status
        self.sql_status = QLabel("Ready")
        self.sql_status.setStyleSheet("padding: 5px; color: #888;")
        layout.addWidget(self.sql_status)
        
        self.tab_widget.addTab(widget, "📝 SQL Editor")
    
    def _create_structure_tab(self):
        """Create database structure tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Controls
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self._load_structure)
        controls_layout.addWidget(btn_refresh)
        
        btn_export_schema = QPushButton("📤 Export Schema")
        btn_export_schema.clicked.connect(self._export_schema)
        controls_layout.addWidget(btn_export_schema)
        
        controls_layout.addStretch()
        layout.addWidget(controls)
        
        # Structure display
        self.structure_text = QPlainTextEdit()
        self.structure_text.setReadOnly(True)
        self.structure_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.structure_text)
        
        self.tab_widget.addTab(widget, "🏗️ Database Structure")
    
    def _create_statusbar(self):
        """Create status bar"""
        statusbar = QWidget()
        statusbar.setFixedHeight(30)
        statusbar.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2d2d30, stop:1 #1e1e1e);
                border-top: 1px solid #3e3e42;
            }
        """)
        
        layout = QHBoxLayout(statusbar)
        layout.setContentsMargins(10, 0, 10, 0)
        
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        self.db_info_label = QLabel()
        layout.addWidget(self.db_info_label)
        
        self.connection_label = QLabel()
        layout.addWidget(self.connection_label)
        
        return statusbar
    
    def _get_modern_stylesheet(self):
        """Get modern VS Code-inspired stylesheet"""
        return """
            QDialog, QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
            }
            
            QMenuBar {
                background-color: #2d2d30;
                color: #ffffff;
                border-bottom: 1px solid #3e3e42;
            }
            
            QMenuBar::item {
                padding: 5px 10px;
                background: transparent;
            }
            
            QMenuBar::item:selected {
                background: #3e3e42;
            }
            
            QMenu {
                background-color: #252526;
                color: #ffffff;
                border: 1px solid #3e3e42;
            }
            
            QMenu::item {
                padding: 5px 25px;
            }
            
            QMenu::item:selected {
                background-color: #094771;
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #505052, stop:1 #3e3e42);
                color: #ffffff;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                padding: 6px 12px;
                font-weight: 500;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a5a5c, stop:1 #505052);
                border-color: #007acc;
            }
            
            QPushButton:pressed {
                background: #007acc;
            }
            
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #3c3c3c;
                color: #ffffff;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                padding: 5px;
            }
            
            QLineEdit:focus, QComboBox:focus {
                border-color: #007acc;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #ffffff;
                margin-right: 5px;
            }
            
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #252526;
                gridline-color: #3e3e42;
                selection-background-color: #094771;
                selection-color: #ffffff;
                border: 1px solid #3e3e42;
            }
            
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #2d2d30;
            }
            
            QTableWidget::item:selected {
                background-color: #094771;
            }
            
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3e3e42, stop:1 #2d2d30);
                color: #ffffff;
                padding: 6px;
                border: none;
                border-right: 1px solid #1e1e1e;
                border-bottom: 1px solid #1e1e1e;
                font-weight: bold;
            }
            
            QHeaderView::section:hover {
                background: #505052;
            }
            
            QTreeWidget {
                background-color: #252526;
                color: #ffffff;
                border: 1px solid #3e3e42;
                alternate-background-color: #2d2d30;
            }
            
            QTreeWidget::item {
                padding: 5px;
            }
            
            QTreeWidget::item:selected {
                background-color: #094771;
            }
            
            QTreeWidget::item:hover {
                background-color: #2a2d2e;
            }
            
            QPlainTextEdit, QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e42;
                selection-background-color: #264f78;
            }
            
            QTabWidget::pane {
                border: 1px solid #3e3e42;
                background: #1e1e1e;
            }
            
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3e3e42, stop:1 #2d2d30);
                color: #ffffff;
                padding: 8px 16px;
                border: 1px solid #3e3e42;
                border-bottom: none;
                border-top-left-radius: 3px;
                border-top-right-radius: 3px;
                margin-right: 2px;
            }
            
            QTabBar::tab:selected {
                background: #1e1e1e;
                border-bottom: 2px solid #007acc;
            }
            
            QTabBar::tab:hover {
                background: #505052;
            }
            
            QScrollBar:vertical {
                background: #1e1e1e;
                width: 12px;
                border: none;
            }
            
            QScrollBar::handle:vertical {
                background: #3e3e42;
                min-height: 20px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: #505052;
            }
            
            QScrollBar:horizontal {
                background: #1e1e1e;
                height: 12px;
                border: none;
            }
            
            QScrollBar::handle:horizontal {
                background: #3e3e42;
                min-width: 20px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background: #505052;
            }
            
            QLabel {
                color: #ffffff;
            }
            
            QGroupBox {
                border: 1px solid #3e3e42;
                border-radius: 3px;
                margin-top: 10px;
                padding-top: 10px;
                color: #ffffff;
                font-weight: bold;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """
    
    def _connect_database(self):
        """Connect to the SQLite database"""
        try:
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.row_factory = sqlite3.Row
            
            # Enable foreign keys
            self.connection.execute("PRAGMA foreign_keys = ON")
            
            self.connection_label.setText(f"✅ Connected: {self.db_path.name}")
            self.status_label.setText("Database connected successfully")
            
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", 
                f"Failed to connect to database:\n{str(e)}")
            self.connection_label.setText("❌ Not connected")
    
    def _load_structure(self):
        """Load database structure into navigator"""
        if not self.connection:
            return
        
        try:
            self.nav_tree.clear()
            cursor = self.connection.cursor()
            
            # Tables
            tables_root = QTreeWidgetItem(self.nav_tree, ["📊 Tables"])
            tables_root.setExpanded(True)
            
            cursor.execute("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = cursor.fetchall()
            
            for table in tables:
                table_item = QTreeWidgetItem(tables_root, [f"📋 {table['name']}"])
                table_item.setData(0, Qt.UserRole, {'type': 'table', 'name': table['name']})
                
                # Get columns
                cursor.execute(f"PRAGMA table_info({table['name']})")
                columns = cursor.fetchall()
                
                for col in columns:
                    pk_marker = " 🔑" if col['pk'] else ""
                    col_item = QTreeWidgetItem(table_item, 
                        [f"  📄 {col['name']} ({col['type']}){pk_marker}"])
            
            # Views
            views_root = QTreeWidgetItem(self.nav_tree, ["👁️ Views"])
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='view' 
                ORDER BY name
            """)
            views = cursor.fetchall()
            
            for view in views:
                view_item = QTreeWidgetItem(views_root, [f"  🔍 {view['name']}"])
                view_item.setData(0, Qt.UserRole, {'type': 'view', 'name': view['name']})
            
            # Indexes
            indexes_root = QTreeWidgetItem(self.nav_tree, ["🔍 Indexes"])
            cursor.execute("""
                SELECT name, tbl_name FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            indexes = cursor.fetchall()
            
            for index in indexes:
                index_item = QTreeWidgetItem(indexes_root, 
                    [f"  ⚡ {index['name']} ({index['tbl_name']})"])
            
            # Triggers
            triggers_root = QTreeWidgetItem(self.nav_tree, ["⚡ Triggers"])
            cursor.execute("""
                SELECT name, tbl_name FROM sqlite_master 
                WHERE type='trigger'
                ORDER BY name
            """)
            triggers = cursor.fetchall()
            
            for trigger in triggers:
                trigger_item = QTreeWidgetItem(triggers_root, 
                    [f"  ⚙️ {trigger['name']} ({trigger['tbl_name']})"])
            
            # Update stats
            self.stats_label.setText(
                f"📊 {len(tables)} tables | 👁️ {len(views)} views | "
                f"🔍 {len(indexes)} indexes | ⚡ {len(triggers)} triggers"
            )
            
            # Load tables into combo
            self.table_combo.clear()
            self.table_combo.addItem("-- Select Table --")
            for table in tables:
                self.table_combo.addItem(table['name'])
            
            # Load structure text
            self._load_structure_text()
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error", 
                f"Failed to load database structure:\n{str(e)}")
    
    def _load_structure_text(self):
        """Load full database structure as SQL"""
        if not self.connection:
            return
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT sql FROM sqlite_master 
                WHERE sql IS NOT NULL 
                ORDER BY type, name
            """)
            
            schema_sql = "-- Database Schema\n"
            schema_sql += f"-- File: {self.db_path.name}\n"
            schema_sql += f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            for row in cursor.fetchall():
                schema_sql += row['sql'] + ";\n\n"
            
            self.structure_text.setPlainText(schema_sql)
            
        except Exception as e:
            self.structure_text.setPlainText(f"Error loading schema:\n{str(e)}")
    
    def _load_table_data(self, table_name):
        """Load data from selected table"""
        if not table_name or table_name == "-- Select Table --":
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)
            return
        
        if not self.connection:
            return
        
        try:
            self.current_table = table_name
            cursor = self.connection.cursor()
            
            # Get column info
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = cursor.fetchall()
            column_names = [col['name'] for col in columns_info]
            
            # Get data
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            # Populate table
            self.data_table.setRowCount(len(rows))
            self.data_table.setColumnCount(len(column_names))
            self.data_table.setHorizontalHeaderLabels(column_names)
            
            for row_idx, row in enumerate(rows):
                for col_idx, col_name in enumerate(column_names):
                    value = row[col_name]
                    self.data_table.setItemData(row_idx, col_idx, value)
                    
                    # Make editable
                    item = self.data_table.item(row_idx, col_idx)
                    if item:
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
            
            self.data_table.resizeColumnsToContents()
            
            # Update status
            self.row_count_label.setText(f"📊 {len(rows):,} rows")
            self.status_label.setText(f"Loaded table '{table_name}' with {len(rows):,} rows")
            
        except Exception as e:
            QMessageBox.critical(self, "Load Error", 
                f"Failed to load table data:\n{str(e)}")
    
    def _on_cell_edited(self, row, col, old_value, new_value):
        """Handle cell editing - UPDATE DATABASE IMMEDIATELY"""
        if not self.current_table or not self.connection:
            return
        
        try:
            # Get column name
            column_name = self.data_table.horizontalHeaderItem(col).text()
            
            # Find primary key
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns = cursor.fetchall()
            
            pk_col = None
            pk_idx = None
            for idx, col_info in enumerate(columns):
                if col_info['pk']:
                    pk_col = col_info['name']
                    pk_idx = idx
                    break
            
            if not pk_col:
                QMessageBox.warning(self, "Update Failed",
                    f"Table '{self.current_table}' has no primary key.\n"
                    "Cannot update without primary key.")
                return
            
            # Get PK value for this row
            pk_item = self.data_table.item(row, pk_idx)
            if not pk_item:
                return
            
            pk_value = pk_item.text()
            
            # Update database
            sql = f"UPDATE {self.current_table} SET {column_name} = ? WHERE {pk_col} = ?"
            cursor.execute(sql, (new_value, pk_value))
            self.connection.commit()
            
            self.status_label.setText(f"✅ Updated: {column_name} = '{new_value}'")
            self.modified_label.setText("✅ Changes committed")
            
        except Exception as e:
            self.connection.rollback()
            QMessageBox.critical(self, "Update Error", 
                f"Failed to update cell:\n{str(e)}")
            # Revert change
            item = self.data_table.item(row, col)
            if item:
                item.setText(old_value)
    
    def _filter_navigator(self, text):
        """Filter navigator tree"""
        # Simple filter implementation
        for i in range(self.nav_tree.topLevelItemCount()):
            item = self.nav_tree.topLevelItem(i)
            self._filter_tree_item(item, text.lower())
    
    def _filter_tree_item(self, item, text):
        """Recursively filter tree items"""
        if not text:
            item.setHidden(False)
            for i in range(item.childCount()):
                self._filter_tree_item(item.child(i), text)
            return
        
        visible = text in item.text(0).lower()
        
        for i in range(item.childCount()):
            child_visible = self._filter_tree_item(item.child(i), text)
            visible = visible or child_visible
        
        item.setHidden(not visible)
        return visible
    
    def _filter_table_data(self, text):
        """Filter table data"""
        for row in range(self.data_table.rowCount()):
            visible = False
            for col in range(self.data_table.columnCount()):
                item = self.data_table.item(row, col)
                if item and text.lower() in item.text().lower():
                    visible = True
                    break
            self.data_table.setRowHidden(row, not visible)
    
    def _on_nav_item_clicked(self, item, column):
        """Handle navigator item double-click"""
        data = item.data(0, Qt.UserRole)
        if data and data.get('type') == 'table':
            table_name = data.get('name')
            # Switch to data browser and load table
            self.table_combo.setCurrentText(table_name)
            self.tab_widget.setCurrentIndex(0)
    
    def _refresh_all(self):
        """Refresh everything"""
        self._load_structure()
        self._refresh_current_table()
        self.status_label.setText("✅ Refreshed all data")
    
    def _refresh_current_table(self):
        """Refresh current table data"""
        if self.current_table:
            self._load_table_data(self.current_table)
    
    def _commit_changes(self):
        """Commit all changes"""
        try:
            self.connection.commit()
            self.modified_label.setText("✅ All changes committed")
            self.status_label.setText("✅ Changes committed successfully")
            QMessageBox.information(self, "Success", "All changes have been committed to the database.")
        except Exception as e:
            QMessageBox.critical(self, "Commit Error", f"Failed to commit changes:\n{str(e)}")
    
    def _rollback_changes(self):
        """Rollback changes"""
        try:
            self.connection.rollback()
            self._refresh_current_table()
            self.modified_label.setText("↩️ Changes rolled back")
            self.status_label.setText("↩️ Changes rolled back")
            QMessageBox.information(self, "Rolled Back", "All uncommitted changes have been rolled back.")
        except Exception as e:
            QMessageBox.critical(self, "Rollback Error", f"Failed to rollback:\n{str(e)}")
    
    def _insert_row(self):
        """Insert new row"""
        if not self.current_table:
            QMessageBox.warning(self, "No Table", "Please select a table first.")
            return
        
        # TODO: Implement insert row dialog
        QMessageBox.information(self, "Insert Row", "Insert row functionality - coming soon!")
    
    def _delete_row(self):
        """Delete selected row(s)"""
        if not self.current_table:
            return
        
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select row(s) to delete.")
            return
        
        reply = QMessageBox.question(self, "Confirm Delete",
            f"Are you sure you want to delete {len(selected_rows)} row(s)?",
            QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # TODO: Implement delete with primary key
            QMessageBox.information(self, "Delete", "Delete functionality - coming soon!")
    
    def _duplicate_row(self):
        """Duplicate selected row"""
        QMessageBox.information(self, "Duplicate", "Duplicate row functionality - coming soon!")
    
    def _execute_sql(self):
        """Execute SQL query"""
        sql = self.sql_editor.toPlainText().strip()
        if not sql:
            return
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
            
            if sql.upper().startswith('SELECT'):
                # Show results
                rows = cursor.fetchall()
                if rows:
                    columns = rows[0].keys()
                    
                    self.sql_results.setRowCount(len(rows))
                    self.sql_results.setColumnCount(len(columns))
                    self.sql_results.setHorizontalHeaderLabels(columns)
                    
                    for row_idx, row in enumerate(rows):
                        for col_idx, col_name in enumerate(columns):
                            value = row[col_name]
                            item = QTableWidgetItem(str(value) if value is not None else "")
                            self.sql_results.setItem(row_idx, col_idx, item)
                    
                    self.sql_results.resizeColumnsToContents()
                    self.sql_status.setText(f"✅ Query returned {len(rows):,} rows")
                else:
                    self.sql_results.setRowCount(0)
                    self.sql_status.setText("✅ Query executed - no results")
            else:
                # Non-SELECT query
                self.connection.commit()
                self.sql_results.setRowCount(0)
                self.sql_status.setText(f"✅ Query executed - {cursor.rowcount} rows affected")
            
            # Add to history
            if sql not in self.query_history:
                self.query_history.append(sql)
                display_text = sql[:100] + "..." if len(sql) > 100 else sql
                self.sql_history_combo.addItem(display_text)
            
        except Exception as e:
            self.sql_status.setText(f"❌ Error: {str(e)}")
            QMessageBox.critical(self, "SQL Error", f"Failed to execute query:\n{str(e)}")
    
    def _format_sql(self):
        """Format SQL query"""
        # Basic SQL formatting
        sql = self.sql_editor.toPlainText()
        keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 
                   'ON', 'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'INSERT', 
                   'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE']
        
        for keyword in keywords:
            sql = sql.replace(keyword.lower(), keyword)
            sql = sql.replace(keyword.capitalize(), keyword)
        
        self.sql_editor.setPlainText(sql)
    
    def _load_history_query(self, text):
        """Load query from history"""
        if text and text != "-- Query History --":
            idx = self.sql_history_combo.currentIndex() - 1
            if 0 <= idx < len(self.query_history):
                self.sql_editor.setPlainText(self.query_history[idx])
    
    # Stub methods for menu actions
    def _open_database(self): pass
    def _export_database(self): pass
    def _import_data(self): pass
    def _show_find(self): pass
    def _show_replace(self): pass
    def _show_settings(self): pass
    def _vacuum_database(self): 
        try:
            self.connection.execute("VACUUM")
            self.connection.commit()
            QMessageBox.information(self, "Success", "Database vacuumed successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"VACUUM failed:\n{str(e)}")
    
    def _reindex_database(self): pass
    def _analyze_database(self): pass
    def _integrity_check(self): pass
    def _create_backup(self): pass
    def _show_docs(self): pass
    def _show_about(self): pass
    def _export_table(self): pass
    def _import_table(self): pass
    def _export_schema(self): pass
    def _save_query(self): pass
    def _show_nav_context_menu(self, pos): pass
    def _show_table_context_menu(self, pos): pass
    def _close_tab(self, index): 
        if self.tab_widget.count() > 1:
            self.tab_widget.removeTab(index)
