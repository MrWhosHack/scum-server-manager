"""
Professional Database Manager - Ultimate Tab Implementations

This module contains all the enhanced tab implementations for the database manager:
- Data Browser Tab (with working inline editing!)
- SQL Editor Tab
- Schema Designer Tab
- Database Tools Tab
- Import/Export Tab
- Query History Tab
- Visualization Tab
"""

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
from datetime import datetime
import csv
import json
import threading
import time


class DataBrowserTab:
    """Ultimate data browser with working inline editing and advanced features"""

    def __init__(self, manager):
        self.manager = manager
        self.current_table = None
        self.filter_text = ""
        self.sort_column = -1
        self.sort_order = Qt.AscendingOrder
        self.original_data = {}  # Store original values for rollback

    def create(self):
        """Create the ultimate data browser tab widget"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Enhanced controls
        controls = self._create_controls()
        layout.addWidget(controls)

        # Ultimate data table with editing
        self.table = self._create_table()
        layout.addWidget(self.table)

        # Enhanced status and info
        status_widget = self._create_status_widget()
        layout.addWidget(status_widget)

        widget.setLayout(layout)
        return widget

    def _create_controls(self):
        """Create the enhanced control bar"""
        controls = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(10)

        # Table selector with icon
        table_layout = QHBoxLayout()
        table_icon = QLabel("📋")
        table_icon.setStyleSheet("font-size: 16px;")
        table_layout.addWidget(table_icon)

        table_label = QLabel("Table:")
        table_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        table_layout.addWidget(table_label)

        self.table_combo = QComboBox()
        self.table_combo.setMinimumWidth(200)
        self.table_combo.setStyleSheet("font-size: 11pt; padding: 5px;")
        self.table_combo.currentTextChanged.connect(self._load_table)
        table_layout.addWidget(self.table_combo)

        layout.addLayout(table_layout)

        # Action buttons with enhanced styling
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(5)

        self.btn_refresh = self._create_action_button("🔄 Refresh", "Refresh table data", self._refresh_data)
        actions_layout.addWidget(self.btn_refresh)

        self.btn_add = self._create_action_button("➕ Add Row", "Add a new row to the table", self._add_row)
        actions_layout.addWidget(self.btn_add)

        self.btn_duplicate = self._create_action_button("📋 Duplicate", "Duplicate selected row", self._duplicate_row)
        actions_layout.addWidget(self.btn_duplicate)

        self.btn_delete = self._create_action_button("🗑️ Delete", "Delete selected row", self._delete_row, "danger")
        actions_layout.addWidget(self.btn_delete)

        self.btn_bulk_delete = self._create_action_button("💥 Bulk Delete", "Delete multiple rows", self._bulk_delete, "danger")
        actions_layout.addWidget(self.btn_bulk_delete)

        layout.addLayout(actions_layout)

        # Advanced operations
        advanced_layout = QHBoxLayout()
        advanced_layout.setSpacing(5)

        self.btn_export = self._create_action_button("📤 Export", "Export table to CSV", self._export_table)
        advanced_layout.addWidget(self.btn_export)

        self.btn_import = self._create_action_button("📥 Import", "Import data from CSV", self._import_table)
        advanced_layout.addWidget(self.btn_import)

        self.btn_clear = self._create_action_button("🧹 Clear All", "Clear all data from table", self._clear_table, "warning")
        advanced_layout.addWidget(self.btn_clear)

        layout.addLayout(advanced_layout)

        layout.addStretch()

        # Enhanced filter section
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(5)

        filter_icon = QLabel("🔍")
        filter_icon.setStyleSheet("font-size: 14px;")
        filter_layout.addWidget(filter_icon)

        filter_label = QLabel("Filter:")
        filter_label.setStyleSheet("font-weight: bold;")
        filter_layout.addWidget(filter_label)

        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Search in table data...")
        self.filter_input.setMinimumWidth(200)
        self.filter_input.setStyleSheet("font-size: 10pt; padding: 5px;")
        self.filter_input.textChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.filter_input)

        self.btn_clear_filter = self._create_action_button("❌", "Clear filter", lambda: self.filter_input.clear())
        self.btn_clear_filter.setMaximumWidth(40)
        filter_layout.addWidget(self.btn_clear_filter)

        layout.addLayout(filter_layout)

        controls.setLayout(layout)
        return controls

    def _create_action_button(self, text, tooltip, callback, style=""):
        """Create a styled action button"""
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        btn.clicked.connect(callback)

        if style == "danger":
            btn.setObjectName("danger")
        elif style == "success":
            btn.setObjectName("success")
        elif style == "warning":
            btn.setObjectName("warning")

        btn.setStyleSheet("""
            QPushButton {
                font-size: 10pt;
                font-weight: 600;
                padding: 8px 12px;
                border-radius: 4px;
                min-width: 80px;
            }
        """)

        return btn

    def _create_table(self):
        """Create the ultimate editable table"""
        table = QTableWidget()
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.ExtendedSelection)

        # CRITICAL: Enable editing properly
        table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.AnyKeyPressed)

        # Connect signals for editing
        table.itemChanged.connect(self._on_cell_changed)
        table.itemDoubleClicked.connect(self._on_cell_double_clicked)
        table.itemSelectionChanged.connect(self._on_selection_changed)

        # Context menu
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_table_context_menu)

        # Header settings
        header = table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSortIndicatorShown(True)
        header.sectionClicked.connect(self._on_header_clicked)

        # Style the table
        table.setStyleSheet("""
            QTableWidget {
                gridline-color: #404040;
                selection-background-color: #264f78;
                selection-color: #ffffff;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333333;
            }
            QTableWidget::item:selected {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #264f78, stop:1 #1a4d7a);
            }
        """)

        return table

    def _create_status_widget(self):
        """Create the status and info widget"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 10, 0, 0)

        # Status label
        self.status = QLabel("Select a table from the dropdown above")
        self.status.setStyleSheet("""
            padding: 10px;
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #2d2d30, stop:1 #1e1e1e);
            border-radius: 6px;
            border: 1px solid #3e3e42;
            font-size: 10pt;
            color: #e6e6e6;
        """)
        layout.addWidget(self.status)

        layout.addStretch()

        # Info labels
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #cccccc; font-size: 9pt;")
        layout.addWidget(self.info_label)

        widget.setLayout(layout)
        return widget

    def _load_tables(self):
        """Load tables into combo box"""
        if not self.manager.connection:
            return

        try:
            cursor = self.manager.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = cursor.fetchall()

            self.table_combo.clear()
            self.table_combo.addItem("-- Select Table --")
            for table in tables:
                self.table_combo.addItem(table[0])

        except Exception as e:
            QMessageBox.critical(self.manager.parent, "Load Error", f"Failed to load tables:\n{str(e)}")

    def _load_table(self, table_name):
        """Load table data with enhanced features"""
        if not table_name or table_name == "-- Select Table --":
            self.current_table = None
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            self.status.setText("Select a table from the dropdown above")
            return

        self.current_table = table_name
        self._refresh_data()

    def _refresh_data(self):
        """Refresh the current table data"""
        if not self.current_table or not self.manager.connection:
            return

        try:
            self.manager.progress_bar.setVisible(True)
            self.manager.progress_bar.setRange(0, 0)  # Indeterminate progress
            QApplication.processEvents()

            cursor = self.manager.connection.cursor()

            # Get column information
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            column_types = {col[1]: col[2] for col in columns}

            # Build and execute query
            query = f"SELECT * FROM {self.current_table}"
            params = []

            if self.filter_text:
                # Advanced filtering - search in all text columns
                text_columns = [col for col, type_ in column_types.items()
                              if 'TEXT' in type_.upper() or 'VARCHAR' in type_.upper() or 'CHAR' in type_.upper()]

                if text_columns:
                    conditions = [f"{col} LIKE ?" for col in text_columns]
                    query += f" WHERE {' OR '.join(conditions)}"
                    params = [f'%{self.filter_text}%'] * len(text_columns)
                else:
                    # If no text columns, search in all columns
                    conditions = [f"CAST({col} AS TEXT) LIKE ?" for col in column_names]
                    query += f" WHERE {' OR '.join(conditions)}"
                    params = [f'%{self.filter_text}%'] * len(column_names)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Update table
            self.table.setColumnCount(len(column_names))
            self.table.setHorizontalHeaderLabels(column_names)
            self.table.setRowCount(len(rows))

            # Store original data for rollback
            self.original_data.clear()

            for row_idx, row in enumerate(rows):
                for col_idx, value in enumerate(row):
                    col_name = column_names[col_idx]

                    # Create editable item
                    item = QTableWidgetItem(str(value) if value is not None else "")
                    item.setData(Qt.UserRole, value)  # Store original value
                    item.setData(Qt.UserRole + 1, column_types[col_name])  # Store column type

                    # Make item editable
                    item.setFlags(item.flags() | Qt.ItemIsEditable)

                    self.table.setItem(row_idx, col_idx, item)

                    # Store original data
                    self.original_data[(row_idx, col_idx)] = value

            # Resize columns and apply sorting
            self.table.resizeColumnsToContents()
            if self.sort_column >= 0:
                self.table.sortItems(self.sort_column, self.sort_order)

            # Update status and info
            filter_info = f" (filtered: '{self.filter_text}')" if self.filter_text else ""
            self.status.setText(f"✅ Loaded {len(rows):,} rows from '{self.current_table}'{filter_info}")
            self.info_label.setText(f"Columns: {len(column_names)} | Sort: {column_names[self.sort_column] if self.sort_column >= 0 else 'None'}")

            self.manager.rows_label.setText(f"📊 {len(rows):,} rows")
            self.manager.status_message.setText(f"Loaded table '{self.current_table}' with {len(rows):,} rows")

        except Exception as e:
            self.status.setText(f"❌ Error: {str(e)}")
            QMessageBox.critical(self.manager.parent, "Load Error", f"Failed to load table '{self.current_table}':\n{str(e)}")
        finally:
            self.manager.progress_bar.setVisible(False)

    def _on_cell_changed(self, item):
        """Handle cell editing and update database - THIS IS THE KEY METHOD!"""
        if not self.current_table or not self.manager.connection:
            return

        try:
            row = item.row()
            col = item.column()
            new_value = item.text()
            original_value = item.data(Qt.UserRole)
            column_type = item.data(Qt.UserRole + 1)

            # Skip if value hasn't changed
            if str(new_value) == str(original_value if original_value is not None else ""):
                return

            # Get column information
            cursor = self.manager.connection.cursor()
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns = cursor.fetchall()
            column_name = columns[col][1]

            # Find primary key for this table
            pk_column = None
            pk_index = None
            for i, col_info in enumerate(columns):
                if col_info[5]:  # pk flag
                    pk_column = col_info[1]
                    pk_index = i
                    break

            if not pk_column:
                QMessageBox.warning(self.manager.parent, "Cannot Update",
                    f"Table '{self.current_table}' has no primary key.\n"
                    "Cannot update rows without a primary key for identification.")
                # Revert the change
                item.setText(str(original_value) if original_value is not None else "")
                return

            # Get the primary key value for this row
            pk_item = self.table.item(row, pk_index)
            if not pk_item:
                QMessageBox.warning(self.manager.parent, "Error", "Cannot identify row to update.")
                item.setText(str(original_value) if original_value is not None else "")
                return

            pk_value = pk_item.text()

            # Type conversion based on column type
            try:
                if 'INTEGER' in column_type.upper() or 'INT' in column_type.upper():
                    if new_value.strip() == "":
                        converted_value = None
                    else:
                        converted_value = int(new_value)
                elif 'REAL' in column_type.upper() or 'FLOAT' in column_type.upper() or 'DOUBLE' in column_type.upper():
                    if new_value.strip() == "":
                        converted_value = None
                    else:
                        converted_value = float(new_value)
                else:
                    converted_value = new_value  # TEXT, VARCHAR, etc.
            except ValueError:
                QMessageBox.warning(self.manager.parent, "Invalid Value",
                    f"Value '{new_value}' is not valid for column type {column_type}.")
                item.setText(str(original_value) if original_value is not None else "")
                return

            # Update the database
            cursor.execute(f"UPDATE {self.current_table} SET {column_name} = ? WHERE {pk_column} = ?",
                          (converted_value, pk_value))
            self.manager.connection.commit()

            # Update stored original value
            item.setData(Qt.UserRole, converted_value)
            self.original_data[(row, col)] = converted_value

            self.status.setText(f"✅ Updated {column_name} = '{converted_value}' in '{self.current_table}'")
            self.manager.status_message.setText("Cell updated successfully")

        except Exception as e:
            QMessageBox.critical(self.manager.parent, "Update Error", f"Failed to update cell:\n{str(e)}")
            # Revert the change
            item.setText(str(original_value) if original_value is not None else "")

    def _on_cell_double_clicked(self, item):
        """Handle double-click for advanced editing"""
        if not self.current_table or not self.manager.connection:
            return

        try:
            row = item.row()
            col = item.column()
            column_name = self.table.horizontalHeaderItem(col).text()
            current_value = item.text()
            column_type = item.data(Qt.UserRole + 1)

            # Create appropriate edit dialog based on data type
            dialog = QDialog(self.manager.parent)
            dialog.setWindowTitle(f"Advanced Edit - {column_name}")
            dialog.setModal(True)
            dialog.resize(500, 300)

            layout = QVBoxLayout()

            # Header with current value
            header = QLabel(f"Editing: <b>{column_name}</b> (Row {row + 1})")
            header.setStyleSheet("font-size: 12pt; margin-bottom: 10px;")
            layout.addWidget(header)

            current_label = QLabel(f"Current value: <code>{current_value}</code>")
            current_label.setStyleSheet("color: #666; font-style: italic; margin-bottom: 15px;")
            layout.addWidget(current_label)

            # Input field based on type
            input_field = self._create_input_field(column_type, current_value)
            layout.addWidget(QLabel(f"New value ({column_type}):"))
            layout.addWidget(input_field)

            # Buttons
            button_layout = QHBoxLayout()
            button_layout.addStretch()

            cancel_btn = QPushButton("❌ Cancel")
            cancel_btn.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_btn)

            save_btn = QPushButton("💾 Save Changes")
            save_btn.setObjectName("success")
            save_btn.clicked.connect(lambda: self._save_advanced_edit(dialog, input_field, item))
            button_layout.addWidget(save_btn)

            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self.manager.parent, "Edit Error", f"Failed to open edit dialog:\n{str(e)}")

    def _create_input_field(self, column_type, current_value):
        """Create appropriate input field based on column type"""
        if 'TEXT' in column_type.upper() or 'VARCHAR' in column_type.upper() or 'CHAR' in column_type.upper():
            # Multi-line text input
            input_field = QTextEdit()
            input_field.setPlainText(current_value)
            input_field.setMaximumHeight(150)
        elif 'INTEGER' in column_type.upper() or 'INT' in column_type.upper():
            # Number input with validation
            input_field = QSpinBox()
            input_field.setRange(-2147483648, 2147483647)
            try:
                input_field.setValue(int(current_value) if current_value else 0)
            except:
                input_field.setValue(0)
        elif 'REAL' in column_type.upper() or 'FLOAT' in column_type.upper() or 'DOUBLE' in column_type.upper():
            # Decimal input
            input_field = QDoubleSpinBox()
            input_field.setRange(-1e308, 1e308)
            input_field.setDecimals(6)
            try:
                input_field.setValue(float(current_value) if current_value else 0.0)
            except:
                input_field.setValue(0.0)
        elif 'BLOB' in column_type.upper():
            # Binary data - show as hex
            input_field = QTextEdit()
            input_field.setPlainText("BLOB data cannot be edited in this interface")
            input_field.setReadOnly(True)
        else:
            # Default to single-line text
            input_field = QLineEdit(current_value)

        return input_field

    def _save_advanced_edit(self, dialog, input_field, table_item):
        """Save the advanced edit value"""
        try:
            # Get new value based on input type
            if isinstance(input_field, QTextEdit):
                if input_field.isReadOnly():
                    dialog.reject()
                    return
                new_value = input_field.toPlainText()
            elif isinstance(input_field, QSpinBox):
                new_value = input_field.value()
            elif isinstance(input_field, QDoubleSpinBox):
                new_value = input_field.value()
            else:
                new_value = input_field.text()

            # Update table item
            table_item.setText(str(new_value))

            dialog.accept()

        except Exception as e:
            QMessageBox.critical(dialog, "Save Error", f"Failed to save value:\n{str(e)}")

    def _on_selection_changed(self):
        """Handle selection changes"""
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if selected_rows:
            self.info_label.setText(f"Selected: {len(selected_rows)} row{'s' if len(selected_rows) > 1 else ''}")
        else:
            self.info_label.setText("")

    def _on_header_clicked(self, column):
        """Handle header click for sorting"""
        if column == self.sort_column:
            # Toggle sort order
            self.sort_order = Qt.DescendingOrder if self.sort_order == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            self.sort_column = column
            self.sort_order = Qt.AscendingOrder

        self.table.sortItems(column, self.sort_order)
        self.table.horizontalHeader().setSortIndicator(column, self.sort_order)

    def _show_table_context_menu(self, position):
        """Show context menu for table"""
        if not self.current_table:
            return

        menu = QMenu()

        # Selection-based actions
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if selected_rows:
            menu.addAction(f"📋 Copy {len(selected_rows)} row{'s' if len(selected_rows) > 1 else ''}", self._copy_selected)
            menu.addAction(f"📄 Duplicate {len(selected_rows)} row{'s' if len(selected_rows) > 1 else ''}", self._duplicate_selected)
            menu.addSeparator()
            menu.addAction(f"🗑️ Delete {len(selected_rows)} row{'s' if len(selected_rows) > 1 else ''}", self._delete_selected)

        menu.addSeparator()
        menu.addAction("➕ Insert Row Above", self._insert_row_above)
        menu.addAction("➕ Insert Row Below", self._insert_row_below)
        menu.addSeparator()
        menu.addAction("🔄 Refresh Data", self._refresh_data)
        menu.addAction("📊 Show Statistics", self._show_table_stats)

        menu.exec(self.table.viewport().mapToGlobal(position))

    def _apply_filter(self, text):
        """Apply filter to table"""
        self.filter_text = text.strip()
        self._refresh_data()

    def _add_row(self):
        """Add a new row to the table"""
        if not self.current_table or not self.manager.connection:
            return

        try:
            cursor = self.manager.connection.cursor()

            # Get column information
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]
            column_types = {col[1]: col[2] for col in columns}

            # Create input dialog
            dialog = QDialog(self.manager.parent)
            dialog.setWindowTitle(f"Add New Row to {self.current_table}")
            dialog.setModal(True)
            dialog.resize(600, 400)

            layout = QVBoxLayout()

            # Header
            header = QLabel(f"Adding new row to <b>{self.current_table}</b>")
            header.setStyleSheet("font-size: 12pt; margin-bottom: 10px;")
            layout.addWidget(header)

            # Scroll area for many columns
            scroll = QScrollArea()
            scroll_widget = QWidget()
            scroll_layout = QFormLayout()

            input_fields = {}

            for col_name, col_type in column_types.items():
                label = QLabel(f"{col_name} ({col_type}):")
                label.setStyleSheet("font-weight: bold;")

                input_field = self._create_input_field(col_type, "")
                input_fields[col_name] = input_field

                scroll_layout.addRow(label, input_field)

            scroll_widget.setLayout(scroll_layout)
            scroll.setWidget(scroll_widget)
            scroll.setWidgetResizable(True)
            layout.addWidget(scroll)

            # Buttons
            button_layout = QHBoxLayout()
            button_layout.addStretch()

            cancel_btn = QPushButton("❌ Cancel")
            cancel_btn.clicked.connect(dialog.reject)
            button_layout.addWidget(cancel_btn)

            add_btn = QPushButton("➕ Add Row")
            add_btn.setObjectName("success")
            add_btn.clicked.connect(lambda: self._save_new_row(dialog, input_fields, column_names))
            button_layout.addWidget(add_btn)

            layout.addLayout(button_layout)
            dialog.setLayout(layout)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self.manager.parent, "Add Row Error", f"Failed to add row:\n{str(e)}")

    def _save_new_row(self, dialog, input_fields, column_names):
        """Save the new row to database"""
        try:
            values = []
            placeholders = []

            for col_name in column_names:
                input_field = input_fields[col_name]
                col_type = ""  # We don't need type here for insertion

                # Get value based on input type
                if isinstance(input_field, QTextEdit):
                    value = input_field.toPlainText()
                elif isinstance(input_field, QSpinBox):
                    value = input_field.value()
                elif isinstance(input_field, QDoubleSpinBox):
                    value = input_field.value()
                else:
                    value = input_field.text()

                values.append(value)
                placeholders.append("?")

            # Insert into database
            cursor = self.manager.connection.cursor()
            query = f"INSERT INTO {self.current_table} ({', '.join(column_names)}) VALUES ({', '.join(placeholders)})"
            cursor.execute(query, values)
            self.manager.connection.commit()

            # Refresh table
            self._refresh_data()

            self.status.setText(f"✅ Added new row to '{self.current_table}'")
            self.manager.status_message.setText("Row added successfully")

            dialog.accept()

        except Exception as e:
            QMessageBox.critical(dialog, "Save Error", f"Failed to save new row:\n{str(e)}")

    def _duplicate_row(self):
        """Duplicate the selected row"""
        if not self.current_table or not self.manager.connection:
            return

        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.information(self.manager.parent, "No Selection", "Please select a row to duplicate.")
            return

        if len(selected_rows) > 1:
            QMessageBox.information(self.manager.parent, "Multiple Selection", "Please select only one row to duplicate.")
            return

        row = list(selected_rows)[0]

        try:
            cursor = self.manager.connection.cursor()

            # Get column information
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]

            # Get values from selected row
            values = []
            for col in range(len(column_names)):
                item = self.table.item(row, col)
                if item:
                    values.append(item.text())
                else:
                    values.append("")

            # Find auto-increment primary key
            pk_column = None
            for col in columns:
                if col[5]:  # pk flag
                    pk_column = col[1]
                    break

            # Remove auto-increment PK value if it exists
            if pk_column and pk_column in column_names:
                pk_index = column_names.index(pk_column)
                values[pk_index] = None  # Let SQLite auto-assign

            # Insert duplicate
            placeholders = ["?" for _ in values]
            query = f"INSERT INTO {self.current_table} ({', '.join(column_names)}) VALUES ({', '.join(placeholders)})"
            cursor.execute(query, values)
            self.manager.connection.commit()

            # Refresh table
            self._refresh_data()

            self.status.setText(f"✅ Duplicated row in '{self.current_table}'")
            self.manager.status_message.setText("Row duplicated successfully")

        except Exception as e:
            QMessageBox.critical(self.manager.parent, "Duplicate Error", f"Failed to duplicate row:\n{str(e)}")

    def _delete_row(self):
        """Delete the selected row"""
        if not self.current_table or not self.manager.connection:
            return

        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.information(self.manager.parent, "No Selection", "Please select a row to delete.")
            return

        if len(selected_rows) > 1:
            QMessageBox.information(self.manager.parent, "Multiple Selection", "Please select only one row to delete. Use 'Bulk Delete' for multiple rows.")
            return

        row = list(selected_rows)[0]

        # Confirm deletion
        reply = QMessageBox.question(self.manager.parent, "Confirm Delete",
            f"Are you sure you want to delete this row from '{self.current_table}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply != QMessageBox.Yes:
            return

        try:
            cursor = self.manager.connection.cursor()

            # Get primary key
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns = cursor.fetchall()

            pk_column = None
            pk_index = None
            for i, col_info in enumerate(columns):
                if col_info[5]:  # pk flag
                    pk_column = col_info[1]
                    pk_index = i
                    break

            if not pk_column:
                QMessageBox.warning(self.manager.parent, "Cannot Delete",
                    f"Table '{self.current_table}' has no primary key.\n"
                    "Cannot delete rows without a primary key for identification.")
                return

            # Get PK value
            pk_item = self.table.item(row, pk_index)
            if not pk_item:
                QMessageBox.warning(self.manager.parent, "Error", "Cannot identify row to delete.")
                return

            pk_value = pk_item.text()

            # Delete from database
            cursor.execute(f"DELETE FROM {self.current_table} WHERE {pk_column} = ?", (pk_value,))
            self.manager.connection.commit()

            # Refresh table
            self._refresh_data()

            self.status.setText(f"✅ Deleted row from '{self.current_table}'")
            self.manager.status_message.setText("Row deleted successfully")

        except Exception as e:
            QMessageBox.critical(self.manager.parent, "Delete Error", f"Failed to delete row:\n{str(e)}")

    def _bulk_delete(self):
        """Delete multiple selected rows"""
        if not self.current_table or not self.manager.connection:
            return

        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.information(self.manager.parent, "No Selection", "Please select rows to delete.")
            return

        # Confirm bulk deletion
        reply = QMessageBox.question(self.manager.parent, "Confirm Bulk Delete",
            f"Are you sure you want to delete {len(selected_rows)} rows from '{self.current_table}'?\n\n"
            "This action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply != QMessageBox.Yes:
            return

        try:
            cursor = self.manager.connection.cursor()

            # Get primary key
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns = cursor.fetchall()

            pk_column = None
            pk_index = None
            for i, col_info in enumerate(columns):
                if col_info[5]:  # pk flag
                    pk_column = col_info[1]
                    pk_index = i
                    break

            if not pk_column:
                QMessageBox.warning(self.manager.parent, "Cannot Delete",
                    f"Table '{self.current_table}' has no primary key.\n"
                    "Cannot delete rows without a primary key for identification.")
                return

            # Delete each selected row
            deleted_count = 0
            for row in selected_rows:
                pk_item = self.table.item(row, pk_index)
                if pk_item:
                    pk_value = pk_item.text()
                    cursor.execute(f"DELETE FROM {self.current_table} WHERE {pk_column} = ?", (pk_value,))
                    deleted_count += 1

            self.manager.connection.commit()

            # Refresh table
            self._refresh_data()

            self.status.setText(f"✅ Deleted {deleted_count} rows from '{self.current_table}'")
            self.manager.status_message.setText(f"Bulk delete completed: {deleted_count} rows removed")

        except Exception as e:
            QMessageBox.critical(self.manager.parent, "Bulk Delete Error", f"Failed to delete rows:\n{str(e)}")

    def _export_table(self):
        """Export table to CSV"""
        if not self.current_table:
            return

        try:
            filename, _ = QFileDialog.getSaveFileName(
                self.manager.parent, "Export Table to CSV",
                f"{self.current_table}.csv", "CSV Files (*.csv);;All Files (*)")

            if not filename:
                return

            cursor = self.manager.connection.cursor()
            cursor.execute(f"SELECT * FROM {self.current_table}")
            rows = cursor.fetchall()

            # Get column names
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns = cursor.fetchall()
            column_names = [col[1] for col in columns]

            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(column_names)
                writer.writerows(rows)

            self.status.setText(f"✅ Exported {len(rows)} rows to '{filename}'")
            self.manager.status_message.setText(f"Table exported successfully")

            QMessageBox.information(self.manager.parent, "Export Complete",
                f"Successfully exported {len(rows)} rows to:\n{filename}")

        except Exception as e:
            QMessageBox.critical(self.manager.parent, "Export Error", f"Failed to export table:\n{str(e)}")

    def _import_table(self):
        """Import data from CSV"""
        if not self.current_table:
            return

        try:
            filename, _ = QFileDialog.getOpenFileName(
                self.manager.parent, "Import CSV to Table",
                "", "CSV Files (*.csv);;All Files (*)")

            if not filename:
                return

            # Confirm import
            reply = QMessageBox.question(self.manager.parent, "Confirm Import",
                f"Are you sure you want to import data from '{filename}' into '{self.current_table}'?\n\n"
                "This will add new rows to the table.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

            if reply != QMessageBox.Yes:
                return

            # Read CSV
            with open(filename, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                headers = next(reader)
                rows = list(reader)

            if not rows:
                QMessageBox.information(self.manager.parent, "Import Complete", "No data rows found in CSV file.")
                return

            cursor = self.manager.connection.cursor()

            # Get table columns
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            table_columns = [col[1] for col in cursor.fetchall()]

            # Check if headers match
            if headers != table_columns:
                QMessageBox.warning(self.manager.parent, "Column Mismatch",
                    f"CSV headers don't match table columns.\n\n"
                    f"Expected: {', '.join(table_columns)}\n"
                    f"Found: {', '.join(headers)}\n\n"
                    "Import cancelled.")
                return

            # Insert rows
            placeholders = ["?" for _ in headers]
            query = f"INSERT INTO {self.current_table} ({', '.join(headers)}) VALUES ({', '.join(placeholders)})"

            imported_count = 0
            for row in rows:
                try:
                    cursor.execute(query, row)
                    imported_count += 1
                except Exception as e:
                    QMessageBox.warning(self.manager.parent, "Import Error",
                        f"Failed to import row {imported_count + 1}: {str(e)}\n"
                        "Continuing with remaining rows...")

            self.manager.connection.commit()

            # Refresh table
            self._refresh_data()

            self.status.setText(f"✅ Imported {imported_count} rows from '{filename}'")
            self.manager.status_message.setText(f"Import completed: {imported_count} rows added")

            QMessageBox.information(self.manager.parent, "Import Complete",
                f"Successfully imported {imported_count} rows from:\n{filename}")

        except Exception as e:
            QMessageBox.critical(self.manager.parent, "Import Error", f"Failed to import data:\n{str(e)}")

    def _clear_table(self):
        """Clear all data from table"""
        if not self.current_table:
            return

        # Confirm clear
        reply = QMessageBox.question(self.manager.parent, "Confirm Clear Table",
            f"Are you sure you want to delete ALL data from '{self.current_table}'?\n\n"
            "This action cannot be undone!",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply != QMessageBox.Yes:
            return

        try:
            cursor = self.manager.connection.cursor()
            cursor.execute(f"DELETE FROM {self.current_table}")
            deleted_count = cursor.rowcount
            self.manager.connection.commit()

            # Refresh table
            self._refresh_data()

            self.status.setText(f"✅ Cleared {deleted_count} rows from '{self.current_table}'")
            self.manager.status_message.setText(f"Table cleared: {deleted_count} rows removed")

        except Exception as e:
            QMessageBox.critical(self.manager.parent, "Clear Error", f"Failed to clear table:\n{str(e)}")

    # Placeholder methods for context menu
    def _copy_selected(self):
        QMessageBox.information(self.manager.parent, "Not Implemented", "Copy functionality coming soon!")

    def _duplicate_selected(self):
        QMessageBox.information(self.manager.parent, "Not Implemented", "Bulk duplicate functionality coming soon!")

    def _delete_selected(self):
        self._bulk_delete()

    def _insert_row_above(self):
        QMessageBox.information(self.manager.parent, "Not Implemented", "Insert row functionality coming soon!")

    def _insert_row_below(self):
        QMessageBox.information(self.manager.parent, "Not Implemented", "Insert row functionality coming soon!")

    def _show_table_stats(self):
        """Show table statistics"""
        if not self.current_table:
            return

        try:
            cursor = self.manager.connection.cursor()

            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {self.current_table}")
            row_count = cursor.fetchone()[0]

            # Get column info
            cursor.execute(f"PRAGMA table_info({self.current_table})")
            columns = cursor.fetchall()

            # Get index info
            cursor.execute(f"PRAGMA index_list({self.current_table})")
            indexes = cursor.fetchall()

            # Show stats dialog
            dialog = QDialog(self.manager.parent)
            dialog.setWindowTitle(f"Statistics - {self.current_table}")
            dialog.setModal(True)
            dialog.resize(400, 300)

            layout = QVBoxLayout()

            # Header
            header = QLabel(f"<h2>📊 {self.current_table}</h2>")
            layout.addWidget(header)

            # Stats
            stats_text = f"""
            <b>Rows:</b> {row_count:,}<br>
            <b>Columns:</b> {len(columns)}<br>
            <b>Indexes:</b> {len(indexes)}<br><br>
            """

            # Column details
            stats_text += "<b>Columns:</b><br>"
            for col in columns:
                pk_marker = " 🔑" if col[5] else ""
                nullable = "NULL" if col[3] else "NOT NULL"
                default = f" DEFAULT {col[4]}" if col[4] else ""
                stats_text += f"• {col[1]} ({col[2]}) {nullable}{default}{pk_marker}<br>"

            stats_label = QLabel(stats_text)
            stats_label.setWordWrap(True)
            layout.addWidget(stats_label)

            # Close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(dialog.accept)
            layout.addWidget(close_btn)

            dialog.setLayout(layout)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self.manager.parent, "Stats Error", f"Failed to show statistics:\n{str(e)}")


class SQLEditorTab:
    """Advanced SQL Editor with multi-query execution and results"""

    def __init__(self, manager):
        self.manager = manager
        self.query_history = []
        self.current_results_tab = None

    def create(self):
        """Create the SQL editor tab widget"""
        widget = QWidget()
        layout = QVBoxLayout()

        # SQL Editor
        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("Enter your SQL queries here...\n\nExample:\nSELECT * FROM users;\nSELECT COUNT(*) FROM products;")
        self.editor.setFont(QFont("Consolas", 10))

        # Syntax highlighting placeholder
        self._setup_editor_highlighting()

        layout.addWidget(self.editor)

        # Controls
        controls = self._create_controls()
        layout.addWidget(controls)

        # Results area
        self.results_tabs = QTabWidget()
        self.results_tabs.setTabsClosable(True)
        self.results_tabs.tabCloseRequested.connect(self._close_results_tab)
        layout.addWidget(self.results_tabs)

        widget.setLayout(layout)
        return widget

    def _create_controls(self):
        """Create control buttons"""
        controls = QWidget()
        layout = QHBoxLayout()

        # Execute buttons
        self.btn_execute = QPushButton("▶️ Execute")
        self.btn_execute.setObjectName("success")
        self.btn_execute.clicked.connect(self._execute_query)
        layout.addWidget(self.btn_execute)

        self.btn_execute_selection = QPushButton("▶️ Execute Selection")
        self.btn_execute_selection.clicked.connect(self._execute_selection)
        layout.addWidget(self.btn_execute_selection)

        # History
        self.btn_history = QPushButton("📚 History")
        self.btn_history.clicked.connect(self._show_history)
        layout.addWidget(self.btn_history)

        # Export
        self.btn_export_results = QPushButton("📤 Export Results")
        self.btn_export_results.clicked.connect(self._export_results)
        layout.addWidget(self.btn_export_results)

        layout.addStretch()

        # Status
        self.query_status = QLabel("Ready")
        self.query_status.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.query_status)

        controls.setLayout(layout)
        return controls

    def _setup_editor_highlighting(self):
        """Setup basic syntax highlighting"""
        # Placeholder for syntax highlighting
        pass

    def _execute_query(self):
        """Execute the full query"""
        if not self.manager.connection:
            return

        query = self.editor.toPlainText().strip()
        if not query:
            return

        self._execute_sql(query, "Full Query")

    def _execute_selection(self):
        """Execute selected text"""
        if not self.manager.connection:
            return

        selected_text = self.editor.textCursor().selectedText()
        if not selected_text.strip():
            return

        self._execute_sql(selected_text, "Selection")

    def _execute_sql(self, sql, title):
        """Execute SQL and show results"""
        try:
            self.manager.progress_bar.setVisible(True)
            self.manager.progress_bar.setRange(0, 0)
            QApplication.processEvents()

            # Split multi-query
            queries = [q.strip() for q in sql.split(';') if q.strip()]

            if not queries:
                return

            # Create results tab
            results_widget = QWidget()
            layout = QVBoxLayout()

            # Execute each query
            for i, query in enumerate(queries):
                if not query:
                    continue

                try:
                    cursor = self.manager.connection.cursor()
                    start_time = time.time()

                    # Execute query
                    cursor.execute(query)
                    execution_time = time.time() - start_time

                    # Get results
                    if query.strip().upper().startswith(('SELECT', 'PRAGMA', 'EXPLAIN')):
                        rows = cursor.fetchall()

                        # Get column names
                        if cursor.description:
                            columns = [desc[0] for desc in cursor.description]
                        else:
                            columns = []

                        # Create results table
                        table = QTableWidget()
                        table.setColumnCount(len(columns))
                        table.setHorizontalHeaderLabels(columns)
                        table.setRowCount(len(rows))
                        table.setAlternatingRowColors(True)

                        for row_idx, row in enumerate(rows):
                            for col_idx, value in enumerate(row):
                                item = QTableWidgetItem(str(value) if value is not None else "")
                                table.setItem(row_idx, col_idx, item)

                        table.resizeColumnsToContents()

                        # Add to layout
                        query_label = QLabel(f"Query {i+1}: {query[:50]}{'...' if len(query) > 50 else ''}")
                        query_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
                        layout.addWidget(query_label)

                        result_info = QLabel(f"📊 {len(rows):,} rows returned in {execution_time:.3f}s")
                        result_info.setStyleSheet("color: #666; font-size: 9pt;")
                        layout.addWidget(result_info)

                        layout.addWidget(table)

                    else:
                        # Non-SELECT query
                        affected_rows = cursor.rowcount
                        self.manager.connection.commit()

                        result_label = QLabel(f"✅ Query {i+1} executed successfully")
                        result_label.setStyleSheet("color: green; font-weight: bold;")
                        layout.addWidget(result_label)

                        info_label = QLabel(f"Affected rows: {affected_rows} | Time: {execution_time:.3f}s")
                        info_label.setStyleSheet("color: #666;")
                        layout.addWidget(info_label)

                        code_label = QLabel(f"<code>{query}</code>")
                        layout.addWidget(code_label)

                except Exception as e:
                    error_label = QLabel(f"❌ Query {i+1} failed: {str(e)}")
                    error_label.setStyleSheet("color: red;")
                    layout.addWidget(error_label)

                    error_code = QLabel(f"<code>{query}</code>")
                    error_code.setStyleSheet("color: #666;")
                    layout.addWidget(error_code)

            results_widget.setLayout(layout)

            # Add to tabs
            tab_title = f"{title} ({len(queries)} queries)"
            tab_index = self.results_tabs.addTab(results_widget, tab_title)
            self.results_tabs.setCurrentIndex(tab_index)

            # Add to history
            self.query_history.append({
                'sql': sql,
                'timestamp': datetime.now(),
                'title': title
            })

            self.query_status.setText(f"✅ Executed {len(queries)} queries")
            self.manager.status_message.setText("SQL execution completed")

        except Exception as e:
            QMessageBox.critical(self.manager.parent, "Query Error", f"Failed to execute SQL:\n{str(e)}")
            self.query_status.setText(f"❌ Error: {str(e)}")
        finally:
            self.manager.progress_bar.setVisible(False)

    def _close_results_tab(self, index):
        """Close a results tab"""
        self.results_tabs.removeTab(index)

    def _show_history(self):
        """Show query history"""
        dialog = QDialog(self.manager.parent)
        dialog.setWindowTitle("Query History")
        dialog.setModal(True)
        dialog.resize(600, 400)

        layout = QVBoxLayout()

        # History list
        self.history_list = QListWidget()
        for item in reversed(self.query_history[-50:]):  # Last 50 queries
            list_item = QListWidgetItem(f"{item['timestamp'].strftime('%H:%M:%S')} - {item['title']}")
            list_item.setData(Qt.UserRole, item)
            self.history_list.addItem(list_item)

        self.history_list.itemDoubleClicked.connect(self._load_history_item)
        layout.addWidget(self.history_list)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        load_btn = QPushButton("📥 Load Query")
        load_btn.clicked.connect(lambda: self._load_history_item(self.history_list.currentItem()) if self.history_list.currentItem() else None)
        button_layout.addWidget(load_btn)

        clear_btn = QPushButton("🗑️ Clear History")
        clear_btn.clicked.connect(self._clear_history)
        button_layout.addWidget(clear_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        dialog.exec()

    def _load_history_item(self, item):
        """Load a history item into the editor"""
        if not item:
            return

        data = item.data(Qt.UserRole)
        self.editor.setPlainText(data['sql'])

        # Close dialog if it exists
        if hasattr(self, '_history_dialog'):
            self._history_dialog.accept()

    def _clear_history(self):
        """Clear query history"""
        self.query_history.clear()
        self.history_list.clear()

    def _export_results(self):
        """Export current results tab"""
        current_tab = self.results_tabs.currentWidget()
        if not current_tab:
            QMessageBox.information(self.manager.parent, "No Results", "No results to export.")
            return

        # This would need to be implemented to export the current results
        QMessageBox.information(self.manager.parent, "Not Implemented", "Results export coming soon!")


class SchemaTab:
    """Schema viewer and editor"""

    def __init__(self, manager):
        self.manager = manager

    def create(self):
        """Create the schema tab widget"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Schema tree
        self.schema_tree = QTreeWidget()
        self.schema_tree.setHeaderLabel("Database Schema")
        self.schema_tree.itemDoubleClicked.connect(self._show_schema_details)
        layout.addWidget(self.schema_tree)

        # Controls
        controls = self._create_controls()
        layout.addWidget(controls)

        # Details area
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(200)
        layout.addWidget(self.details_text)

        widget.setLayout(layout)
        return widget

    def _create_controls(self):
        """Create control buttons"""
        controls = QWidget()
        layout = QHBoxLayout()

        self.btn_refresh = QPushButton("🔄 Refresh Schema")
        self.btn_refresh.clicked.connect(self._load_schema)
        layout.addWidget(self.btn_refresh)

        self.btn_create_table = QPushButton("➕ Create Table")
        self.btn_create_table.clicked.connect(self._create_table)
        layout.addWidget(self.btn_create_table)

        layout.addStretch()

        controls.setLayout(layout)
        return controls

    def _load_schema(self):
        """Load database schema"""
        if not self.manager.connection:
            return

        try:
            self.schema_tree.clear()
            cursor = self.manager.connection.cursor()

            # Tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = cursor.fetchall()

            for table in tables:
                table_item = QTreeWidgetItem(self.schema_tree, [f"📋 {table[0]}"])
                table_item.setData(0, Qt.UserRole, ('table', table[0]))

                # Columns
                cursor.execute(f"PRAGMA table_info({table[0]})")
                columns = cursor.fetchall()

                for col in columns:
                    pk_marker = " 🔑" if col[5] else ""
                    col_item = QTreeWidgetItem(table_item, [f"📄 {col[1]} ({col[2]}){pk_marker}"])
                    col_item.setData(0, Qt.UserRole, ('column', table[0], col[1]))

            # Indexes
            cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            indexes = cursor.fetchall()

            for index in indexes:
                index_item = QTreeWidgetItem(self.schema_tree, [f"🔍 {index[0]} (on {index[1]})"])
                index_item.setData(0, Qt.UserRole, ('index', index[0], index[1]))

        except Exception as e:
            QMessageBox.critical(self.manager.parent, "Schema Error", f"Failed to load schema:\n{str(e)}")

    def _show_schema_details(self, item):
        """Show details for selected schema item"""
        if not item:
            return

        data = item.data(0, Qt.UserRole)
        if not data:
            return

        item_type, *args = data

        try:
            cursor = self.manager.connection.cursor()
            details = f"Type: {item_type.upper()}\n"

            if item_type == 'table':
                table_name = args[0]
                details += f"Name: {table_name}\n\n"

                # Row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                details += f"Rows: {row_count:,}\n\n"

                # Columns
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                details += f"Columns ({len(columns)}):\n"
                for col in columns:
                    pk = " PRIMARY KEY" if col[5] else ""
                    nullable = "" if col[3] else " NOT NULL"
                    default = f" DEFAULT {col[4]}" if col[4] else ""
                    details += f"  - {col[1]} ({col[2]}){nullable}{default}{pk}\n"

                # Indexes
                cursor.execute(f"PRAGMA index_list({table_name})")
                indexes = cursor.fetchall()
                if indexes:
                    details += f"\nIndexes ({len(indexes)}):\n"
                    for idx in indexes:
                        details += f"  - {idx[1]}\n"

            elif item_type == 'column':
                table_name, col_name = args
                details += f"Table: {table_name}\n"
                details += f"Column: {col_name}\n\n"

                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                for col in columns:
                    if col[1] == col_name:
                        details += f"Type: {col[2]}\n"
                        details += f"Nullable: {'Yes' if col[3] else 'No'}\n"
                        details += f"Default: {col[4] if col[4] else 'None'}\n"
                        details += f"Primary Key: {'Yes' if col[5] else 'No'}\n"
                        break

            elif item_type == 'index':
                index_name, table_name = args
                details += f"Name: {index_name}\n"
                details += f"Table: {table_name}\n\n"

                cursor.execute(f"PRAGMA index_info({index_name})")
                index_cols = cursor.fetchall()
                details += f"Columns ({len(index_cols)}):\n"
                for col in index_cols:
                    details += f"  - {col[2]}\n"

            self.details_text.setPlainText(details)

        except Exception as e:
            self.details_text.setPlainText(f"Error loading details:\n{str(e)}")

    def _create_table(self):
        """Create a new table"""
        QMessageBox.information(self.manager.parent, "Not Implemented", "Table creation wizard coming soon!")


class ToolsTab:
    """Database maintenance and tools"""

    def __init__(self, manager):
        self.manager = manager

    def create(self):
        """Create the tools tab widget"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Tools list
        tools_group = QGroupBox("Database Maintenance")
        tools_layout = QVBoxLayout()

        # VACUUM
        vacuum_btn = QPushButton("🧹 VACUUM Database")
        vacuum_btn.setToolTip("Rebuild the database file, repacking it into a minimal amount of disk space")
        vacuum_btn.clicked.connect(self._vacuum_database)
        tools_layout.addWidget(vacuum_btn)

        # REINDEX
        reindex_btn = QPushButton("🔄 REINDEX Database")
        reindex_btn.setToolTip("Rebuild all indexes in the database")
        reindex_btn.clicked.connect(self._reindex_database)
        tools_layout.addWidget(reindex_btn)

        # ANALYZE
        analyze_btn = QPushButton("📊 ANALYZE Database")
        analyze_btn.setToolTip("Gather statistics about tables and indexes for the query optimizer")
        analyze_btn.clicked.connect(self._analyze_database)
        tools_layout.addWidget(analyze_btn)

        # Integrity Check
        integrity_btn = QPushButton("✅ Integrity Check")
        integrity_btn.setToolTip("Verify that the database is not corrupted")
        integrity_btn.clicked.connect(self._integrity_check)
        tools_layout.addWidget(integrity_btn)

        tools_group.setLayout(tools_layout)
        layout.addWidget(tools_group)

        # File operations
        file_group = QGroupBox("File Operations")
        file_layout = QVBoxLayout()

        # Backup
        backup_btn = QPushButton("💾 Create Backup")
        backup_btn.clicked.connect(self._create_backup)
        file_layout.addWidget(backup_btn)

        # Clone
        clone_btn = QPushButton("📋 Clone Database")
        clone_btn.clicked.connect(self._clone_database)
        file_layout.addWidget(clone_btn)

        # Optimize
        optimize_btn = QPushButton("⚡ Optimize Database")
        optimize_btn.clicked.connect(self._optimize_database)
        file_layout.addWidget(optimize_btn)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Results area
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        layout.addWidget(self.results_text)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _vacuum_database(self):
        """VACUUM the database"""
        if not self.manager.connection:
            return

        try:
            cursor = self.manager.connection.cursor()
            start_time = time.time()
            cursor.execute("VACUUM")
            execution_time = time.time() - start_time

            self.results_text.append(f"✅ VACUUM completed in {execution_time:.3f} seconds")
            self.manager.status_message.setText("Database vacuumed successfully")

        except Exception as e:
            self.results_text.append(f"❌ VACUUM failed: {str(e)}")
            QMessageBox.critical(self.manager.parent, "VACUUM Error", f"Failed to vacuum database:\n{str(e)}")

    def _reindex_database(self):
        """REINDEX the database"""
        if not self.manager.connection:
            return

        try:
            cursor = self.manager.connection.cursor()
            start_time = time.time()
            cursor.execute("REINDEX")
            execution_time = time.time() - start_time

            self.results_text.append(f"✅ REINDEX completed in {execution_time:.3f} seconds")
            self.manager.status_message.setText("Database reindexed successfully")

        except Exception as e:
            self.results_text.append(f"❌ REINDEX failed: {str(e)}")
            QMessageBox.critical(self.manager.parent, "REINDEX Error", f"Failed to reindex database:\n{str(e)}")

    def _analyze_database(self):
        """ANALYZE the database"""
        if not self.manager.connection:
            return

        try:
            cursor = self.manager.connection.cursor()
            start_time = time.time()
            cursor.execute("ANALYZE")
            execution_time = time.time() - start_time

            self.results_text.append(f"✅ ANALYZE completed in {execution_time:.3f} seconds")
            self.manager.status_message.setText("Database analyzed successfully")

        except Exception as e:
            self.results_text.append(f"❌ ANALYZE failed: {str(e)}")
            QMessageBox.critical(self.manager.parent, "ANALYZE Error", f"Failed to analyze database:\n{str(e)}")

    def _integrity_check(self):
        """Check database integrity"""
        if not self.manager.connection:
            return

        try:
            cursor = self.manager.connection.cursor()
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()

            if result and result[0] == "ok":
                self.results_text.append("✅ Integrity check passed - database is healthy")
                self.manager.status_message.setText("Database integrity verified")
            else:
                self.results_text.append(f"❌ Integrity check failed: {result[0] if result else 'Unknown error'}")
                QMessageBox.warning(self.manager.parent, "Integrity Issue", f"Database integrity check failed:\n{result[0] if result else 'Unknown error'}")

        except Exception as e:
            self.results_text.append(f"❌ Integrity check failed: {str(e)}")
            QMessageBox.critical(self.manager.parent, "Integrity Check Error", f"Failed to check integrity:\n{str(e)}")

    def _create_backup(self):
        """Create a database backup"""
        if not self.manager.db_path:
            return

        try:
            from shutil import copy2
            import os

            # Suggest backup filename
            db_dir = os.path.dirname(self.manager.db_path)
            db_name = os.path.basename(self.manager.db_path)
            name_without_ext = os.path.splitext(db_name)[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{name_without_ext}_backup_{timestamp}.db"

            backup_path, _ = QFileDialog.getSaveFileName(
                self.manager.parent, "Create Database Backup",
                os.path.join(db_dir, backup_name), "SQLite Database (*.db);;All Files (*)")

            if not backup_path:
                return

            # Close current connection temporarily
            self.manager.connection.close()
            self.manager.connection = None

            # Copy file
            copy2(self.manager.db_path, backup_path)

            # Reconnect
            self.manager._connect_to_database()

            self.results_text.append(f"✅ Backup created: {backup_path}")
            self.manager.status_message.setText("Database backup created successfully")

            QMessageBox.information(self.manager.parent, "Backup Complete",
                f"Database backup created successfully:\n{backup_path}")

        except Exception as e:
            self.results_text.append(f"❌ Backup failed: {str(e)}")
            QMessageBox.critical(self.manager.parent, "Backup Error", f"Failed to create backup:\n{str(e)}")

    def _clone_database(self):
        """Clone the database"""
        QMessageBox.information(self.manager.parent, "Not Implemented", "Database cloning coming soon!")

    def _optimize_database(self):
        """Optimize the database"""
        if not self.manager.connection:
            return

        try:
            self.results_text.append("🔄 Starting database optimization...")

            cursor = self.manager.connection.cursor()

            # Run optimization sequence
            operations = [
                ("VACUUM", "VACUUM"),
                ("REINDEX", "REINDEX"),
                ("ANALYZE", "ANALYZE")
            ]

            total_time = 0
            for name, sql in operations:
                start_time = time.time()
                cursor.execute(sql)
                execution_time = time.time() - start_time
                total_time += execution_time
                self.results_text.append(f"✅ {name} completed in {execution_time:.3f} seconds")

            self.results_text.append(f"🎉 Optimization completed in {total_time:.3f} seconds total")
            self.manager.status_message.setText("Database optimized successfully")

        except Exception as e:
            self.results_text.append(f"❌ Optimization failed: {str(e)}")
            QMessageBox.critical(self.manager.parent, "Optimization Error", f"Failed to optimize database:\n{str(e)}")


# Export the classes
__all__ = ['DataBrowserTab', 'SQLEditorTab', 'SchemaTab', 'ToolsTab']
