# 🗄️ SQLiteStudio Professional

**A Modern, Professional SQLite Database Manager**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/GUI-PySide6-green.svg)](https://pypi.org/project/PySide6/)

---

## ✨ Features

### 🎨 **Stunning Modern UI**
- Beautiful gradient-based dark theme
- Better design than SQLiteStudio.pl
- Smooth animations and transitions
- Professional VS Code-inspired styling
- 3D button effects with hover animations

### 📊 **Powerful Data Management**
- **Direct Cell Editing** - Click and type to edit instantly
- Visual confirmation with green flash on save
- Smart input widgets based on column types
- Primary key protection (read-only)
- Bulk row operations (insert, edit, delete, duplicate)

### 📝 **Professional SQL Editor**
- Syntax highlighting for SQL keywords
- Auto-completion for functions and keywords
- Query history tracking
- Multi-query execution
- SQL formatting tools

### 🔧 **Advanced Tools**
- Visual Query Builder (drag & drop)
- Test Data Generator
- Performance Monitor
- Foreign Key Visualizer
- Database Integrity Checker
- VACUUM, REINDEX, ANALYZE tools

### 💾 **Import/Export**
- CSV export/import
- JSON data export
- XML export support
- SQL schema export
- Backup database functionality

### ⚡ **User Experience**
- Keyboard shortcuts for all actions
- Context menus on right-click
- Advanced filtering and search
- Sortable columns
- Row counting and statistics

---

## 🚀 Quick Start

### For End Users:

1. **Download** `SQLiteStudio-Pro.exe` (Windows)
2. **Run** the executable
3. **Select** your SQLite database file
4. **Start** managing your data!

*No installation or Python required!*

---

### For Developers:

#### Installation:
```bash
pip install PySide6
```

#### Usage in Your Application:
```python
from sqlitestudio_pro import SQLiteStudioPro
from PySide6.QtWidgets import QApplication

app = QApplication([])
dialog = SQLiteStudioPro(None, "path/to/your/database.db")
dialog.exec()
```

#### Standalone Launch:
```bash
python run_sqlitestudio_standalone.py
```

---

## 📸 Screenshots

### Main Interface
- Beautiful gradient header with database name
- Modern data grid with instant cell editing
- Color-coded action buttons (Green, Blue, Red)

### SQL Editor
- Syntax highlighting in real-time
- Query history dropdown
- Professional code editor feel

### Row Editor Dialog
- Smart input widgets per data type
- Date/Time pickers
- Number spinners
- Multi-line text editors

---

## 🎯 How to Use

### Editing Data:
1. **Double-click** any cell to edit
2. **Type** your new value
3. **Press Enter** or click away
4. **See green flash** - your data is saved!

### Inserting Rows:
1. Click **➕ Insert Row** button
2. Fill in the form (auto-increment fields are disabled)
3. Click **💾 Save**
4. Row appears in table instantly!

### Deleting Rows:
1. **Select** one or more rows
2. Click **🗑️ Delete** button
3. **Confirm** deletion
4. Rows removed from database

### Running SQL:
1. Go to **📝 SQL Editor** tab
2. **Type** your SQL query
3. **Press F5** or click **▶️ Execute**
4. **View** results in table below

### Using Query Builder:
1. **Tools** menu → **🔧 Query Builder**
2. **Select** tables and columns visually
3. **Add** WHERE conditions with dropdowns
4. **Copy** generated SQL to editor

### Generating Test Data:
1. **Tools** menu → **🎲 Data Generator**
2. **Select** target table
3. **Configure** column generation rules
4. **Generate** rows with progress bar

---

## 🔑 Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Refresh | `F5` |
| Insert Row | `Ctrl+N` |
| Edit Row | `Ctrl+E` |
| Delete Rows | `Delete` |
| Duplicate Row | `Ctrl+D` |
| Find | `Ctrl+F` |
| Execute SQL | `F5` (in SQL Editor) |
| Close | `Ctrl+W` |
| Open Database | `Ctrl+O` |

---

## 📦 Distribution

### Build Standalone Executable:

```bash
# Run the build script
build_sqlitestudio_exe.bat

# Or manually:
pyinstaller --onefile --windowed --name "SQLiteStudio-Pro" run_sqlitestudio_standalone.py
```

**Output:** `dist\SQLiteStudio-Pro.exe`

### What to Include:
- ✅ `SQLiteStudio-Pro.exe` - Main executable
- ✅ `LICENSE` - MIT License file
- ✅ `README.md` - This documentation
- ✅ `DISTRIBUTION_GUIDE.md` - How to share

See [DISTRIBUTION_GUIDE.md](DISTRIBUTION_GUIDE.md) for detailed instructions.

---

## 📄 License & Copyright

**Copyright (c) 2025 SCUM Server Manager Project**

This software is licensed under the **MIT License**.

### What this means:
✅ **Free to use** commercially and personally  
✅ **Free to modify** and customize  
✅ **Free to distribute** with attribution  
✅ **No warranty** provided  

See [LICENSE](LICENSE) file for full terms.

---

## 🛠️ Technical Details

### Built With:
- **Python 3.8+** - Programming language
- **PySide6** - Qt6 GUI framework
- **SQLite3** - Database engine (built into Python)

### Architecture:
- Modern dialog-based application
- Event-driven GUI
- Direct database connection
- Transaction-safe operations
- Error handling and recovery

### File Structure:
```
sqlitestudio_pro.py          # Main application code
run_sqlitestudio_standalone.py  # Standalone launcher
build_sqlitestudio_exe.bat   # Build script
DISTRIBUTION_GUIDE.md        # Distribution instructions
LICENSE                      # MIT License
README.md                    # This file
```

---

## 🐛 Troubleshooting

### "Cannot edit cells"
- Make sure you're **double-clicking** the cell
- Primary key columns are **read-only** (blue background)
- Check that table has a primary key

### "Insert dialog error"
- Fixed in latest version
- Update to current release

### "Executable won't run"
- Requires **Windows 10/11**
- Rebuild if needed with `build_sqlitestudio_exe.bat`

### "Import error"
- Install PySide6: `pip install PySide6`
- Use Python 3.8 or higher

---

## 🎨 Customization

### Change Theme Colors:
Edit `_get_stylesheet()` method in `sqlitestudio_pro.py`

### Add Your Logo:
Modify header section in `_init_ui()` method

### Custom Features:
Extend the `SQLiteStudioPro` class with your own methods

---

## 🚀 Future Enhancements

Planned features:
- [ ] Multiple database tabs
- [ ] SQL syntax checking
- [ ] Visual ER diagrams
- [ ] Cloud database support
- [ ] Plugin system
- [ ] Custom themes
- [ ] Export to Excel
- [ ] Advanced filtering UI

---

## 💬 Support

For questions, issues, or feature requests:
- Open an issue on GitHub
- Check the documentation
- Review the source code comments

---

## 🙏 Acknowledgments

- Built with ❤️ for the database management community
- Inspired by SQLiteStudio.pl (but better!)
- Uses the excellent PySide6 framework
- MIT License for maximum freedom

---

## 📞 Contact

**SCUM Server Manager Project**  
Copyright © 2025  
Licensed under MIT License

---

**Made with 💙 for database enthusiasts worldwide!**

*Start managing your SQLite databases like a pro today!* 🚀
