# 📦 SQLiteStudio Pro - Distribution Guide

## Copyright & License

**SQLiteStudio Professional**  
Copyright (c) 2025 SCUM Server Manager Project  
Licensed under the MIT License

This means:
✅ **Free to use** commercially and personally  
✅ **Free to modify** and customize  
✅ **Free to distribute** with attribution  
✅ **No warranty** - use at your own risk  

---

## 📤 How to Share with Users

### Option 1: Share Source Code (Recommended for Developers)

1. **Share these files:**
   - `sqlitestudio_pro.py` - Main application
   - `LICENSE` - MIT License file
   - `README.md` - Documentation
   - `requirements.txt` - Dependencies

2. **Users need to install:**
   ```bash
   pip install PySide6
   ```

3. **Users can run:**
   ```python
   from sqlitestudio_pro import SQLiteStudioPro
   
   dialog = SQLiteStudioPro(None, "path/to/database.db")
   dialog.exec()
   ```

---

### Option 2: Create Standalone Executable (For End Users)

#### Using PyInstaller:

1. **Install PyInstaller:**
   ```bash
   pip install pyinstaller
   ```

2. **Create a launcher script** (`run_sqlitestudio.py`):
   ```python
   import sys
   from PySide6.QtWidgets import QApplication, QFileDialog
   from sqlitestudio_pro import SQLiteStudioPro
   
   if __name__ == "__main__":
       app = QApplication(sys.argv)
       
       # Ask user to select database
       db_path, _ = QFileDialog.getOpenFileName(
           None,
           "Select SQLite Database",
           "",
           "SQLite Database (*.db *.sqlite *.sqlite3);;All Files (*.*)"
       )
       
       if db_path:
           window = SQLiteStudioPro(None, db_path)
           window.exec()
       
       sys.exit(0)
   ```

3. **Build executable:**
   ```bash
   pyinstaller --onefile --windowed --name "SQLiteStudio-Pro" --icon=icon.ico run_sqlitestudio.py
   ```

4. **Distribute:**
   - Find `SQLiteStudio-Pro.exe` in `dist/` folder
   - Share the `.exe` file with users
   - No Python installation needed!

---

### Option 3: Create Installer Package

#### Using Inno Setup (Windows):

1. **Download Inno Setup:** https://jrsoftware.org/isinfo.php

2. **Create installer script** (`setup.iss`):
   ```iss
   [Setup]
   AppName=SQLiteStudio Professional
   AppVersion=1.0
   DefaultDirName={pf}\SQLiteStudio Pro
   DefaultGroupName=SQLiteStudio Pro
   OutputDir=installer
   OutputBaseFilename=SQLiteStudio-Pro-Setup
   Compression=lzma2
   SolidCompression=yes
   
   [Files]
   Source: "dist\SQLiteStudio-Pro.exe"; DestDir: "{app}"
   Source: "LICENSE"; DestDir: "{app}"
   Source: "README.md"; DestDir: "{app}"
   
   [Icons]
   Name: "{group}\SQLiteStudio Pro"; Filename: "{app}\SQLiteStudio-Pro.exe"
   Name: "{commondesktop}\SQLiteStudio Pro"; Filename: "{app}\SQLiteStudio-Pro.exe"
   
   [Run]
   Filename: "{app}\SQLiteStudio-Pro.exe"; Description: "Launch SQLiteStudio Pro"; Flags: postinstall nowait skipifsilent
   ```

3. **Build installer:**
   - Open setup.iss in Inno Setup
   - Click "Compile"
   - Share `SQLiteStudio-Pro-Setup.exe`

---

## 📋 Requirements for Users

### If sharing source code:
- Python 3.8 or higher
- PySide6 (`pip install PySide6`)

### If sharing executable:
- **Nothing!** Executable is standalone
- Works on Windows 10/11

---

## 🎨 Branding Your Distribution

### Add Your Logo:
Replace the header in `sqlitestudio_pro.py`:
```python
title = QLabel(f"🗄️ YOUR COMPANY NAME - Database Manager")
```

### Custom Icon:
Use your own `.ico` file when building:
```bash
pyinstaller --icon=your_logo.ico ...
```

### About Dialog:
Modify `_show_about()` method to include your info.

---

## 📄 Include Copyright Notice

Always include this notice when distributing:

```
SQLiteStudio Professional
Copyright (c) 2025 SCUM Server Manager Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## 🚀 Quick Start for Users

### Windows Users:
1. Download `SQLiteStudio-Pro-Setup.exe`
2. Run installer
3. Launch from Start Menu or Desktop icon
4. Select your SQLite database file
5. Start managing your data!

### Developers:
1. `pip install PySide6`
2. Import: `from sqlitestudio_pro import SQLiteStudioPro`
3. Use: `SQLiteStudioPro(parent, db_path).exec()`

---

## 💡 Tips for Distribution

✅ **Include README.md** - Help users understand features  
✅ **Include LICENSE** - Legal protection  
✅ **Test on clean system** - Ensure executable works  
✅ **Create screenshots** - Show off the beautiful UI  
✅ **Provide sample database** - Let users try it out  
✅ **Version your releases** - Use semantic versioning  
✅ **Create release notes** - Document what's new  

---

## 📞 Support

For issues and feature requests:
- GitHub Issues (if you create a repo)
- Email support
- Documentation site

---

## 🎉 Ready to Share!

Your SQLiteStudio Pro is now ready to distribute to users worldwide!

**Remember:** Always include the MIT License and copyright notice.

**Have fun sharing your amazing database manager!** 🚀
