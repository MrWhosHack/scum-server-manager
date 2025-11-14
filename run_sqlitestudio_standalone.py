"""
SQLiteStudio Professional - Standalone Launcher
Copyright (c) 2025 SCUM Server Manager Project
Licensed under the MIT License
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
from sqlitestudio_pro import SQLiteStudioPro

def main():
    """Launch SQLiteStudio Pro with file picker"""
    app = QApplication(sys.argv)
    app.setApplicationName("SQLiteStudio Professional")
    app.setOrganizationName("SCUM Server Manager")
    
    # Show file picker
    db_path, _ = QFileDialog.getOpenFileName(
        None,
        "🗄️ Select SQLite Database to Open",
        str(Path.home()),
        "SQLite Database (*.db *.sqlite *.sqlite3 *.db3);;All Files (*.*)"
    )
    
    if not db_path:
        # User cancelled
        return 0
    
    # Verify file exists
    if not Path(db_path).exists():
        QMessageBox.critical(
            None,
            "File Not Found",
            f"The selected database file does not exist:\n{db_path}"
        )
        return 1
    
    # Launch SQLiteStudio Pro
    try:
        window = SQLiteStudioPro(None, db_path)
        window.exec()
        return 0
    except Exception as e:
        QMessageBox.critical(
            None,
            "Error",
            f"Failed to open database:\n{str(e)}"
        )
        return 1

if __name__ == "__main__":
    sys.exit(main())
