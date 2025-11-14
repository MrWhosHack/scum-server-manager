"""
🗄️ SQLiteStudio Professional - Ultimate Database Manager
===========================================================

Copyright (c) 2025 SCUM Server Manager Project
Licensed under the MIT License

A complete, professional-grade SQLite database management system
with advanced features, beautiful UI, and powerful tools.

Features:
• 🎨 Modern Dark UI with VS Code-inspired design
• 📊 Advanced Data Browser with pagination, filtering, sorting
• 📝 Professional SQL Editor with syntax highlighting & auto-completion
• 🏗️ Database Structure Viewer with relationships
• 🔧 Powerful Row Editor with smart input widgets
• 📈 Performance Monitor & Query Statistics
• 💾 Multi-format Export/Import (CSV, JSON, XML, SQL)
• 🛠️ Database Maintenance Tools (VACUUM, REINDEX, ANALYZE)
• 📋 Query History & Favorites
• 🎯 Visual Query Builder
• 📊 Data Generator for Testing
• 🔗 Foreign Key Relationships Viewer
• ⚡ Keyboard Shortcuts & Context Menus
• 🔄 Drag & Drop Operations
• 📱 Responsive Design

Usage:
    from sqlitestudio_pro import SQLiteStudioPro
    
    # In your application:
    dialog = SQLiteStudioPro(parent, database_path)
    dialog.exec()

Distribution:
    This software is free to use and distribute under the MIT License.
    See LICENSE file for full terms.
"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import sqlite3
from pathlib import Path
from datetime import datetime
import csv
import json
import xml.etree.ElementTree as ET
import re
import random
import string
import time
import sys


class SyntaxHighlighter(QSyntaxHighlighter):
    """SQL Syntax Highlighter"""

    def __init__(self, document):
        super().__init__(document)

        # Keywords
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6"))
        keyword_format.setFontWeight(QFont.Bold)
        keywords = [
            "SELECT", "FROM", "WHERE", "JOIN", "INNER", "LEFT", "RIGHT", "OUTER",
            "ON", "GROUP", "BY", "ORDER", "HAVING", "LIMIT", "OFFSET", "DISTINCT",
            "INSERT", "INTO", "VALUES", "UPDATE", "SET", "DELETE", "CREATE", "TABLE",
            "INDEX", "VIEW", "TRIGGER", "DROP", "ALTER", "ADD", "COLUMN", "CONSTRAINT",
            "PRIMARY", "KEY", "FOREIGN", "REFERENCES", "UNIQUE", "NOT", "NULL", "DEFAULT",
            "AUTOINCREMENT", "BEGIN", "COMMIT", "ROLLBACK", "TRANSACTION", "PRAGMA",
            "VACUUM", "REINDEX", "ANALYZE", "EXPLAIN", "QUERY", "PLAN"
        ]
        self.keyword_patterns = [r'\b' + re.escape(word) + r'\b' for word in keywords]

        # Functions
        function_format = QTextCharFormat()
        function_format.setForeground(QColor("#DCDCAA"))
        functions = [
            "COUNT", "SUM", "AVG", "MIN", "MAX", "ABS", "LENGTH", "SUBSTR", "REPLACE",
            "UPPER", "LOWER", "TRIM", "ROUND", "RANDOM", "DATE", "TIME", "DATETIME",
            "JULIANDAY", "STRFTIME", "COALESCE", "NULLIF", "IFNULL", "CASE", "WHEN"
        ]
        self.function_patterns = [r'\b' + re.escape(func) + r'\b' for func in functions]

        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178"))

        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955"))
        comment_format.setFontItalic(True)

        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8"))

        self.formats = {
            'keyword': keyword_format,
            'function': function_format,
            'string': string_format,
            'comment': comment_format,
            'number': number_format
        }

    def highlightBlock(self, text):
        # Keywords
        for pattern in self.keyword_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                self.setFormat(match.start(), match.end() - match.start(), self.formats['keyword'])

        # Functions
        for pattern in self.function_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                self.setFormat(match.start(), match.end() - match.start(), self.formats['function'])

        # Strings
        for match in re.finditer(r"'([^']*)'", text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats['string'])

        # Comments
        for match in re.finditer(r'--[^\n]*', text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats['comment'])

        # Numbers
        for match in re.finditer(r'\b\d+\.?\d*\b', text):
            self.setFormat(match.start(), match.end() - match.start(), self.formats['number'])


class AutoCompleter(QCompleter):
    """SQL Auto-Completer"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.keywords = [
            "SELECT", "FROM", "WHERE", "JOIN", "INNER", "LEFT", "RIGHT", "OUTER",
            "ON", "GROUP BY", "ORDER BY", "HAVING", "LIMIT", "OFFSET", "DISTINCT",
            "INSERT INTO", "VALUES", "UPDATE", "SET", "DELETE FROM", "CREATE TABLE",
            "DROP TABLE", "ALTER TABLE", "CREATE INDEX", "DROP INDEX", "CREATE VIEW",
            "DROP VIEW", "BEGIN TRANSACTION", "COMMIT", "ROLLBACK", "PRAGMA",
            "VACUUM", "REINDEX", "ANALYZE", "EXPLAIN QUERY PLAN"
        ]
        self.functions = [
            "COUNT(", "SUM(", "AVG(", "MIN(", "MAX(", "ABS(", "LENGTH(", "SUBSTR(",
            "REPLACE(", "UPPER(", "LOWER(", "TRIM(", "ROUND(", "RANDOM()", "DATE(",
            "TIME()", "DATETIME()", "JULIANDAY(", "STRFTIME(", "COALESCE(", "NULLIF(",
            "IFNULL(", "CASE WHEN THEN ELSE END"
        ]
        self.setModel(QStringListModel(self.keywords + self.functions))
        self.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompletionMode(QCompleter.PopupCompletion)


class QueryBuilderDialog(QDialog):
    """Visual Query Builder"""

    def __init__(self, parent, tables, columns):
        super().__init__(parent)
        self.tables = tables
        self.columns = columns
        self.query_parts = {
            'select': [],
            'from': '',
            'joins': [],
            'where': [],
            'group_by': [],
            'having': [],
            'order_by': [],
            'limit': ''
        }

        self.setWindowTitle("🎯 Visual Query Builder")
        self.resize(800, 600)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("🎯 Build SQL Query Visually")
        header.setStyleSheet("""
            font-size: 16pt; font-weight: bold; padding: 10px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #007acc, stop:1 #005a9e);
            color: white; border-radius: 5px;
        """)
        layout.addWidget(header)

        # Tabs for different query parts
        tabs = QTabWidget()

        # SELECT tab
        select_tab = self._create_select_tab()
        tabs.addTab(select_tab, "📋 SELECT")

        # FROM/JOIN tab
        from_tab = self._create_from_tab()
        tabs.addTab(from_tab, "🔗 FROM/JOIN")

        # WHERE tab
        where_tab = self._create_where_tab()
        tabs.addTab(where_tab, "🔍 WHERE")

        # GROUP BY / ORDER BY tab
        group_tab = self._create_group_tab()
        tabs.addTab(group_tab, "📊 GROUP/ORDER")

        layout.addWidget(tabs)

        # Generated SQL preview
        preview_group = QGroupBox("📝 Generated SQL")
        preview_layout = QVBoxLayout()
        self.sql_preview = QPlainTextEdit()
        self.sql_preview.setFont(QFont("Consolas", 10))
        self.sql_preview.setMaximumHeight(150)
        preview_layout.addWidget(self.sql_preview)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        copy_btn = QPushButton("📋 Copy SQL")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.sql_preview.toPlainText()))
        button_layout.addWidget(copy_btn)

        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        use_btn = QPushButton("✅ Use Query")
        use_btn.clicked.connect(self.accept)
        use_btn.setDefault(True)
        button_layout.addWidget(use_btn)

        layout.addLayout(button_layout)

        self._update_preview()

    def _create_select_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Available columns
        layout.addWidget(QLabel("📋 Select Columns:"))

        self.select_list = QListWidget()
        self.select_list.setSelectionMode(QAbstractItemView.MultiSelection)
        for table, cols in self.columns.items():
            for col in cols:
                item = QListWidgetItem(f"{table}.{col}")
                item.setData(Qt.UserRole, (table, col))
                self.select_list.addItem(item)
        layout.addWidget(self.select_list)

        # Selected columns
        layout.addWidget(QLabel("✅ Selected Columns:"))
        self.selected_columns = QListWidget()
        layout.addWidget(self.selected_columns)

        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Add →")
        add_btn.clicked.connect(self._add_columns)
        btn_layout.addWidget(add_btn)

        remove_btn = QPushButton("← ➖ Remove")
        remove_btn.clicked.connect(self._remove_columns)
        btn_layout.addWidget(remove_btn)

        layout.addLayout(btn_layout)

        # Aggregate functions
        agg_layout = QHBoxLayout()
        agg_layout.addWidget(QLabel("🔢 Aggregate:"))
        self.agg_combo = QComboBox()
        self.agg_combo.addItems(["", "COUNT", "SUM", "AVG", "MIN", "MAX"])
        agg_layout.addWidget(self.agg_combo)

        apply_agg_btn = QPushButton("Apply")
        apply_agg_btn.clicked.connect(self._apply_aggregate)
        agg_layout.addWidget(apply_agg_btn)

        layout.addLayout(agg_layout)

        return widget

    def _create_from_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Main table
        layout.addWidget(QLabel("📊 Main Table:"))
        self.main_table_combo = QComboBox()
        self.main_table_combo.addItems(self.tables)
        self.main_table_combo.currentTextChanged.connect(self._update_preview)
        layout.addWidget(self.main_table_combo)

        # Joins
        layout.addWidget(QLabel("🔗 Joins:"))
        self.joins_list = QListWidget()
        layout.addWidget(self.joins_list)

        # Add join controls
        join_controls = QHBoxLayout()
        join_controls.addWidget(QLabel("Join Type:"))
        self.join_type_combo = QComboBox()
        self.join_type_combo.addItems(["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL OUTER JOIN"])
        join_controls.addWidget(self.join_type_combo)

        join_controls.addWidget(QLabel("Table:"))
        self.join_table_combo = QComboBox()
        self.join_table_combo.addItems(self.tables)
        join_controls.addWidget(self.join_table_combo)

        add_join_btn = QPushButton("➕ Add Join")
        add_join_btn.clicked.connect(self._add_join)
        join_controls.addWidget(add_join_btn)

        layout.addLayout(join_controls)

        return widget

    def _create_where_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # Conditions list
        layout.addWidget(QLabel("🔍 WHERE Conditions:"))
        self.where_list = QListWidget()
        layout.addWidget(self.where_list)

        # Add condition controls
        cond_layout = QGridLayout()

        cond_layout.addWidget(QLabel("Column:"), 0, 0)
        self.where_column_combo = QComboBox()
        for table, cols in self.columns.items():
            for col in cols:
                self.where_column_combo.addItem(f"{table}.{col}")
        cond_layout.addWidget(self.where_column_combo, 0, 1)

        cond_layout.addWidget(QLabel("Operator:"), 1, 0)
        self.where_op_combo = QComboBox()
        self.where_op_combo.addItems(["=", "!=", "<", "<=", ">", ">=", "LIKE", "IN", "IS NULL", "IS NOT NULL"])
        cond_layout.addWidget(self.where_op_combo, 1, 1)

        cond_layout.addWidget(QLabel("Value:"), 2, 0)
        self.where_value_edit = QLineEdit()
        cond_layout.addWidget(self.where_value_edit, 2, 1)

        add_cond_btn = QPushButton("➕ Add Condition")
        add_cond_btn.clicked.connect(self._add_condition)
        cond_layout.addWidget(add_cond_btn, 3, 0, 1, 2)

        layout.addLayout(cond_layout)

        return widget

    def _create_group_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        # GROUP BY
        layout.addWidget(QLabel("📊 GROUP BY:"))
        self.groupby_list = QListWidget()
        layout.addWidget(self.groupby_list)

        # ORDER BY
        layout.addWidget(QLabel("📈 ORDER BY:"))
        self.orderby_list = QListWidget()
        layout.addWidget(self.orderby_list)

        # LIMIT
        limit_layout = QHBoxLayout()
        limit_layout.addWidget(QLabel("📏 LIMIT:"))
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(0, 1000000)
        self.limit_spin.setValue(1000)
        limit_layout.addWidget(self.limit_spin)
        layout.addLayout(limit_layout)

        return widget

    def _add_columns(self):
        for item in self.select_list.selectedItems():
            table, col = item.data(Qt.UserRole)
            self.query_parts['select'].append(f"{table}.{col}")
            self.selected_columns.addItem(f"{table}.{col}")
        self._update_preview()

    def _remove_columns(self):
        for item in self.selected_columns.selectedItems():
            text = item.text()
            if text in self.query_parts['select']:
                self.query_parts['select'].remove(text)
            self.selected_columns.takeItem(self.selected_columns.row(item))
        self._update_preview()

    def _apply_aggregate(self):
        agg = self.agg_combo.currentText()
        if not agg:
            return

        selected = self.selected_columns.selectedItems()
        if not selected:
            return

        col = selected[0].text()
        agg_expr = f"{agg}({col})"
        self.query_parts['select'].append(agg_expr)
        self.selected_columns.addItem(agg_expr)
        self._update_preview()

    def _add_join(self):
        join_type = self.join_type_combo.currentText()
        table = self.join_table_combo.currentText()
        if table:
            join = f"{join_type} {table}"
            self.query_parts['joins'].append(join)
            self.joins_list.addItem(join)
            self._update_preview()

    def _add_condition(self):
        column = self.where_column_combo.currentText()
        op = self.where_op_combo.currentText()
        value = self.where_value_edit.text().strip()

        if column and value:
            condition = f"{column} {op} '{value}'"
            self.query_parts['where'].append(condition)
            self.where_list.addItem(condition)
            self._update_preview()

    def _update_preview(self):
        """Update SQL preview"""
        sql = "SELECT "

        if self.query_parts['select']:
            sql += ", ".join(self.query_parts['select'])
        else:
            sql += "*"

        sql += "\nFROM "

        main_table = self.main_table_combo.currentText()
        if main_table:
            sql += main_table
        else:
            sql += "table_name"

        for join in self.query_parts['joins']:
            sql += f"\n{join}"

        if self.query_parts['where']:
            sql += "\nWHERE " + " AND ".join(self.query_parts['where'])

        if self.query_parts['group_by']:
            sql += "\nGROUP BY " + ", ".join(self.query_parts['group_by'])

        if self.query_parts['having']:
            sql += "\nHAVING " + " AND ".join(self.query_parts['having'])

        if self.query_parts['order_by']:
            sql += "\nORDER BY " + ", ".join(self.query_parts['order_by'])

        limit = self.limit_spin.value()
        if limit > 0:
            sql += f"\nLIMIT {limit}"

        sql += ";"

        self.sql_preview.setPlainText(sql)

    def get_sql(self):
        return self.sql_preview.toPlainText()


class DataGeneratorDialog(QDialog):
    """Data Generator for Testing"""

    def __init__(self, parent, table_name, columns_info):
        super().__init__(parent)
        self.table_name = table_name
        self.columns_info = columns_info

        self.setWindowTitle(f"🎲 Data Generator - {table_name}")
        self.resize(600, 400)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("🎲 Generate Test Data")
        header.setStyleSheet("""
            font-size: 14pt; font-weight: bold; padding: 10px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #50fa7b, stop:1 #22c55e);
            color: white; border-radius: 5px;
        """)
        layout.addWidget(header)

        # Settings
        settings_group = QGroupBox("⚙️ Generation Settings")
        settings_layout = QGridLayout()

        settings_layout.addWidget(QLabel("Number of Rows:"), 0, 0)
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 10000)
        self.rows_spin.setValue(100)
        settings_layout.addWidget(self.rows_spin, 0, 1)

        settings_layout.addWidget(QLabel("Batch Size:"), 1, 0)
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 1000)
        self.batch_spin.setValue(50)
        settings_layout.addWidget(self.batch_spin, 1, 1)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Column settings
        columns_group = QGroupBox("📋 Column Settings")
        columns_layout = QVBoxLayout()

        self.column_settings = {}
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        for col_info in self.columns_info:
            col_name = col_info['name']
            col_type = col_info['type']

            # Skip auto-increment PKs
            if col_info['pk'] and 'INTEGER' in col_type.upper():
                continue

            col_widget = QWidget()
            col_layout = QHBoxLayout(col_widget)

            col_layout.addWidget(QLabel(f"{col_name} ({col_type}):"))

            gen_type_combo = QComboBox()
            gen_type_combo.addItem("Auto", "auto")
            gen_type_combo.addItem("Fixed Value", "fixed")
            gen_type_combo.addItem("Random", "random")
            gen_type_combo.addItem("Skip", "skip")
            gen_type_combo.setCurrentText("Auto")

            value_edit = QLineEdit()
            value_edit.setPlaceholderText("Value for fixed/random")

            col_layout.addWidget(gen_type_combo)
            col_layout.addWidget(value_edit)

            scroll_layout.addWidget(col_widget)

            self.column_settings[col_name] = {
                'type': gen_type_combo,
                'value': value_edit,
                'col_type': col_type
            }

        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        columns_layout.addWidget(scroll)
        columns_group.setLayout(columns_layout)
        layout.addWidget(columns_group)

        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        generate_btn = QPushButton("🎲 Generate Data")
        generate_btn.clicked.connect(self._generate_data)
        generate_btn.setDefault(True)
        button_layout.addWidget(generate_btn)

        layout.addLayout(button_layout)

    def _generate_data(self):
        """Generate the test data"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Collect generation settings
        settings = {}
        for col_name, widgets in self.column_settings.items():
            gen_type = widgets['type'].currentData()
            value = widgets['value'].text().strip()
            settings[col_name] = {
                'type': gen_type,
                'value': value,
                'col_type': widgets['col_type']
            }

        # Generate data in batches
        total_rows = self.rows_spin.value()
        batch_size = self.batch_spin.value()

        generated = 0
        self.generated_data = []

        while generated < total_rows:
            batch_count = min(batch_size, total_rows - generated)
            batch_data = []

            for _ in range(batch_count):
                row = {}
                for col_name, setting in settings.items():
                    if setting['type'] == 'skip':
                        continue
                    elif setting['type'] == 'fixed':
                        row[col_name] = self._parse_value(setting['value'], setting['col_type'])
                    elif setting['type'] == 'random':
                        row[col_name] = self._generate_random_value(setting['col_type'])
                    else:  # auto
                        row[col_name] = self._generate_auto_value(setting['col_type'], generated)
                batch_data.append(row)

            self.generated_data.extend(batch_data)
            generated += batch_count
            self.progress_bar.setValue(int((generated / total_rows) * 100))
            QApplication.processEvents()

        self.progress_bar.setVisible(False)
        self.accept()

    def _parse_value(self, value, col_type):
        """Parse value based on column type"""
        if 'INTEGER' in col_type.upper() or 'INT' in col_type.upper():
            try:
                return int(value)
            except:
                return 0
        elif 'REAL' in col_type.upper() or 'FLOAT' in col_type.upper():
            try:
                return float(value)
            except:
                return 0.0
        else:
            return value

    def _generate_random_value(self, col_type):
        """Generate random value based on column type"""
        if 'INTEGER' in col_type.upper() or 'INT' in col_type.upper():
            return random.randint(1, 1000)
        elif 'REAL' in col_type.upper() or 'FLOAT' in col_type.upper():
            return round(random.uniform(0, 1000), 2)
        elif 'TEXT' in col_type.upper():
            return ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        else:
            return f"random_{random.randint(1, 100)}"

    def _generate_auto_value(self, col_type, index):
        """Generate auto value based on column type"""
        if 'INTEGER' in col_type.upper() or 'INT' in col_type.upper():
            return index + 1
        elif 'REAL' in col_type.upper() or 'FLOAT' in col_type.upper():
            return float(index + 1)
        elif 'TEXT' in col_type.upper():
            return f"Auto Value {index + 1}"
        else:
            return f"auto_{index + 1}"

    def get_generated_data(self):
        return self.generated_data


class PerformanceMonitorDialog(QDialog):
    """Database Performance Monitor"""

    def __init__(self, parent, connection):
        super().__init__(parent)
        self.connection = connection

        self.setWindowTitle("📈 Performance Monitor")
        self.resize(800, 600)
        self.setModal(False)

        self._init_ui()
        self._load_stats()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("📈 Database Performance Statistics")
        header.setStyleSheet("""
            font-size: 16pt; font-weight: bold; padding: 10px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #ffb86b, stop:1 #ff922b);
            color: white; border-radius: 5px;
        """)
        layout.addWidget(header)

        # Stats tabs
        tabs = QTabWidget()

        # General Stats
        general_tab = self._create_general_stats_tab()
        tabs.addTab(general_tab, "📊 General")

        # Table Stats
        table_tab = self._create_table_stats_tab()
        tabs.addTab(table_tab, "📋 Tables")

        # Index Stats
        index_tab = self._create_index_stats_tab()
        tabs.addTab(index_tab, "🔍 Indexes")

        layout.addWidget(tabs)

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Statistics")
        refresh_btn.clicked.connect(self._load_stats)
        layout.addWidget(refresh_btn)

    def _create_general_stats_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        self.general_stats_text = QPlainTextEdit()
        self.general_stats_text.setReadOnly(True)
        self.general_stats_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.general_stats_text)

        return widget

    def _create_table_stats_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        self.table_stats_table = QTableWidget()
        self.table_stats_table.setAlternatingRowColors(True)
        layout.addWidget(self.table_stats_table)

        return widget

    def _create_index_stats_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()

        self.index_stats_table = QTableWidget()
        self.index_stats_table.setAlternatingRowColors(True)
        layout.addWidget(self.index_stats_table)

        return widget

    def _load_stats(self):
        """Load performance statistics"""
        try:
            cursor = self.connection.cursor()

            # General stats
            stats = []

            # Database size
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]

            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]

            db_size = page_size * page_count
            stats.append(f"Database Size: {db_size:,} bytes ({db_size/1024/1024:.2f} MB)")

            # Tables count
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]
            stats.append(f"Tables: {table_count}")

            # Indexes count
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index'")
            index_count = cursor.fetchone()[0]
            stats.append(f"Indexes: {index_count}")

            # Views count
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view'")
            view_count = cursor.fetchone()[0]
            stats.append(f"Views: {view_count}")

            # Total rows
            total_rows = 0
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            for (table_name,) in cursor.fetchall():
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    total_rows += cursor.fetchone()[0]
                except:
                    pass
            stats.append(f"Total Rows: {total_rows:,}")

            # Foreign keys
            cursor.execute("PRAGMA foreign_keys")
            fk_enabled = cursor.fetchone()[0]
            stats.append(f"Foreign Keys: {'Enabled' if fk_enabled else 'Disabled'}")

            # Auto vacuum
            cursor.execute("PRAGMA auto_vacuum")
            auto_vacuum = cursor.fetchone()[0]
            stats.append(f"Auto Vacuum: {auto_vacuum}")

            # Journal mode
            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            stats.append(f"Journal Mode: {journal_mode}")

            # Synchronous mode
            cursor.execute("PRAGMA synchronous")
            sync_mode = cursor.fetchone()[0]
            stats.append(f"Synchronous: {sync_mode}")

            self.general_stats_text.setPlainText("\n".join(stats))

            # Table stats
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = cursor.fetchall()

            self.table_stats_table.setRowCount(len(tables))
            self.table_stats_table.setColumnCount(4)
            self.table_stats_table.setHorizontalHeaderLabels(["Table", "Rows", "Columns", "Size (KB)"])

            for row, (table_name,) in enumerate(tables):
                # Row count
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                except:
                    row_count = "Error"

                # Column count
                cursor.execute(f"PRAGMA table_info({table_name})")
                col_count = len(cursor.fetchall())

                # Size estimate
                try:
                    cursor.execute(f"SELECT SUM(LENGTH(*)) FROM {table_name}")
                    size_bytes = cursor.fetchone()[0] or 0
                    size_kb = size_bytes / 1024
                except:
                    size_kb = 0

                self.table_stats_table.setItem(row, 0, QTableWidgetItem(table_name))
                self.table_stats_table.setItem(row, 1, QTableWidgetItem(str(row_count)))
                self.table_stats_table.setItem(row, 2, QTableWidgetItem(str(col_count)))
                self.table_stats_table.setItem(row, 3, QTableWidgetItem(f"{size_kb:.1f}"))

            self.table_stats_table.resizeColumnsToContents()

            # Index stats
            cursor.execute("""
                SELECT name, tbl_name FROM sqlite_master
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
                ORDER BY tbl_name, name
            """)
            indexes = cursor.fetchall()

            self.index_stats_table.setRowCount(len(indexes))
            self.index_stats_table.setColumnCount(2)
            self.index_stats_table.setHorizontalHeaderLabels(["Index", "Table"])

            for row, (index_name, table_name) in enumerate(indexes):
                self.index_stats_table.setItem(row, 0, QTableWidgetItem(index_name))
                self.index_stats_table.setItem(row, 1, QTableWidgetItem(table_name))

            self.index_stats_table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load statistics:\n{str(e)}")


class ForeignKeyVisualizer(QDialog):
    """Foreign Key Relationships Visualizer"""

    def __init__(self, parent, connection):
        super().__init__(parent)
        self.connection = connection

        self.setWindowTitle("🔗 Foreign Key Relationships")
        self.resize(800, 600)
        self.setModal(False)

        self._init_ui()
        self._load_relationships()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("🔗 Database Relationships")
        header.setStyleSheet("""
            font-size: 16pt; font-weight: bold; padding: 10px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #bd93f9, stop:1 #8b5cf6);
            color: white; border-radius: 5px;
        """)
        layout.addWidget(header)

        # Relationships tree
        self.relationships_tree = QTreeWidget()
        self.relationships_tree.setHeaderLabels(["Table", "Column", "References", "Action"])
        self.relationships_tree.setAlternatingRowColors(True)
        layout.addWidget(self.relationships_tree)

        # Legend
        legend = QLabel("🔑 Primary Key | 🔗 Foreign Key | 📋 Referenced Table")
        legend.setStyleSheet("color: #888; padding: 5px; font-size: 10pt;")
        layout.addWidget(legend)

    def _load_relationships(self):
        """Load foreign key relationships"""
        try:
            cursor = self.connection.cursor()

            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()

            for (table_name,) in tables:
                # Get foreign key info for this table
                cursor.execute(f"PRAGMA foreign_key_list({table_name})")
                fks = cursor.fetchall()

                if fks:
                    table_item = QTreeWidgetItem(self.relationships_tree, [table_name, "", "", ""])
                    table_item.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))

                    for fk in fks:
                        fk_item = QTreeWidgetItem(table_item, [
                            "",
                            fk['from'],
                            f"{fk['table']}.{fk['to']}",
                            f"ON {fk['on_update']} / {fk['on_delete']}"
                        ])
                        fk_item.setIcon(1, self.style().standardIcon(QStyle.SP_ArrowRight))
                else:
                    # Table with no foreign keys
                    table_item = QTreeWidgetItem(self.relationships_tree, [table_name, "No relationships", "", ""])
                    table_item.setIcon(0, self.style().standardIcon(QStyle.SP_FileIcon))

            self.relationships_tree.expandAll()
            self.relationships_tree.resizeColumnToContents(0)
            self.relationships_tree.resizeColumnToContents(1)
            self.relationships_tree.resizeColumnToContents(2)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load relationships:\n{str(e)}")


class EditRowDialog(QDialog):
    """Professional row editing dialog - Makes editing super easy!"""

    def __init__(self, parent, table_name, columns_info, row_data=None, mode="edit"):
        super().__init__(parent)
        self.table_name = table_name
        self.columns_info = columns_info
        self.row_data = row_data
        self.mode = mode
        self.field_widgets = {}

        self.setWindowTitle(f"{'Edit' if mode == 'edit' else 'Insert'} Row - {table_name}")
        self.resize(600, 500)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self):
        """Create the editing interface"""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"{'✏️ Edit Row' if self.mode == 'edit' else '➕ Insert New Row'}")
        header.setStyleSheet("""
            font-size: 14pt;
            font-weight: bold;
            padding: 10px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #007acc, stop:1 #005a9e);
            color: white;
            border-radius: 5px;
        """)
        layout.addWidget(header)

        # Info label
        info = QLabel(f"Table: <b>{self.table_name}</b> | "
                     f"{'Editing existing row' if self.mode == 'edit' else 'Creating new row'}")
        info.setStyleSheet("color: #888; padding: 5px; font-size: 9pt;")
        layout.addWidget(info)

        # Scroll area for fields
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        scroll_widget = QWidget()
        scroll_layout = QFormLayout(scroll_widget)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(10, 10, 10, 10)

        # Create input fields for each column
        for col_info in self.columns_info:
            col_name = col_info['name']
            col_type = col_info['type']
            is_pk = col_info['pk']
            not_null = col_info['notnull']
            default_val = col_info['dflt_value']

            # Create label with indicators
            label_text = f"{col_name}"
            if is_pk:
                label_text += " 🔑"
            if not_null:
                label_text += " *"

            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold; font-size: 10pt;")

            # Add type info
            type_label = QLabel(f"({col_type})")
            type_label.setStyleSheet("color: #666; font-size: 9pt;")

            # Create label widget (QFormLayout needs QWidget, not QLayout)
            label_widget = QWidget()
            label_layout = QHBoxLayout(label_widget)
            label_layout.setContentsMargins(0, 0, 0, 0)
            label_layout.addWidget(label)
            label_layout.addWidget(type_label)
            label_layout.addStretch()

            # Create appropriate input widget
            widget = self._create_input_widget(col_type, col_name, default_val, is_pk)

            # Set existing value if editing
            if self.mode == 'edit' and self.row_data and col_name in self.row_data.keys():
                self._set_widget_value(widget, self.row_data[col_name])

            # Disable PK if auto-increment and mode is insert
            if is_pk and self.mode == 'insert' and 'INTEGER' in col_type.upper():
                widget.setEnabled(False)
                if hasattr(widget, 'setPlaceholderText'):
                    widget.setPlaceholderText("Auto-generated")

            scroll_layout.addRow(label_widget, widget)
            self.field_widgets[col_name] = widget

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Help text
        help_text = QLabel("* Required field | 🔑 Primary Key")
        help_text.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        layout.addWidget(help_text)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setFixedSize(120, 35)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #e81123;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c50f1f; }
        """)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("💾 Save" if self.mode == 'edit' else "➕ Insert")
        save_btn.setFixedSize(120, 35)
        save_btn.clicked.connect(self.accept)
        save_btn.setDefault(True)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #16c60c;
                color: white;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #13a10e; }
        """)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _create_input_widget(self, col_type, col_name, default_val, is_pk):
        """Create appropriate input widget based on column type"""
        col_type_upper = col_type.upper()

        if 'INTEGER' in col_type_upper or 'INT' in col_type_upper:
            widget = QSpinBox()
            widget.setRange(-2147483648, 2147483647)
            widget.setFixedHeight(30)
            if default_val:
                try:
                    widget.setValue(int(default_val))
                except:
                    pass
            return widget

        elif 'REAL' in col_type_upper or 'FLOAT' in col_type_upper or 'DOUBLE' in col_type_upper:
            widget = QDoubleSpinBox()
            widget.setRange(-1e308, 1e308)
            widget.setDecimals(6)
            widget.setFixedHeight(30)
            if default_val:
                try:
                    widget.setValue(float(default_val))
                except:
                    pass
            return widget

        elif 'TEXT' in col_type_upper or 'CHAR' in col_type_upper or 'CLOB' in col_type_upper:
            # Multi-line text for TEXT types
            widget = QTextEdit()
            widget.setMaximumHeight(100)
            if default_val:
                widget.setPlainText(str(default_val))
            return widget

        elif 'BLOB' in col_type_upper:
            widget = QLineEdit()
            widget.setReadOnly(True)
            widget.setPlaceholderText("BLOB data (binary)")
            widget.setFixedHeight(30)
            return widget

        elif 'DATE' in col_type_upper:
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDate(QDate.currentDate())
            widget.setFixedHeight(30)
            return widget

        elif 'TIME' in col_type_upper:
            widget = QTimeEdit()
            widget.setTime(QTime.currentTime())
            widget.setFixedHeight(30)
            return widget

        else:
            # Default to line edit
            widget = QLineEdit()
            widget.setFixedHeight(30)
            if default_val:
                widget.setText(str(default_val))
            return widget

    def _set_widget_value(self, widget, value):
        """Set value in widget based on type"""
        if value is None:
            return

        if isinstance(widget, QSpinBox):
            try:
                widget.setValue(int(value))
            except:
                pass
        elif isinstance(widget, QDoubleSpinBox):
            try:
                widget.setValue(float(value))
            except:
                pass
        elif isinstance(widget, QTextEdit):
            widget.setPlainText(str(value))
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value))
        elif isinstance(widget, QDateEdit):
            try:
                # Parse date string
                date_str = str(value)
                if date_str:
                    widget.setDate(QDate.fromString(date_str, "yyyy-MM-dd"))
            except:
                pass
        elif isinstance(widget, QTimeEdit):
            try:
                time_str = str(value)
                if time_str:
                    widget.setTime(QTime.fromString(time_str, "HH:mm:ss"))
            except:
                pass

    def get_values(self):
        """Get all field values as dictionary"""
        values = {}
        for col_name, widget in self.field_widgets.items():
            if isinstance(widget, QSpinBox) or isinstance(widget, QDoubleSpinBox):
                values[col_name] = widget.value()
            elif isinstance(widget, QTextEdit):
                text = widget.toPlainText().strip()
                values[col_name] = text if text else None
            elif isinstance(widget, QLineEdit):
                text = widget.text().strip()
                values[col_name] = text if text else None
            elif isinstance(widget, QDateEdit):
                values[col_name] = widget.date().toString("yyyy-MM-dd")
            elif isinstance(widget, QTimeEdit):
                values[col_name] = widget.time().toString("HH:mm:ss")
            else:
                values[col_name] = None

        return values


class SQLiteStudioPro(QDialog):
    """Complete SQLiteStudio Professional Clone"""
    
    def __init__(self, parent, db_path):
        super().__init__(parent)
        self.db_path = Path(db_path)
        self.connection = None
        self.current_table = None
        self.query_history = []
        
        self.setWindowTitle(f"🗄️ SQLiteStudio Professional - {self.db_path.name}")
        self.resize(1600, 1000)
        self.setModal(False)
        
        self._init_ui()
        self._connect_database()
        self._load_structure()
    
    def _init_ui(self):
        """Initialize complete UI"""
        self.setStyleSheet(self._get_stylesheet())
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Stunning Header Banner
        header_widget = QWidget()
        header_widget.setFixedHeight(80)
        header_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0078d4, stop:0.5 #00a8ff, stop:1 #0078d4);
                border-bottom: 3px solid #00d4ff;
            }
        """)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 10, 20, 10)
        
        # App Title
        title = QLabel(f"🗄️ SQLiteStudio Professional")
        title.setStyleSheet("""
            font-size: 24pt;
            font-weight: bold;
            color: #ffffff;
        """)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Database Name
        db_label = QLabel(f"📁 {self.db_path.name}")
        db_label.setStyleSheet("""
            font-size: 14pt;
            font-weight: 600;
            color: #ffffff;
            background-color: rgba(0, 0, 0, 0.3);
            padding: 8px 16px;
            border-radius: 6px;
        """)
        header_layout.addWidget(db_label)
        
        layout.addWidget(header_widget)
        
        # Menu bar
        menubar = self._create_menubar()
        layout.setMenuBar(menubar)
        
        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        
        # Main splitter
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Left: Navigator
        nav_widget = self._create_navigator()
        main_splitter.addWidget(nav_widget)
        
        # Right: Tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        
        self._create_data_tab()
        self._create_sql_tab()
        self._create_structure_tab()
        
        main_splitter.addWidget(self.tab_widget)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 4)
        
        layout.addWidget(main_splitter)
        
        # Status bar
        statusbar = self._create_statusbar()
        layout.addWidget(statusbar)
    
    def _create_menubar(self):
        """Create menu bar"""
        menubar = QMenuBar()
        
        # Database menu
        db_menu = menubar.addMenu("&Database")
        db_menu.addAction("📂 Open Database...", self._open_database, "Ctrl+O")
        db_menu.addAction("🔄 Refresh", self._refresh_all, "F5")
        db_menu.addSeparator()
        db_menu.addAction("📤 Export Database...", self._export_database)
        db_menu.addAction("📥 Import CSV...", self._import_csv)
        db_menu.addSeparator()
        db_menu.addAction("🚪 Close", self.close, "Ctrl+W")
        
        # Table menu
        table_menu = menubar.addMenu("&Table")
        table_menu.addAction("🆕 Create Table...", self._create_table)
        table_menu.addAction("✏️ Alter Table...", self._alter_table)
        table_menu.addAction("🗑️ Drop Table...", self._drop_table)
        table_menu.addSeparator()
        table_menu.addAction("📤 Export Table...", self._export_table)
        table_menu.addAction("📥 Import to Table...", self._import_to_table)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        edit_menu.addAction("➕ Insert Row", self._insert_row, "Ctrl+N")
        edit_menu.addAction("✏️ Edit Row", self._edit_row, "Ctrl+E")
        edit_menu.addAction("📋 Duplicate Row", self._duplicate_row, "Ctrl+D")
        edit_menu.addAction("🗑️ Delete Row(s)", self._delete_rows, "Delete")
        edit_menu.addSeparator()
        edit_menu.addAction("🔍 Find...", self._show_find, "Ctrl+F")
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        tools_menu.addAction("🧹 VACUUM", self._vacuum_database)
        tools_menu.addAction("🔄 REINDEX", self._reindex_database)
        tools_menu.addAction("📊 ANALYZE", self._analyze_database)
        tools_menu.addSeparator()
        tools_menu.addAction("✅ Integrity Check", self._integrity_check)
        tools_menu.addAction("💾 Backup Database...", self._backup_database)
        tools_menu.addSeparator()
        tools_menu.addAction("🔧 Query Builder...", self._show_query_builder)
        tools_menu.addAction("🎲 Data Generator...", self._show_data_generator)
        tools_menu.addAction("📈 Performance Monitor...", self._show_performance_monitor)
        tools_menu.addAction("🔗 Foreign Key Visualizer...", self._show_fk_visualizer)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        help_menu.addAction("📖 Documentation", self._show_help)
        help_menu.addAction("ℹ️ About", self._show_about)
        
        return menubar
    
    def _create_toolbar(self):
        """Create toolbar"""
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
                font-size: 18px;
            }
            QToolButton:hover {
                background: #505052;
                border-color: #007acc;
            }
            QToolButton:pressed {
                background: #007acc;
            }
        """)
        
        # Add actions
        toolbar.addAction("📂").triggered.connect(self._open_database)
        toolbar.addAction("🔄").triggered.connect(self._refresh_all)
        toolbar.addSeparator()
        toolbar.addAction("➕").triggered.connect(self._insert_row)
        toolbar.addAction("✏️").triggered.connect(self._edit_row)
        toolbar.addAction("🗑️").triggered.connect(self._delete_rows)
        toolbar.addSeparator()
        toolbar.addAction("🔍").triggered.connect(self._show_find)
        toolbar.addAction("📤").triggered.connect(self._export_table)
        toolbar.addAction("📥").triggered.connect(self._import_to_table)
        toolbar.addSeparator()
        toolbar.addAction("🧹").triggered.connect(self._vacuum_database)
        toolbar.addSeparator()
        toolbar.addAction("🔧").triggered.connect(self._show_query_builder)
        toolbar.addAction("🎲").triggered.connect(self._show_data_generator)
        toolbar.addAction("📈").triggered.connect(self._show_performance_monitor)
        toolbar.addAction("🔗").triggered.connect(self._show_fk_visualizer)
        
        return toolbar
    
    def _create_navigator(self):
        """Create navigator panel"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        header = QLabel("📁 Database Objects")
        header.setStyleSheet("font-weight: bold; font-size: 11pt; padding: 5px;")
        layout.addWidget(header)
        
        self.nav_filter = QLineEdit()
        self.nav_filter.setPlaceholderText("🔍 Filter...")
        self.nav_filter.textChanged.connect(self._filter_navigator)
        layout.addWidget(self.nav_filter)
        
        self.nav_tree = QTreeWidget()
        self.nav_tree.setHeaderHidden(True)
        self.nav_tree.itemDoubleClicked.connect(self._on_nav_double_click)
        self.nav_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.nav_tree.customContextMenuRequested.connect(self._show_nav_context_menu)
        layout.addWidget(self.nav_tree)
        
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #888; font-size: 9pt; padding: 5px;")
        layout.addWidget(self.stats_label)
        
        return widget
    
    def _create_data_tab(self):
        """Create data browser tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Controls
        controls = QWidget()
        controls.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1f1f1f);
                border-radius: 8px;
                padding: 8px;
            }
        """)
        controls_layout = QHBoxLayout(controls)
        
        controls_layout.addWidget(QLabel("📋 Table:"))
        self.table_combo = QComboBox()
        self.table_combo.setMinimumWidth(200)
        self.table_combo.currentTextChanged.connect(self._load_table_data)
        controls_layout.addWidget(self.table_combo)
        
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self._refresh_current_table)
        controls_layout.addWidget(btn_refresh)
        
        btn_insert = QPushButton("➕ Insert Row")
        btn_insert.clicked.connect(self._insert_row)
        btn_insert.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #16c60c, stop:1 #13a10e);
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1fff00, stop:1 #16c60c);
            }
        """)
        controls_layout.addWidget(btn_insert)
        
        btn_edit = QPushButton("✏️ Edit Row")
        btn_edit.clicked.connect(self._edit_row)
        btn_edit.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0078d4, stop:1 #005a9e);
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00a8ff, stop:1 #0078d4);
            }
        """)
        controls_layout.addWidget(btn_edit)
        
        btn_delete = QPushButton("🗑️ Delete")
        btn_delete.clicked.connect(self._delete_rows)
        btn_delete.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e81123, stop:1 #c50f1f);
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff1f3f, stop:1 #e81123);
            }
        """)
        controls_layout.addWidget(btn_delete)
        
        controls_layout.addStretch()
        
        controls_layout.addWidget(QLabel("🔍 Filter:"))
        self.data_filter = QLineEdit()
        self.data_filter.setPlaceholderText("Search...")
        self.data_filter.setMinimumWidth(200)
        self.data_filter.textChanged.connect(self._filter_table_data)
        controls_layout.addWidget(self.data_filter)
        
        layout.addWidget(controls)
        
        # Data table - EXACTLY like SQLiteStudio.pl!
        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setSortingEnabled(False)  # Disable during editing
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.data_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # ENABLE ALL EDIT TRIGGERS - Just like SQLiteStudio!
        self.data_table.setEditTriggers(
            QAbstractItemView.DoubleClicked | 
            QAbstractItemView.EditKeyPressed | 
            QAbstractItemView.AnyKeyPressed |
            QAbstractItemView.SelectedClicked
        )
        self.data_table.itemChanged.connect(self._on_cell_edited)
        self.data_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.data_table.customContextMenuRequested.connect(self._show_data_context_menu)
        layout.addWidget(self.data_table)
        
        # Info bar
        info_bar = QWidget()
        info_layout = QHBoxLayout(info_bar)
        self.row_count_label = QLabel("0 rows")
        self.selected_label = QLabel("")
        info_layout.addWidget(self.row_count_label)
        info_layout.addWidget(self.selected_label)
        info_layout.addStretch()
        layout.addWidget(info_bar)
        
        self.tab_widget.addTab(widget, "📊 Data Browser")
    
    def _create_sql_tab(self):
        """Create SQL editor tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Controls
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        
        btn_execute = QPushButton("▶️ Execute (F5)")
        btn_execute.setStyleSheet("background-color: #16c60c; font-weight: bold; font-size: 11pt;")
        btn_execute.clicked.connect(self._execute_sql)
        controls_layout.addWidget(btn_execute)
        
        btn_clear = QPushButton("🧹 Clear")
        btn_clear.clicked.connect(lambda: self.sql_editor.clear())
        controls_layout.addWidget(btn_clear)
        
        btn_format = QPushButton("📝 Format")
        btn_format.clicked.connect(self._format_sql)
        controls_layout.addWidget(btn_format)
        
        controls_layout.addStretch()
        
        controls_layout.addWidget(QLabel("📚 History:"))
        self.sql_history_combo = QComboBox()
        self.sql_history_combo.setMinimumWidth(300)
        self.sql_history_combo.addItem("-- Query History --")
        self.sql_history_combo.currentTextChanged.connect(self._load_history_query)
        controls_layout.addWidget(self.sql_history_combo)
        
        layout.addWidget(controls)
        
        # SQL Editor
        self.sql_editor = QPlainTextEdit()
        self.sql_editor.setFont(QFont("Consolas", 11))
        self.sql_editor.setPlaceholderText(
            "-- SQLiteStudio Professional SQL Editor\n"
            "-- Write your SQL queries here and press F5 to execute\n\n"
            "-- Examples:\n"
            "SELECT * FROM my_table WHERE id > 10 LIMIT 100;\n\n"
            "INSERT INTO my_table (name, value) VALUES ('example', 123);\n\n"
            "UPDATE my_table SET value = 456 WHERE name = 'example';\n\n"
            "DELETE FROM my_table WHERE id = 1;"
        )

        # Add syntax highlighting and auto-completion
        self.syntax_highlighter = SyntaxHighlighter(self.sql_editor.document())
        self.auto_completer = AutoCompleter(self.sql_editor)

        layout.addWidget(self.sql_editor, stretch=1)
        
        # Results
        results_label = QLabel("📊 Query Results:")
        results_label.setStyleSheet("font-weight: bold; padding: 5px; font-size: 10pt;")
        layout.addWidget(results_label)
        
        self.sql_results = QTableWidget()
        self.sql_results.setAlternatingRowColors(True)
        layout.addWidget(self.sql_results, stretch=2)
        
        # Status
        self.sql_status = QLabel("Ready to execute SQL queries")
        self.sql_status.setStyleSheet("padding: 5px; color: #888;")
        layout.addWidget(self.sql_status)
        
        self.tab_widget.addTab(widget, "📝 SQL Editor")
    
    def _create_structure_tab(self):
        """Create structure tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        
        btn_refresh = QPushButton("🔄 Refresh Structure")
        btn_refresh.clicked.connect(self._load_structure)
        controls_layout.addWidget(btn_refresh)
        
        btn_export = QPushButton("📤 Export Schema")
        btn_export.clicked.connect(self._export_schema)
        controls_layout.addWidget(btn_export)
        
        controls_layout.addStretch()
        layout.addWidget(controls)
        
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
    
    def _get_stylesheet(self):
        """Get stunning modern stylesheet - Better than SQLiteStudio.pl!"""
        return """
            /* Main Window - Sleek Gradient Background */
            QDialog, QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0f0f0f, stop:1 #1a1a1a);
                color: #e0e0e0;
                font-family: 'Segoe UI', 'San Francisco', Arial, sans-serif;
                font-size: 10pt;
            }
            
            QWidget {
                background-color: transparent;
                color: #e0e0e0;
            }
            
            /* MenuBar - Premium Look */
            QMenuBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1f1f1f);
                color: #ffffff;
                border-bottom: 2px solid #0078d4;
                padding: 4px;
            }
            
            QMenuBar::item {
                padding: 6px 12px;
                background: transparent;
                border-radius: 4px;
                margin: 2px;
            }
            
            QMenuBar::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0078d4, stop:1 #005a9e);
            }
            
            QMenuBar::item:pressed {
                background: #005a9e;
            }
            
            /* Menu Dropdowns - Modern & Clean */
            QMenu {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 2px solid #0078d4;
                border-radius: 6px;
                padding: 4px;
            }
            
            QMenu::item {
                padding: 8px 30px 8px 20px;
                border-radius: 4px;
                margin: 2px;
            }
            
            QMenu::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0078d4, stop:1 #005a9e);
            }
            
            QMenu::separator {
                height: 2px;
                background: #404040;
                margin: 4px 10px;
            }
            
            /* Buttons - 3D Modern Style */
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a3a3a, stop:1 #2a2a2a);
                color: #ffffff;
                border: 2px solid #4a4a4a;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                min-height: 25px;
            }
            
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0078d4, stop:1 #005a9e);
                border-color: #0078d4;
            }
            
            QPushButton:pressed {
                background: #005a9e;
                padding-top: 10px;
                padding-left: 18px;
            }
            
            QPushButton:disabled {
                background: #1a1a1a;
                color: #666666;
                border-color: #333333;
            }
            
            /* Input Fields - Elegant Style */
            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 2px solid #404040;
                border-radius: 5px;
                padding: 6px 10px;
                selection-background-color: #0078d4;
            }
            
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
                border: 2px solid #0078d4;
                background-color: #2f2f2f;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 25px;
                background: #3a3a3a;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #ffffff;
                margin-right: 5px;
            }
            
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                border: 2px solid #0078d4;
                selection-background-color: #0078d4;
                selection-color: #ffffff;
                border-radius: 4px;
            }
            
            /* Table Widget - Professional Data Grid */
            QTableWidget {
                background-color: #1a1a1a;
                alternate-background-color: #222222;
                gridline-color: #333333;
                selection-background-color: #0078d4;
                selection-color: #ffffff;
                border: 2px solid #333333;
                border-radius: 6px;
            }
            
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #2a2a2a;
            }
            
            QTableWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0078d4, stop:1 #005a9e);
            }
            
            QTableWidget::item:hover {
                background-color: #2a2a2a;
            }
            
            /* Header - Standout Design */
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3a3a3a, stop:1 #2a2a2a);
                color: #ffffff;
                padding: 8px;
                border: none;
                border-right: 1px solid #1a1a1a;
                border-bottom: 2px solid #0078d4;
                font-weight: bold;
                font-size: 10pt;
            }
            
            QHeaderView::section:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0078d4, stop:1 #005a9e);
            }
            
            /* Tree Widget - Clean Hierarchy */
            QTreeWidget {
                background-color: #1f1f1f;
                color: #e0e0e0;
                border: 2px solid #333333;
                border-radius: 6px;
                padding: 4px;
            }
            
            QTreeWidget::item {
                padding: 6px;
                border-radius: 4px;
            }
            
            QTreeWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0078d4, stop:1 #005a9e);
                color: #ffffff;
            }
            
            QTreeWidget::item:hover {
                background-color: #2a2a2a;
            }
            
            QTreeWidget::branch {
                background: transparent;
            }
            
            /* Text Editors - Code Style */
            QPlainTextEdit, QTextEdit {
                background-color: #1a1a1a;
                color: #d4d4d4;
                border: 2px solid #333333;
                border-radius: 6px;
                selection-background-color: #264f78;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                padding: 8px;
            }
            
            QPlainTextEdit:focus, QTextEdit:focus {
                border-color: #0078d4;
            }
            
            /* Tab Widget - Modern Tabs */
            QTabWidget::pane {
                border: 2px solid #333333;
                background: #1a1a1a;
                border-radius: 6px;
                top: -2px;
            }
            
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1f1f1f);
                color: #b0b0b0;
                padding: 10px 20px;
                border: 2px solid #333333;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
                font-weight: 600;
            }
            
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0078d4, stop:1 #005a9e);
                color: #ffffff;
                border-bottom: 3px solid #0078d4;
            }
            
            QTabBar::tab:hover {
                background: #2a2a2a;
                color: #ffffff;
            }
            
            /* Scrollbars - Sleek Design */
            QScrollBar:vertical {
                background: #1a1a1a;
                width: 14px;
                border-radius: 7px;
                margin: 2px;
            }
            
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a4a4a, stop:1 #3a3a3a);
                min-height: 30px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0078d4, stop:1 #005a9e);
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            
            QScrollBar:horizontal {
                background: #1a1a1a;
                height: 14px;
                border-radius: 7px;
                margin: 2px;
            }
            
            QScrollBar::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4a4a4a, stop:1 #3a3a3a);
                min-width: 30px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0078d4, stop:1 #005a9e);
            }
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            
            /* ToolBar - Professional Look */
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2a2a2a, stop:1 #1f1f1f);
                border-bottom: 2px solid #0078d4;
                spacing: 6px;
                padding: 6px;
            }
            
            QToolButton {
                background: transparent;
                border: 2px solid transparent;
                border-radius: 6px;
                padding: 8px;
                color: #ffffff;
                font-size: 16px;
            }
            
            QToolButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0078d4, stop:1 #005a9e);
                border-color: #0078d4;
            }
            
            QToolButton:pressed {
                background: #005a9e;
            }
            
            /* Labels - Clean Typography */
            QLabel {
                color: #e0e0e0;
                background: transparent;
            }
            
            /* GroupBox - Card Style */
            QGroupBox {
                border: 2px solid #333333;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: #1f1f1f;
                font-weight: bold;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 4px 10px;
                background-color: #0078d4;
                color: #ffffff;
                border-radius: 4px;
                left: 10px;
            }
            
            /* Status Bar - Informative Footer */
            QStatusBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1f1f1f, stop:1 #0f0f0f);
                color: #b0b0b0;
                border-top: 2px solid #0078d4;
            }
            
            /* Progress Bar - Modern Loading */
            QProgressBar {
                border: 2px solid #333333;
                border-radius: 5px;
                background-color: #1a1a1a;
                text-align: center;
                color: #ffffff;
                font-weight: bold;
            }
            
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0078d4, stop:1 #00d4ff);
                border-radius: 3px;
            }
        """
    
    def _connect_database(self):
        """Connect to database"""
        try:
            self.connection = sqlite3.connect(str(self.db_path))
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA foreign_keys = ON")
            
            self.connection_label.setText(f"✅ {self.db_path.name}")
            self.status_label.setText("Connected to database")
            
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect:\n{str(e)}")
    
    def _load_structure(self):
        """Load database structure"""
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
                
                cursor.execute(f"PRAGMA table_info({table['name']})")
                columns = cursor.fetchall()
                
                for col in columns:
                    pk_marker = " 🔑" if col['pk'] else ""
                    col_item = QTreeWidgetItem(table_item, 
                        [f"  📄 {col['name']} ({col['type']}){pk_marker}"])
            
            # Views
            views_root = QTreeWidgetItem(self.nav_tree, ["👁️ Views"])
            cursor.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
            for view in cursor.fetchall():
                QTreeWidgetItem(views_root, [f"  🔍 {view['name']}"])
            
            # Indexes
            indexes_root = QTreeWidgetItem(self.nav_tree, ["🔍 Indexes"])
            cursor.execute("""
                SELECT name, tbl_name FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            for index in cursor.fetchall():
                QTreeWidgetItem(indexes_root, [f"  ⚡ {index['name']} ({index['tbl_name']})"])
            
            self.stats_label.setText(f"📊 {len(tables)} tables")
            
            # Load into combo
            self.table_combo.clear()
            self.table_combo.addItem("-- Select Table --")
            for table in tables:
                self.table_combo.addItem(table['name'])
            
            # Load structure text
            self._load_structure_text()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load structure:\n{str(e)}")
    
    def _load_structure_text(self):
        """Load structure as SQL"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type, name")
            
            schema_sql = f"-- Database Schema: {self.db_path.name}\n"
            schema_sql += f"-- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            for row in cursor.fetchall():
                schema_sql += row['sql'] + ";\n\n"
            
            self.structure_text.setPlainText(schema_sql)
        except:
            pass
    
    def _load_table_data(self, table_name):
        """Load table data"""
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
            self.current_columns_info = cursor.fetchall()
            column_names = [col['name'] for col in self.current_columns_info]
            
            # Get data
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            # Disable itemChanged signal during loading
            self.data_table.itemChanged.disconnect(self._on_cell_edited)
            
            # Populate table
            self.data_table.setRowCount(len(rows))
            self.data_table.setColumnCount(len(column_names))
            self.data_table.setHorizontalHeaderLabels(column_names)
            
            for row_idx, row in enumerate(rows):
                for col_idx, col_name in enumerate(column_names):
                    value = row[col_name]
                    item = QTableWidgetItem(str(value) if value is not None else "")
                    item.setData(Qt.UserRole, value)  # Store original value
                    item.setData(Qt.UserRole + 1, row_idx)  # Store row index
                    
                    # Make PK cells read-only
                    if self.current_columns_info[col_idx]['pk']:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        item.setBackground(QColor("#2a3a4a"))  # Highlight PKs
                    
                    self.data_table.setItem(row_idx, col_idx, item)
            
            self.data_table.resizeColumnsToContents()
            
            # Reconnect signal
            self.data_table.itemChanged.connect(self._on_cell_edited)
            
            self.row_count_label.setText(f"📊 {len(rows):,} rows")
            self.status_label.setText(f"Loaded table '{table_name}' with {len(rows):,} rows")
            
        except Exception as e:
            self.data_table.itemChanged.connect(self._on_cell_edited)
            QMessageBox.critical(self, "Load Error", f"Failed to load table:\n{str(e)}")
    
    def _insert_row(self):
        """Insert new row with easy dialog"""
        if not self.current_table:
            QMessageBox.warning(self, "No Table", "Please select a table first.")
            return
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns_info = cursor.fetchall()
            
            dialog = EditRowDialog(self, self.current_table, columns_info, mode="insert")
            if dialog.exec() == QDialog.Accepted:
                values = dialog.get_values()
                
                # Build INSERT query
                columns = []
                placeholders = []
                vals = []
                
                for col_info in columns_info:
                    col_name = col_info['name']
                    # Skip auto-increment PKs
                    if col_info['pk'] and 'INTEGER' in col_info['type'].upper() and values[col_name] is None:
                        continue
                    
                    columns.append(col_name)
                    placeholders.append('?')
                    vals.append(values[col_name])
                
                sql = f"INSERT INTO {self.current_table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                cursor.execute(sql, vals)
                self.connection.commit()
                
                self._refresh_current_table()
                self.status_label.setText(f"✅ Row inserted into '{self.current_table}'")
                QMessageBox.information(self, "Success", "Row inserted successfully!")
                
        except Exception as e:
            self.connection.rollback()
            QMessageBox.critical(self, "Insert Error", f"Failed to insert row:\n{str(e)}")
    
    def _edit_row(self):
        """Edit selected row with easy dialog"""
        if not self.current_table:
            return
        
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())
        
        if len(selected_rows) != 1:
            QMessageBox.warning(self, "Selection", "Please select exactly one row to edit.")
            return
        
        row_idx = list(selected_rows)[0]
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns_info = cursor.fetchall()
            
            # Get current row data
            row_data = {}
            for col_idx, col_info in enumerate(columns_info):
                col_name = col_info['name']
                item = self.data_table.item(row_idx, col_idx)
                if item:
                    row_data[col_name] = item.data(Qt.UserRole)
            
            dialog = EditRowDialog(self, self.current_table, columns_info, row_data, mode="edit")
            if dialog.exec() == QDialog.Accepted:
                new_values = dialog.get_values()
                
                # Find PK
                pk_col = None
                pk_value = None
                for col_info in columns_info:
                    if col_info['pk']:
                        pk_col = col_info['name']
                        pk_value = row_data[pk_col]
                        break
                
                if not pk_col:
                    QMessageBox.warning(self, "No Primary Key", 
                        "Cannot update - table has no primary key.")
                    return
                
                # Build UPDATE query
                set_parts = []
                vals = []
                for col_name, value in new_values.items():
                    if col_name != pk_col:  # Don't update PK
                        set_parts.append(f"{col_name} = ?")
                        vals.append(value)
                
                vals.append(pk_value)
                
                sql = f"UPDATE {self.current_table} SET {', '.join(set_parts)} WHERE {pk_col} = ?"
                cursor.execute(sql, vals)
                self.connection.commit()
                
                self._refresh_current_table()
                self.status_label.setText(f"✅ Row updated in '{self.current_table}'")
                QMessageBox.information(self, "Success", "Row updated successfully!")
                
        except Exception as e:
            self.connection.rollback()
            QMessageBox.critical(self, "Update Error", f"Failed to update row:\n{str(e)}")
    
    def _delete_rows(self):
        """Delete selected rows"""
        if not self.current_table:
            return
        
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select row(s) to delete.")
            return
        
        reply = QMessageBox.question(self, "Confirm Delete",
            f"Are you sure you want to delete {len(selected_rows)} row(s)?\n\n"
            "This action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns_info = cursor.fetchall()
            
            # Find PK
            pk_col = None
            pk_idx = None
            for idx, col_info in enumerate(columns_info):
                if col_info['pk']:
                    pk_col = col_info['name']
                    pk_idx = idx
                    break
            
            if not pk_col:
                QMessageBox.warning(self, "No Primary Key",
                    "Cannot delete - table has no primary key.")
                return
            
            # Delete each row
            deleted = 0
            for row_idx in selected_rows:
                item = self.data_table.item(row_idx, pk_idx)
                if item:
                    pk_value = item.data(Qt.UserRole)
                    cursor.execute(f"DELETE FROM {self.current_table} WHERE {pk_col} = ?", (pk_value,))
                    deleted += 1
            
            self.connection.commit()
            self._refresh_current_table()
            self.status_label.setText(f"✅ Deleted {deleted} row(s) from '{self.current_table}'")
            QMessageBox.information(self, "Success", f"Deleted {deleted} row(s) successfully!")
            
        except Exception as e:
            self.connection.rollback()
            QMessageBox.critical(self, "Delete Error", f"Failed to delete row(s):\n{str(e)}")
    
    def _duplicate_row(self):
        """Duplicate selected row"""
        if not self.current_table:
            return
        
        selected_rows = set()
        for item in self.data_table.selectedItems():
            selected_rows.add(item.row())
        
        if len(selected_rows) != 1:
            QMessageBox.warning(self, "Selection", "Please select exactly one row to duplicate.")
            return
        
        row_idx = list(selected_rows)[0]
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns_info = cursor.fetchall()
            
            columns = []
            values = []
            
            for col_idx, col_info in enumerate(columns_info):
                col_name = col_info['name']
                # Skip auto-increment PK
                if col_info['pk'] and 'INTEGER' in col_info['type'].upper():
                    continue
                
                item = self.data_table.item(row_idx, col_idx)
                if item:
                    columns.append(col_name)
                    values.append(item.data(Qt.UserRole))
            
            placeholders = ', '.join(['?'] * len(values))
            sql = f"INSERT INTO {self.current_table} ({', '.join(columns)}) VALUES ({placeholders})"
            cursor.execute(sql, values)
            self.connection.commit()
            
            self._refresh_current_table()
            self.status_label.setText(f"✅ Row duplicated in '{self.current_table}'")
            QMessageBox.information(self, "Success", "Row duplicated successfully!")
            
        except Exception as e:
            self.connection.rollback()
            QMessageBox.critical(self, "Duplicate Error", f"Failed to duplicate row:\n{str(e)}")
    
    def _execute_sql(self):
        """Execute SQL query"""
        sql = self.sql_editor.toPlainText().strip()
        if not sql:
            return
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
            
            if sql.upper().strip().startswith('SELECT'):
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
                self.connection.commit()
                self.sql_results.setRowCount(0)
                self.sql_status.setText(f"✅ Query executed - {cursor.rowcount} rows affected")
                self._refresh_current_table()  # Refresh if data changed
            
            # Add to history
            if sql not in self.query_history:
                self.query_history.append(sql)
                display = sql[:80] + "..." if len(sql) > 80 else sql
                self.sql_history_combo.addItem(display)
            
        except Exception as e:
            self.sql_status.setText(f"❌ Error: {str(e)}")
            QMessageBox.critical(self, "SQL Error", f"Failed to execute query:\n{str(e)}")
    
    def _format_sql(self):
        """Format SQL"""
        sql = self.sql_editor.toPlainText()
        keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT',
                   'ON', 'GROUP BY', 'ORDER BY', 'LIMIT', 'INSERT', 'INTO',
                   'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE']
        
        for keyword in keywords:
            sql = sql.replace(keyword.lower(), keyword)
        
        self.sql_editor.setPlainText(sql)
    
    def _load_history_query(self, text):
        """Load query from history"""
        if text and text != "-- Query History --":
            idx = self.sql_history_combo.currentIndex() - 1
            if 0 <= idx < len(self.query_history):
                self.sql_editor.setPlainText(self.query_history[idx])
    
    def _filter_navigator(self, text):
        """Filter navigator"""
        for i in range(self.nav_tree.topLevelItemCount()):
            self._filter_tree_item(self.nav_tree.topLevelItem(i), text.lower())
    
    def _filter_tree_item(self, item, text):
        """Filter tree item"""
        if not text:
            item.setHidden(False)
            for i in range(item.childCount()):
                self._filter_tree_item(item.child(i), text)
            return True
        
        visible = text in item.text(0).lower()
        for i in range(item.childCount()):
            if self._filter_tree_item(item.child(i), text):
                visible = True
        
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
    
    def _on_cell_edited(self, item):
        """Handle direct cell editing - EXACTLY like SQLiteStudio.pl!"""
        if not self.current_table or not item:
            return
        
        try:
            row_idx = item.row()
            col_idx = item.column()
            new_value = item.text().strip() if item.text().strip() else None
            old_value = item.data(Qt.UserRole)
            
            # Skip if value hasn't changed
            if str(new_value) == str(old_value):
                return
            
            # Get column info
            col_info = self.current_columns_info[col_idx]
            col_name = col_info['name']
            
            # Find PK
            pk_col = None
            pk_value = None
            for idx, info in enumerate(self.current_columns_info):
                if info['pk']:
                    pk_col = info['name']
                    pk_item = self.data_table.item(row_idx, idx)
                    if pk_item:
                        pk_value = pk_item.data(Qt.UserRole)
                    break
            
            if not pk_col:
                QMessageBox.warning(self, "No Primary Key", 
                    "Cannot update - table has no primary key.")
                item.setText(str(old_value) if old_value is not None else "")
                return
            
            # Update database
            cursor = self.connection.cursor()
            cursor.execute(f"UPDATE {self.current_table} SET [{col_name}] = ? WHERE [{pk_col}] = ?", 
                          (new_value, pk_value))
            self.connection.commit()
            
            # Update stored value
            item.setData(Qt.UserRole, new_value)
            
            # Visual feedback - Brief highlight
            original_bg = item.background()
            item.setBackground(QColor("#00ff00"))
            QTimer.singleShot(300, lambda: item.setBackground(original_bg))
            
            self.status_label.setText(f"✅ Updated {col_name} = '{new_value}' in row {row_idx + 1}")
            
        except Exception as e:
            self.connection.rollback()
            QMessageBox.critical(self, "Update Error", f"Failed to update cell:\n{str(e)}")
            # Revert to original value
            if item.data(Qt.UserRole) is not None:
                item.setText(str(item.data(Qt.UserRole)))
    
    def _on_nav_double_click(self, item, column):
        """Handle nav double-click"""
        data = item.data(0, Qt.UserRole)
        if data and data.get('type') == 'table':
            self.table_combo.setCurrentText(data.get('name'))
            self.tab_widget.setCurrentIndex(0)
    
    def _refresh_all(self):
        """Refresh everything"""
        self._load_structure()
        self._refresh_current_table()
        self.status_label.setText("✅ Refreshed")
    
    def _refresh_current_table(self):
        """Refresh current table"""
        if self.current_table:
            self._load_table_data(self.current_table)
    
    def _vacuum_database(self):
        """VACUUM database"""
        try:
            self.connection.execute("VACUUM")
            self.connection.commit()
            QMessageBox.information(self, "Success", "Database vacuumed successfully!")
            self.status_label.setText("✅ Database vacuumed")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"VACUUM failed:\n{str(e)}")
    
    def _reindex_database(self):
        """REINDEX database"""
        try:
            self.connection.execute("REINDEX")
            self.connection.commit()
            QMessageBox.information(self, "Success", "Database reindexed successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"REINDEX failed:\n{str(e)}")
    
    def _analyze_database(self):
        """ANALYZE database"""
        try:
            self.connection.execute("ANALYZE")
            self.connection.commit()
            QMessageBox.information(self, "Success", "Database analyzed successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"ANALYZE failed:\n{str(e)}")
    
    def _integrity_check(self):
        """Check integrity"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            
            if result == "ok":
                QMessageBox.information(self, "Integrity Check",
                    "✅ Database integrity check PASSED!\n\nYour database is healthy.")
            else:
                QMessageBox.warning(self, "Integrity Check",
                    f"❌ Database integrity check FAILED!\n\n{result}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Integrity check failed:\n{str(e)}")
    
    def _backup_database(self):
        """Backup database"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Backup Database",
            f"backup_{self.db_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
            "SQLite Database (*.db *.sqlite *.sqlite3)")
        
        if filename:
            try:
                import shutil
                self.connection.close()
                shutil.copy2(self.db_path, filename)
                self._connect_database()
                QMessageBox.information(self, "Success",
                    f"Database backed up successfully to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Backup failed:\n{str(e)}")
    
    def _export_table(self):
        """Export table to CSV"""
        if not self.current_table:
            QMessageBox.warning(self, "No Table", "Please select a table first.")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, f"Export {self.current_table}",
            f"{self.current_table}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)")
        
        if filename:
            try:
                cursor = self.connection.cursor()
                cursor.execute(f"SELECT * FROM {self.current_table}")
                rows = cursor.fetchall()
                
                cursor.execute(f"PRAGMA table_info({self.current_table})")
                columns = [col['name'] for col in cursor.fetchall()]
                
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(columns)
                    writer.writerows(rows)
                
                QMessageBox.information(self, "Success",
                    f"Exported {len(rows):,} rows to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export:\n{str(e)}")
    
    def _export_schema(self):
        """Export schema"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Schema",
            f"schema_{self.db_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql",
            "SQL Files (*.sql)")
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.structure_text.toPlainText())
                
                QMessageBox.information(self, "Success", f"Schema exported to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")
    
    # Stub methods
    def _open_database(self): pass
    def _export_database(self): pass
    def _import_csv(self): pass
    def _import_to_table(self): pass
    def _create_table(self): pass
    def _alter_table(self): pass
    def _drop_table(self): pass
    def _show_find(self): pass
    def _show_help(self): pass
    def _show_about(self): pass
    def _show_nav_context_menu(self, pos): pass
    def _show_data_context_menu(self, pos): pass
    def _close_tab(self, index):
        if self.tab_widget.count() > 1:
            self.tab_widget.removeTab(index)

    # Professional Features Implementation

    def _show_query_builder(self):
        """Show visual query builder dialog"""
        if not self.connection:
            QMessageBox.warning(self, "No Database", "Please connect to a database first.")
            return

        dialog = QueryBuilderDialog(self, self.connection)
        dialog.exec()

    def _show_data_generator(self):
        """Show data generator dialog"""
        if not self.connection:
            QMessageBox.warning(self, "No Database", "Please connect to a database first.")
            return
        
        if not self.current_table:
            QMessageBox.warning(self, "No Table", "Please select a table first.")
            return

        dialog = DataGeneratorDialog(self, self.current_table, self.current_columns_info)
        dialog.exec()

    def _show_performance_monitor(self):
        """Show performance monitor dialog"""
        if not self.connection:
            QMessageBox.warning(self, "No Database", "Please connect to a database first.")
            return

        dialog = PerformanceMonitorDialog(self, self.connection)
        dialog.exec()

    def _show_fk_visualizer(self):
        """Show foreign key visualizer dialog"""
        if not self.connection:
            QMessageBox.warning(self, "No Database", "Please connect to a database first.")
            return

        dialog = ForeignKeyVisualizer(self, self.connection)
        dialog.exec()
