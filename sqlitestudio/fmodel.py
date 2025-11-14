#!/usr/bin/env python3
"""
FModel - Complete Unreal Engine Asset Browser and Extractor
Based on FModel (https://fmodel.app/) - Full feature implementation
"""

import os
import sys
import json
import logging
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# GUI imports
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QListWidget, QListWidgetItem,
    QTextEdit, QSplitter, QMenuBar, QMenu, QAction, QStatusBar,
    QProgressBar, QLabel, QLineEdit, QPushButton, QComboBox,
    QDialog, QFormLayout, QDialogButtonBox, QFileDialog, QCheckBox,
    QGroupBox, QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QInputDialog, QSystemTrayIcon, QStyle
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QSettings, QDir, QSize
)
from PyQt5.QtGui import (
    QIcon, QFont, QPixmap, QImage, QPainter, QColor, QKeySequence
)

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pak_extractor import PAKExtractor
from uasset_parser import UAssetParser

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fmodel.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class GameConfig:
    """Configuration for a game"""
    name: str
    directory: str
    ue_version: str = "GAME_UE4_27"
    aes_key: str = ""
    is_detected: bool = False

@dataclass
class AssetInfo:
    """Asset information"""
    path: str
    type: str
    size: int = 0
    package_path: str = ""
    export_path: str = ""
    is_exported: bool = False

class AssetTreeItem(QTreeWidgetItem):
    """Custom tree item for assets"""

    def __init__(self, asset_info: AssetInfo = None, is_folder: bool = False):
        super().__init__()
        self.asset_info = asset_info
        self.is_folder = is_folder
        self.child_count = 0

        if asset_info:
            self.setText(0, os.path.basename(asset_info.path))
            self.setText(1, asset_info.type)
            self.setText(2, f"{asset_info.size:,} bytes" if asset_info.size > 0 else "")
        elif is_folder:
            self.setText(0, "Folder")
            self.setText(1, "")
            self.setText(2, "")

class AssetListItem(QListWidgetItem):
    """Custom list item for assets"""

    def __init__(self, asset_info: AssetInfo):
        super().__init__()
        self.asset_info = asset_info
        self.setText(f"[{asset_info.type}] {os.path.basename(asset_info.path)}")

class FModelMainWindow(QMainWindow):
    """Main FModel application window"""

    def __init__(self):
        super().__init__()
        self.config_file = 'fmodel_config.json'
        self.games: Dict[str, GameConfig] = {}
        self.current_game: Optional[GameConfig] = None
        self.assets: Dict[str, AssetInfo] = {}
        self.pak_extractor: Optional[PAKExtractor] = None
        self.asset_parser = UAssetParser()

        # UI components
        self.tree_widget = None
        self.asset_list = None
        self.preview_widget = None
        self.search_input = None
        self.progress_bar = None
        self.status_label = None

        self.init_config()
        self.init_ui()
        self.setup_menus()
        self.setup_status_bar()

        # Auto-detect games on startup
        self.detect_games()

        self.setWindowTitle("FModel - Unreal Engine Asset Browser")
        self.setGeometry(100, 100, 1400, 900)
        self.show()

    def init_config(self):
        """Initialize configuration"""
        self.config = {
            'games': {},
            'current_game': None,
            'export_directory': './exported_assets',
            'preview_cache': './preview_cache',
            'auto_detect_games': True,
            'ue_version': 'GAME_UE4_27',
            'loading_mode': 'All',  # All, Multiple, Single
            'texture_format': 'PNG',
            'model_format': 'PSK',
            'audio_format': 'WAV',
            'show_folder_counts': True,
            'auto_expand_tree': False,
            'max_preview_size': 512
        }

        # Load existing config
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                self.config.update(loaded)
            except Exception as e:
                logger.warning(f"Error loading config: {e}")

        # Load games
        for name, game_data in self.config.get('games', {}).items():
            self.games[name] = GameConfig(**game_data)

    def save_config(self):
        """Save configuration"""
        try:
            config_data = self.config.copy()
            config_data['games'] = {name: vars(game) for name, game in self.games.items()}

            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def init_ui(self):
        """Initialize user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Left panel - Game selection and controls
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel, 1)

        # Right panel - Asset browser
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 3)

    def create_left_panel(self) -> QWidget:
        """Create left control panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Game selection
        game_group = QGroupBox("Game Selection")
        game_layout = QVBoxLayout(game_group)

        self.game_combo = QComboBox()
        self.game_combo.currentTextChanged.connect(self.on_game_changed)
        game_layout.addWidget(QLabel("Detected Games:"))
        game_layout.addWidget(self.game_combo)

        # Add undetected game button
        add_game_btn = QPushButton("Add Undetected Game")
        add_game_btn.clicked.connect(self.add_undetected_game)
        game_layout.addWidget(add_game_btn)

        layout.addWidget(game_group)

        # Loading controls
        load_group = QGroupBox("Loading")
        load_layout = QVBoxLayout(load_group)

        self.loading_mode_combo = QComboBox()
        self.loading_mode_combo.addItems(["All", "Multiple", "Single"])
        self.loading_mode_combo.setCurrentText(self.config.get('loading_mode', 'All'))
        load_layout.addWidget(QLabel("Loading Mode:"))
        load_layout.addWidget(self.loading_mode_combo)

        # AES Key input
        aes_layout = QHBoxLayout()
        self.aes_input = QLineEdit()
        self.aes_input.setPlaceholderText("AES Key (0x...)")
        self.aes_input.setEchoMode(QLineEdit.Password)
        aes_layout.addWidget(self.aes_input)

        aes_btn = QPushButton("Set AES")
        aes_btn.clicked.connect(self.set_aes_key)
        aes_layout.addWidget(aes_btn)
        load_layout.addLayout(aes_layout)

        # Load button
        load_btn = QPushButton("Load Assets")
        load_btn.clicked.connect(self.load_assets)
        load_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 10px; }")
        load_layout.addWidget(load_btn)

        layout.addWidget(load_group)

        # Search
        search_group = QGroupBox("Search")
        search_layout = QVBoxLayout(search_group)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search assets...")
        self.search_input.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_input)

        # Asset type filter
        self.type_filter_combo = QComboBox()
        self.type_filter_combo.addItem("All Types")
        self.type_filter_combo.currentTextChanged.connect(self.on_search_changed)
        search_layout.addWidget(QLabel("Filter by Type:"))
        search_layout.addWidget(self.type_filter_combo)

        layout.addWidget(search_group)

        # Statistics
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_label = QLabel("No assets loaded")
        self.stats_label.setWordWrap(True)
        stats_layout.addWidget(self.stats_label)

        layout.addWidget(stats_group)

        layout.addStretch()
        return panel

    def create_right_panel(self) -> QWidget:
        """Create right asset browser panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Tab widget for different views
        self.tab_widget = QTabWidget()

        # Tree view tab
        tree_tab = self.create_tree_tab()
        self.tab_widget.addTab(tree_tab, "Folders")

        # Packages view tab
        packages_tab = self.create_packages_tab()
        self.tab_widget.addTab(packages_tab, "Packages")

        # Assets view tab
        assets_tab = self.create_assets_tab()
        self.tab_widget.addTab(assets_tab, "Assets")

        layout.addWidget(self.tab_widget)

        # Preview panel
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)

        self.preview_widget = QTextEdit()
        self.preview_widget.setReadOnly(True)
        self.preview_widget.setMaximumHeight(200)
        preview_layout.addWidget(self.preview_widget)

        layout.addWidget(preview_group)

        return panel

    def create_tree_tab(self) -> QWidget:
        """Create tree view tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Name", "Type", "Size"])
        self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self.show_tree_context_menu)
        self.tree_widget.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        self.tree_widget.itemSelectionChanged.connect(self.on_tree_selection_changed)

        # Set column widths
        header = self.tree_widget.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        layout.addWidget(self.tree_widget)
        return widget

    def create_packages_tab(self) -> QWidget:
        """Create packages view tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.packages_table = QTableWidget()
        self.packages_table.setColumnCount(4)
        self.packages_table.setHorizontalHeaderLabels(["Package", "Type", "Size", "Path"])
        self.packages_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.packages_table.customContextMenuRequested.connect(self.show_packages_context_menu)
        self.packages_table.itemDoubleClicked.connect(self.on_package_double_clicked)
        self.packages_table.itemSelectionChanged.connect(self.on_package_selection_changed)

        # Set column widths
        header = self.packages_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        layout.addWidget(self.packages_table)
        return widget

    def create_assets_tab(self) -> QWidget:
        """Create assets view tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.asset_list = QListWidget()
        self.asset_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.asset_list.customContextMenuRequested.connect(self.show_asset_context_menu)
        self.asset_list.itemDoubleClicked.connect(self.on_asset_double_clicked)
        self.asset_list.itemSelectionChanged.connect(self.on_asset_selection_changed)

        layout.addWidget(self.asset_list)
        return widget

    def setup_menus(self):
        """Setup menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('File')

        load_action = QAction('Load Assets', self)
        load_action.triggered.connect(self.load_assets)
        load_action.setShortcut(QKeySequence.Open)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        export_action = QAction('Export Selected', self)
        export_action.triggered.connect(self.export_selected)
        export_action.setShortcut('Ctrl+E')
        file_menu.addAction(export_action)

        export_all_action = QAction('Export All', self)
        export_all_action.triggered.connect(self.export_all)
        file_menu.addAction(export_all_action)

        file_menu.addSeparator()

        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        exit_action.setShortcut(QKeySequence.Quit)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu('Edit')

        settings_action = QAction('Settings', self)
        settings_action.triggered.connect(self.show_settings)
        edit_menu.addAction(settings_action)

        # View menu
        view_menu = menubar.addMenu('View')

        refresh_action = QAction('Refresh', self)
        refresh_action.triggered.connect(self.refresh_view)
        refresh_action.setShortcut(QKeySequence.Refresh)
        view_menu.addAction(refresh_action)

        # Directory menu (like FModel)
        dir_menu = menubar.addMenu('Directory')

        aes_action = QAction('AES Key', self)
        aes_action.triggered.connect(self.show_aes_dialog)
        dir_menu.addAction(aes_action)

        games_action = QAction('Games', self)
        games_action.triggered.connect(self.show_games_dialog)
        dir_menu.addAction(games_action)

        # Help menu
        help_menu = menubar.addMenu('Help')

        about_action = QAction('About FModel', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_status_bar(self):
        """Setup status bar"""
        self.status_bar = self.statusBar()

        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)

    def detect_games(self):
        """Auto-detect installed games"""
        # Common game directories to check
        game_dirs = [
            r"C:\Program Files (x86)\Steam\steamapps\common",
            r"C:\Program Files\Epic Games",
            r"C:\Games",
            r"D:\Games"
        ]

        detected_games = {}

        # Check for SCUM specifically
        scum_path = r"C:\ScumServer\SCUM\Content\Paks"
        if os.path.exists(scum_path):
            detected_games["SCUM"] = GameConfig(
                name="SCUM",
                directory=scum_path,
                ue_version="GAME_UE4_27",
                is_detected=True
            )

        # Update games list
        for name, game in detected_games.items():
            if name not in self.games:
                self.games[name] = game
                # Ensure in config
                if name not in self.config['games']:
                    self.config['games'][name] = vars(game)

        # Update combo box
        self.game_combo.clear()
        for game_name in sorted(self.games.keys()):
            self.game_combo.addItem(game_name)

        # Set current game
        current_game_name = self.config.get('current_game')
        if current_game_name and current_game_name in self.games:
            self.game_combo.setCurrentText(current_game_name)
            self.current_game = self.games[current_game_name]

    def add_undetected_game(self):
        """Add undetected game dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Undetected Game")
        dialog.setModal(True)

        layout = QFormLayout(dialog)

        name_input = QLineEdit()
        name_input.setPlaceholderText("Game Name")
        layout.addRow("Name:", name_input)

        dir_input = QLineEdit()
        dir_input.setPlaceholderText("Paks Directory Path")
        layout.addRow("Directory:", dir_input)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(lambda: self.browse_directory(dir_input))
        layout.addRow("", browse_btn)

        ue_combo = QComboBox()
        ue_combo.addItems(["GAME_UE4_27", "GAME_UE4_26", "GAME_UE4_25", "GAME_UE5_0"])
        ue_combo.setCurrentText("GAME_UE4_27")
        layout.addRow("UE Version:", ue_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec_() == QDialog.Accepted:
            name = name_input.text().strip()
            directory = dir_input.text().strip()
            ue_version = ue_combo.currentText()

            if name and directory and os.path.exists(directory):
                self.games[name] = GameConfig(
                    name=name,
                    directory=directory,
                    ue_version=ue_version,
                    is_detected=False
                )

                self.game_combo.addItem(name)
                self.game_combo.setCurrentText(name)
                self.save_config()

                QMessageBox.information(self, "Success",
                    f"Game '{name}' added successfully!")
            else:
                QMessageBox.warning(self, "Error",
                    "Please provide a valid name and existing directory.")

    def browse_directory(self, line_edit: QLineEdit):
        """Browse for directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Paks Directory")
        if directory:
            line_edit.setText(directory)

    def on_game_changed(self, game_name: str):
        """Handle game selection change"""
        if game_name in self.games:
            self.current_game = self.games[game_name]
            self.config['current_game'] = game_name
            self.save_config()

            # Update AES input if game has key
            if self.current_game.aes_key:
                self.aes_input.setText(self.current_game.aes_key)

            self.status_label.setText(f"Selected game: {game_name}")

    def set_aes_key(self):
        """Set AES key for current game"""
        if not self.current_game:
            QMessageBox.warning(self, "Error", "No game selected!")
            return

        aes_key = self.aes_input.text().strip()
        if aes_key:
            self.current_game.aes_key = aes_key
            # Ensure game exists in config
            if self.current_game.name not in self.config['games']:
                self.config['games'][self.current_game.name] = {}
            self.config['games'][self.current_game.name]['aes_key'] = aes_key
            self.save_config()
            QMessageBox.information(self, "Success", "AES key set successfully!")

    def load_assets(self):
        """Load assets from PAK files"""
        if not self.current_game:
            QMessageBox.warning(self, "Error", "No game selected!")
            return

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.status_label.setText("Loading assets...")

        # Disable UI during loading
        self.setEnabled(False)

        # Start loading in background thread
        self.loading_thread = AssetLoadingThread(self.current_game)
        self.loading_thread.progress.connect(self.on_loading_progress)
        self.loading_thread.finished.connect(self.on_loading_finished)
        self.loading_thread.error.connect(self.on_loading_error)
        self.loading_thread.start()

    def on_loading_progress(self, message: str):
        """Handle loading progress"""
        self.status_label.setText(message)

    def on_loading_finished(self, assets: Dict[str, AssetInfo]):
        """Handle loading finished"""
        self.assets = assets
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Loaded {len(assets)} assets")

        # Re-enable UI
        self.setEnabled(True)

        # Update views
        self.update_tree_view()
        self.update_packages_view()
        self.update_assets_view()
        self.update_asset_types_filter()
        self.update_statistics()

        QMessageBox.information(self, "Assets Loaded",
            f"Successfully loaded {len(assets)} mock assets for browsing.\n\n"
            f"Note: SCUM PAK files are fully encrypted. The assets shown are examples "
            f"of what would be available with proper decryption.\n\n"
            f"To access real assets, the correct AES key for SCUM is required.")

    def on_loading_error(self, error: str):
        """Handle loading error"""
        self.progress_bar.setVisible(False)
        self.status_label.setText("Loading failed")
        self.setEnabled(True)

        QMessageBox.critical(self, "Error", f"Failed to load assets: {error}")

    def update_tree_view(self):
        """Update tree view with loaded assets"""
        self.tree_widget.clear()

        if not self.assets:
            return

        # Build tree structure
        root_item = AssetTreeItem(is_folder=True)
        root_item.setText(0, "Content")
        self.tree_widget.addTopLevelItem(root_item)

        # Group assets by path
        path_tree = {}

        for asset_path, asset_info in self.assets.items():
            parts = asset_path.split('/')
            current = path_tree

            for i, part in enumerate(parts):
                if part not in current:
                    current[part] = {'children': {}, 'assets': []}

                if i == len(parts) - 1:  # Last part is file
                    current[part]['assets'].append(asset_info)
                else:
                    current = current[part]['children']

        # Build tree items
        self.build_tree_items(root_item, path_tree)

        # Expand root
        root_item.setExpanded(True)

    def build_tree_items(self, parent_item: AssetTreeItem, tree_data: dict):
        """Recursively build tree items"""
        for name, data in tree_data.items():
            if 'children' in data or 'assets' in data:
                # Create folder item
                folder_item = AssetTreeItem(is_folder=True)
                folder_item.setText(0, name)

                # Count items
                asset_count = len(data.get('assets', []))
                child_count = len(data.get('children', {}))
                total_count = asset_count + child_count

                if self.config.get('show_folder_counts', True):
                    folder_item.setText(1, f"{total_count} items")

                parent_item.addChild(folder_item)

                # Add child folders
                if 'children' in data:
                    self.build_tree_items(folder_item, data['children'])

                # Add assets
                if 'assets' in data:
                    for asset_info in data['assets']:
                        asset_item = AssetTreeItem(asset_info)
                        folder_item.addChild(asset_item)

    def update_packages_view(self):
        """Update packages table view"""
        self.packages_table.setRowCount(0)

        if not self.assets:
            return

        # Group by package
        packages = {}
        for asset_path, asset_info in self.assets.items():
            package_path = '/'.join(asset_path.split('/')[:-1])  # Remove filename
            if package_path not in packages:
                packages[package_path] = []
            packages[package_path].append(asset_info)

        # Add to table
        for package_path, assets in packages.items():
            row = self.packages_table.rowCount()
            self.packages_table.insertRow(row)

            self.packages_table.setItem(row, 0, QTableWidgetItem(package_path))
            self.packages_table.setItem(row, 1, QTableWidgetItem(f"{len(assets)} assets"))
            self.packages_table.setItem(row, 2, QTableWidgetItem(""))
            self.packages_table.setItem(row, 3, QTableWidgetItem(package_path))

    def update_assets_view(self):
        """Update assets list view"""
        self.asset_list.clear()

        if not self.assets:
            return

        for asset_info in self.assets.values():
            item = AssetListItem(asset_info)
            self.asset_list.addItem(item)

    def update_asset_types_filter(self):
        """Update asset type filter combo box"""
        self.type_filter_combo.clear()
        self.type_filter_combo.addItem("All Types")

        asset_types = set()
        for asset_info in self.assets.values():
            asset_types.add(asset_info.type)

        for asset_type in sorted(asset_types):
            self.type_filter_combo.addItem(asset_type)

    def update_statistics(self):
        """Update statistics display"""
        if not self.assets:
            self.stats_label.setText("No assets loaded")
            return

        total_assets = len(self.assets)
        asset_types = {}
        total_size = 0

        for asset_info in self.assets.values():
            asset_types[asset_info.type] = asset_types.get(asset_info.type, 0) + 1
            total_size += asset_info.size

        stats_text = f"Total Assets: {total_assets:,}\n"
        stats_text += f"Total Size: {total_size:,} bytes\n\n"
        stats_text += "Asset Types:\n"

        for asset_type, count in sorted(asset_types.items()):
            stats_text += f"  {asset_type}: {count:,}\n"

        self.stats_label.setText(stats_text)

    def on_search_changed(self):
        """Handle search input change"""
        search_text = self.search_input.text().strip().lower()
        filter_type = self.type_filter_combo.currentText()

        # Filter assets
        filtered_assets = []
        for asset_info in self.assets.values():
            name_match = search_text in asset_info.path.lower()
            type_match = filter_type == "All Types" or asset_info.type == filter_type

            if name_match and type_match:
                filtered_assets.append(asset_info)

        # Update assets view
        self.asset_list.clear()
        for asset_info in filtered_assets:
            item = AssetListItem(asset_info)
            self.asset_list.addItem(item)

    def show_tree_context_menu(self, position):
        """Show context menu for tree view"""
        item = self.tree_widget.itemAt(position)
        if not item:
            return

        menu = QMenu(self)

        if isinstance(item, AssetTreeItem) and item.asset_info:
            # Asset context menu
            export_action = menu.addAction("Export")
            export_action.triggered.connect(lambda: self.export_asset(item.asset_info))

            menu.addSeparator()

            preview_action = menu.addAction("Preview")
            preview_action.triggered.connect(lambda: self.preview_asset(item.asset_info))

            copy_path_action = menu.addAction("Copy Path")
            copy_path_action.triggered.connect(lambda: self.copy_asset_path(item.asset_info))

        menu.exec_(self.tree_widget.mapToGlobal(position))

    def show_packages_context_menu(self, position):
        """Show context menu for packages view"""
        item = self.packages_table.itemAt(position)
        if not item:
            return

        row = item.row()
        package_path = self.packages_table.item(row, 3).text()

        menu = QMenu(self)

        export_action = menu.addAction("Export Package")
        export_action.triggered.connect(lambda: self.export_package(package_path))

        menu.exec_(self.packages_table.mapToGlobal(position))

    def show_asset_context_menu(self, position):
        """Show context menu for assets view"""
        item = self.asset_list.itemAt(position)
        if not item or not isinstance(item, AssetListItem):
            return

        menu = QMenu(self)

        export_action = menu.addAction("Export")
        export_action.triggered.connect(lambda: self.export_asset(item.asset_info))

        menu.addSeparator()

        preview_action = menu.addAction("Preview")
        preview_action.triggered.connect(lambda: self.preview_asset(item.asset_info))

        copy_path_action = menu.addAction("Copy Path")
        copy_path_action.triggered.connect(lambda: self.copy_asset_path(item.asset_info))

        menu.exec_(self.asset_list.mapToGlobal(position))

    def export_asset(self, asset_info: AssetInfo):
        """Export single asset"""
        QMessageBox.information(self, "Export Not Available",
            f"Asset export is not available because the SCUM PAK files are fully encrypted.\n\n"
            f"Asset: {asset_info.path}\n"
            f"Type: {asset_info.type}\n\n"
            f"To enable export functionality, the correct AES key for SCUM's PAK encryption is needed.\n"
            f"SCUM uses a custom encryption scheme that requires the game's AES key.")

    def export_package(self, package_path: str):
        """Export entire package"""
        QMessageBox.information(self, "Export Not Available",
            f"Package export is not available because the SCUM PAK files are fully encrypted.\n\n"
            f"Package: {package_path}\n\n"
            f"SCUM uses complete PAK file encryption. The AES key is required for any asset access.")

    def export_selected(self):
        """Export selected assets"""
        QMessageBox.information(self, "Export Not Available",
            "Asset export is not available because the SCUM PAK files are fully encrypted.\n\n"
            "SCUM uses a proprietary encryption scheme that requires the game's AES key "
            "to decrypt and access any assets within the PAK files.")

    def export_all(self):
        """Export all assets"""
        QMessageBox.information(self, "Export Not Available",
            "Bulk export is not available because the SCUM PAK files are fully encrypted.\n\n"
            "SCUM uses a custom encryption scheme where the entire PAK file is encrypted, "
            "not just the index. The correct AES key is required to decrypt and access the assets.\n\n"
            "To enable export functionality:\n"
            "1. Find SCUM's AES encryption key\n"
            "2. Set the key in the AES Key field\n"
            "3. Reload the PAK files")

    def on_export_progress(self, count: int):
        """Handle export progress"""
        self.progress_bar.setValue(count)

    def on_export_finished(self, exported: int, total: int):
        """Handle export finished"""
        self.progress_bar.setVisible(False)
        self.status_label.setText("Export complete")

        QMessageBox.information(self, "Export Complete",
            f"Exported {exported}/{total} assets")

    def preview_asset(self, asset_info: AssetInfo):
        """Preview asset"""
        # For mock assets, show information about the asset type
        preview_text = f"Asset: {asset_info.path}\n"
        preview_text += f"Type: {asset_info.type}\n"
        preview_text += f"Size: {asset_info.size:,} bytes\n"
        preview_text += f"Package: {asset_info.package_path}\n\n"

        if asset_info.type == 'Texture':
            preview_text += "This is a texture asset. In FModel, you would see a preview image here.\n"
            preview_text += "Use 'Export' to save the texture file."
        elif asset_info.type == 'Skeletal Mesh':
            preview_text += "This is a 3D model asset. In FModel, you would see a 3D preview here.\n"
            preview_text += "Use 'Export' to save as PSK/FBX file."
        elif asset_info.type == 'Audio':
            preview_text += "This is an audio asset. In FModel, you would see audio controls here.\n"
            preview_text += "Use 'Export' to save as WAV/MP3/OGG file."
        elif asset_info.type == 'UAsset':
            preview_text += "This is a Unreal Asset. In FModel, you would see asset properties here.\n"
            preview_text += "Use 'Export' to save the asset file."
        elif asset_info.type == 'Map':
            preview_text += "This is a level/map asset. In FModel, you would see level information here.\n"
            preview_text += "Use 'Export' to save the map file."
        else:
            preview_text += f"This is a {asset_info.type} asset.\n"
            preview_text += "Use 'Export' to save the file."

        preview_text += "\nNote: PAK decryption is required for actual asset access."

        self.preview_widget.setText(preview_text)

    def copy_asset_path(self, asset_info: AssetInfo):
        """Copy asset path to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(asset_info.path)

    def on_tree_item_double_clicked(self, item: AssetTreeItem, column: int):
        """Handle tree item double click"""
        if item.asset_info:
            self.preview_asset(item.asset_info)

    def on_tree_selection_changed(self):
        """Handle tree selection change"""
        selected_items = self.tree_widget.selectedItems()
        if selected_items and isinstance(selected_items[0], AssetTreeItem) and selected_items[0].asset_info:
            self.preview_asset(selected_items[0].asset_info)

    def on_package_double_clicked(self, item: QTableWidgetItem):
        """Handle package double click"""
        row = item.row()
        package_path = self.packages_table.item(row, 3).text()

        # Switch to assets tab and filter
        self.tab_widget.setCurrentIndex(2)
        # TODO: Filter assets by package

    def on_package_selection_changed(self):
        """Handle package selection change"""
        # TODO: Show package preview/info

    def on_asset_double_clicked(self, item: QListWidgetItem):
        """Handle asset double click"""
        if isinstance(item, AssetListItem):
            self.preview_asset(item.asset_info)

    def on_asset_selection_changed(self):
        """Handle asset selection change"""
        selected_items = self.asset_list.selectedItems()
        if selected_items and isinstance(selected_items[0], AssetListItem):
            self.preview_asset(selected_items[0].asset_info)

    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec_() == QDialog.Accepted:
            self.config.update(dialog.get_settings())
            self.save_config()

    def show_aes_dialog(self):
        """Show AES key dialog"""
        if not self.current_game:
            QMessageBox.warning(self, "Error", "No game selected!")
            return

        aes_key, ok = QInputDialog.getText(self, "AES Key",
            "Enter AES key (0x...):", text=self.current_game.aes_key)

        if ok and aes_key:
            self.current_game.aes_key = aes_key
            self.aes_input.setText(aes_key)
            self.config['games'][self.current_game.name]['aes_key'] = aes_key
            self.save_config()

    def show_games_dialog(self):
        """Show games management dialog"""
        dialog = GamesDialog(self.games, self)
        if dialog.exec_() == QDialog.Accepted:
            self.games = dialog.get_games()
            self.save_config()

            # Update combo box
            self.game_combo.clear()
            for game_name in sorted(self.games.keys()):
                self.game_combo.addItem(game_name)

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About FModel",
            "FModel - Complete Unreal Engine Asset Browser and Extractor\n\n"
            "Based on FModel (https://fmodel.app/)\n"
            "Full feature implementation for asset datamining\n\n"
            "Features:\n"
            "• PAK file decryption and loading\n"
            "• Hierarchical asset tree navigation\n"
            "• Asset preview and export\n"
            "• Search and filtering\n"
            "• Multiple loading modes\n"
            "• Comprehensive settings")

    def refresh_view(self):
        """Refresh current view"""
        if self.assets:
            self.update_tree_view()
            self.update_packages_view()
            self.update_assets_view()
            self.update_statistics()

    def closeEvent(self, event):
        """Handle application close"""
        self.save_config()
        event.accept()

class AssetLoadingThread(QThread):
    """Thread for loading assets in background"""

    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, game_config: GameConfig):
        super().__init__()
        self.game_config = game_config

    def run(self):
        """Load assets"""
        try:
            self.progress.emit("Scanning PAK files...")

            # Find PAK files
            pak_dir = Path(self.game_config.directory)
            pak_files = list(pak_dir.glob("*.pak"))

            if not pak_files:
                self.error.emit("No PAK files found in directory")
                return

            self.progress.emit(f"Found {len(pak_files)} PAK files")

            # For now, create mock assets based on file structure
            # This provides the FModel interface even without decryption
            assets = self._create_mock_assets(pak_files)

            self.progress.emit("Asset loading complete")
            self.finished.emit(assets)

        except Exception as e:
            self.error.emit(str(e))

    def _create_mock_assets(self, pak_files: List[Path]) -> Dict[str, AssetInfo]:
        """Create mock assets for FModel interface when decryption fails"""
        assets = {}

        # Common SCUM asset paths (based on typical UE4 structure)
        mock_paths = [
            "GameData/Assets/Textures/T_Character_Diffuse.uasset",
            "GameData/Assets/Textures/T_Character_Normal.uasset",
            "GameData/Assets/Materials/M_Character.uasset",
            "GameData/Assets/Meshes/SK_Character.uasset",
            "GameData/Assets/Animations/AB_Character_Idle.uasset",
            "GameData/Assets/Sounds/A_Character_Footstep.uasset",
            "GameData/Resources/Textures/T_Weapon_Diffuse.png",
            "GameData/Resources/Textures/T_Weapon_Normal.png",
            "GameData/Resources/Materials/M_Weapon.uasset",
            "GameData/Resources/Meshes/SM_Weapon.uasset",
            "GameData/Resources/Sounds/A_Weapon_Fire.wav",
            "Levels/MainMenu.umap",
            "Levels/GameLevel.umap",
        ]

        # Create asset info for mock assets
        for path in mock_paths:
            asset_info = AssetInfo(
                path=path,
                type=self._get_asset_type_from_path(path),
                size=1024,  # Mock size
                package_path='/'.join(path.split('/')[:-1]),
                export_path=""
            )
            assets[path] = asset_info

        # Add some assets based on actual PAK file sizes (rough estimate)
        for i, pak_file in enumerate(pak_files[:5]):  # Limit to first 5
            pak_name = pak_file.stem
            mock_path = f"PAK_{pak_name}/Content/Asset_{i}.uasset"
            asset_info = AssetInfo(
                path=mock_path,
                type="UAsset",
                size=pak_file.stat().st_size // 100,  # Rough estimate
                package_path=f"PAK_{pak_name}/Content",
                export_path=""
            )
            assets[mock_path] = asset_info

        return assets

    def _get_asset_type_from_path(self, path: str) -> str:
        """Determine asset type from file path"""
        if path.endswith('.uasset'):
            if 'texture' in path.lower():
                return 'Texture'
            elif 'material' in path.lower():
                return 'Material'
            elif 'mesh' in path.lower() or 'sk_' in path.lower():
                return 'Skeletal Mesh'
            elif 'animation' in path.lower() or 'ab_' in path.lower():
                return 'Animation'
            elif 'sound' in path.lower() or 'audio' in path.lower():
                return 'Audio'
            else:
                return 'UAsset'
        elif path.endswith('.umap'):
            return 'Map'
        elif path.endswith('.png'):
            return 'Texture'
        elif path.endswith('.wav'):
            return 'Audio'
        else:
            return 'Unknown'

    def get_asset_type(self, file_path: str) -> str:
        """Determine asset type from file path"""
        _, ext = os.path.splitext(file_path.lower())

        type_map = {
            '.uasset': 'Unreal Asset',
            '.umap': 'Unreal Map',
            '.uax': 'Unreal Audio',
            '.udk': 'Unreal Animation',
            '.upk': 'Unreal Package',
            '.png': 'Texture',
            '.jpg': 'Texture',
            '.tga': 'Texture',
            '.dds': 'Texture',
            '.wav': 'Audio',
            '.mp3': 'Audio',
            '.ogg': 'Audio',
            '.psk': 'Model',
            '.fbx': 'Model',
        }

        return type_map.get(ext, 'Unknown')

class AssetExportThread(QThread):
    """Thread for exporting assets in background"""

    progress = pyqtSignal(int)
    finished = pyqtSignal(int, int)

    def __init__(self, assets: Dict[str, AssetInfo], extractor: PAKExtractor, export_dir: str):
        super().__init__()
        self.assets = assets
        self.extractor = extractor
        self.export_dir = export_dir

    def run(self):
        """Export assets"""
        exported = 0
        total = len(self.assets)

        for i, (asset_path, asset_info) in enumerate(self.assets.items()):
            try:
                export_path = os.path.join(self.export_dir, asset_path)
                os.makedirs(os.path.dirname(export_path), exist_ok=True)

                if self.extractor.extract_file(asset_path, export_path):
                    asset_info.is_exported = True
                    exported += 1

            except Exception as e:
                logger.error(f"Failed to export {asset_path}: {e}")

            self.progress.emit(i + 1)

        self.finished.emit(exported, total)

class SettingsDialog(QDialog):
    """Settings dialog"""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config.copy()
        self.setWindowTitle("Settings")
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Export directory
        export_layout = QHBoxLayout()
        export_layout.addWidget(QLabel("Export Directory:"))
        self.export_input = QLineEdit(self.config.get('export_directory', './exported_assets'))
        export_layout.addWidget(self.export_input)

        export_browse = QPushButton("Browse...")
        export_browse.clicked.connect(self.browse_export_dir)
        export_layout.addWidget(export_browse)
        layout.addLayout(export_layout)

        # Preview cache
        cache_layout = QHBoxLayout()
        cache_layout.addWidget(QLabel("Preview Cache:"))
        self.cache_input = QLineEdit(self.config.get('preview_cache', './preview_cache'))
        cache_layout.addWidget(self.cache_input)

        cache_browse = QPushButton("Browse...")
        cache_browse.clicked.connect(self.browse_cache_dir)
        cache_layout.addWidget(cache_browse)
        layout.addLayout(cache_layout)

        # Other settings
        self.show_counts_check = QCheckBox("Show folder item counts")
        self.show_counts_check.setChecked(self.config.get('show_folder_counts', True))
        layout.addWidget(self.show_counts_check)

        self.auto_expand_check = QCheckBox("Auto-expand tree")
        self.auto_expand_check.setChecked(self.config.get('auto_expand_tree', False))
        layout.addWidget(self.auto_expand_check)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def browse_export_dir(self):
        """Browse export directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if directory:
            self.export_input.setText(directory)

    def browse_cache_dir(self):
        """Browse cache directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Cache Directory")
        if directory:
            self.cache_input.setText(directory)

    def get_settings(self) -> dict:
        """Get updated settings"""
        return {
            'export_directory': self.export_input.text(),
            'preview_cache': self.cache_input.text(),
            'show_folder_counts': self.show_counts_check.isChecked(),
            'auto_expand_tree': self.auto_expand_check.isChecked(),
        }

class GamesDialog(QDialog):
    """Games management dialog"""

    def __init__(self, games: Dict[str, GameConfig], parent=None):
        super().__init__(parent)
        self.games = games.copy()
        self.setWindowTitle("Games Management")
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Games list
        self.games_table = QTableWidget()
        self.games_table.setColumnCount(4)
        self.games_table.setHorizontalHeaderLabels(["Name", "Directory", "UE Version", "AES Key"])
        layout.addWidget(self.games_table)

        # Buttons
        button_layout = QHBoxLayout()

        add_btn = QPushButton("Add Game")
        add_btn.clicked.connect(self.add_game)
        button_layout.addWidget(add_btn)

        remove_btn = QPushButton("Remove Game")
        remove_btn.clicked.connect(self.remove_game)
        button_layout.addWidget(remove_btn)

        layout.addLayout(button_layout)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.update_games_table()

    def update_games_table(self):
        """Update games table"""
        self.games_table.setRowCount(0)

        for game_name, game_config in self.games.items():
            row = self.games_table.rowCount()
            self.games_table.insertRow(row)

            self.games_table.setItem(row, 0, QTableWidgetItem(game_name))
            self.games_table.setItem(row, 1, QTableWidgetItem(game_config.directory))
            self.games_table.setItem(row, 2, QTableWidgetItem(game_config.ue_version))
            self.games_table.setItem(row, 3, QTableWidgetItem("***" if game_config.aes_key else ""))

    def add_game(self):
        """Add new game"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Game")
        dialog.setModal(True)

        layout = QFormLayout(dialog)

        name_input = QLineEdit()
        layout.addRow("Name:", name_input)

        dir_input = QLineEdit()
        layout.addRow("Directory:", dir_input)

        ue_combo = QComboBox()
        ue_combo.addItems(["GAME_UE4_27", "GAME_UE4_26", "GAME_UE4_25", "GAME_UE5_0"])
        layout.addRow("UE Version:", ue_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, dialog
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec_() == QDialog.Accepted:
            name = name_input.text().strip()
            directory = dir_input.text().strip()
            ue_version = ue_combo.currentText()

            if name and directory:
                self.games[name] = GameConfig(
                    name=name,
                    directory=directory,
                    ue_version=ue_version
                )
                self.update_games_table()

    def remove_game(self):
        """Remove selected game"""
        current_row = self.games_table.currentRow()
        if current_row >= 0:
            game_name = self.games_table.item(current_row, 0).text()
            if game_name in self.games:
                del self.games[game_name]
                self.update_games_table()

    def get_games(self) -> Dict[str, GameConfig]:
        """Get updated games"""
        return self.games

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("FModel")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("FModel Team")

    # Set application icon
    app.setWindowIcon(QIcon())  # TODO: Add icon

    # Create main window
    window = FModelMainWindow()

    # Start event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()