# 🗄️ Database Manager - Quick Reference

## 🚀 Launch
Click **"🗄️ Open SQLite Studio"** button in SCUM Server Manager

---

## 📊 DATA BROWSER TAB

### View Data
1. Select table from dropdown
2. Data loads automatically
3. Click column headers to sort

### Edit Data
- **Double-click cell** to edit
- **➕ Add Row** button creates new record
- **🗑️ Delete Row** removes selected record
- **🔄 Refresh** reloads table data

### Search
- Type in **Filter** box
- Searches across ALL columns
- Updates instantly as you type

### Export
- **📤 Export** saves to CSV
- **📋 Copy** puts data on clipboard

---

## 💻 SQL EDITOR TAB

### Execute Queries
1. Type SQL in editor area
2. Press **F5** or click **▶️ Execute**
3. Results appear in tabs below

### Multiple Queries
Separate queries with semicolons:
```sql
DELETE FROM old_data WHERE date < '2024-01-01';
VACUUM;
SELECT COUNT(*) FROM current_data;
```

### Query History
- Use **History** dropdown to rerun queries
- **💾 Save Query** exports to .sql file
- **📝 Format** cleans up SQL code

### Results
- Each query creates a new tab
- **📤 Export** results to CSV
- **📋 Copy** to clipboard
- **✖️ Close** tabs you don't need

---

## 📋 SCHEMA DESIGNER TAB

### View Schema
- See all CREATE TABLE statements
- Copy to clipboard (Ctrl+A, Ctrl+C)
- Use as reference for queries

### Refresh
Click **🔄 Refresh Schema** to reload

---

## 🛠️ DATABASE TOOLS TAB

### Quick Optimize
Click **⚡ Full Optimize** - runs all optimizations at once!

### Individual Tools
- **🧹 VACUUM** - Reclaim wasted space
- **🔄 REINDEX** - Rebuild indexes (fixes slow queries)
- **📊 ANALYZE** - Update query statistics
- **✅ Integrity Check** - Verify database health

### Backup
- **💾 Create Backup** - Save a copy
- **📋 Clone Database** - Duplicate entire database

### When to Use
- **After major changes**: Run Full Optimize
- **Before modifications**: Create Backup
- **Monthly**: Integrity Check
- **Queries slow?**: REINDEX

---

## 🎯 KEYBOARD SHORTCUTS

| Key | Action |
|-----|--------|
| **F5** | Execute SQL query |
| **Ctrl+C** | Copy selected data |
| **Double-Click** | Edit cell (Data Browser) |
| **Right-Click** | Context menu |

---

## 📍 SIDEBAR NAVIGATION

### Tree Structure
- **📋 Tables** - All database tables
  - Expand to see columns
  - Double-click to browse data
  - Right-click for menu
- **📇 Indexes** - Database indexes
- **👁️ Views** - Saved views
- **⚡ Triggers** - Automatic triggers

### Right-Click Menu
- **📊 Browse Data** - Open in Data Browser
- **📝 Show Schema** - View CREATE statement
- **📤 Export to CSV** - Quick export
- **🗑️ Drop Table** - Delete table (⚠️ careful!)

### Search
Type in search box to filter objects

---

## ⚡ COMMON TASKS

### Export Table to CSV
1. Sidebar → Right-click table → **Export to CSV**
2. Choose filename → Save
3. Done!

### Find Specific Records
1. Data Browser → Select table
2. Type search term in **Filter** box
3. Results appear instantly!

### Run Multiple Queries
1. SQL Editor → Type queries (separate with `;`)
2. Press **F5**
3. Each query shows results in separate tab

### Optimize Database
1. Database Tools tab
2. Click **⚡ Full Optimize**
3. Wait for success message
4. Done!

### Backup Database
1. Database Tools tab
2. Click **💾 Create Backup**
3. Choose location
4. Save!

---

## 💡 PRO TIPS

1. **F5 is your friend** - Fastest way to execute queries
2. **Use filters** - Don't scroll through thousands of rows
3. **Export before changes** - Always have a backup!
4. **Full Optimize weekly** - Keeps things fast
5. **Query history** - Reuse queries instead of retyping
6. **Right-click tables** - Quick access to everything
7. **Multiple result tabs** - Compare queries side-by-side
8. **Integrity check monthly** - Catch problems early
9. **ANALYZE before big queries** - Makes them faster
10. **Watch status bar** - Shows what's happening

---

## 🆘 QUICK FIXES

### Query Failed?
- Check SQL syntax
- Look at status bar for error
- Make sure table/column names are correct

### Data Not Showing?
- Click **🔄 Refresh**
- Check if table is empty
- Clear filter box

### Can't Edit?
- Make sure you double-clicked cell
- Some system tables are read-only
- Check database isn't locked

### Database Slow?
1. Tools tab → **🔄 REINDEX**
2. Then → **📊 ANALYZE**
3. Done!

---

## 📊 STATUS BAR (Bottom)

Shows real-time info:
- ⏱️ **Query execution time**
- 📊 **Row counts**
- ✅ **Success messages**
- ❌ **Error messages**

Always check the status bar for feedback!

---

## 🎨 INTERFACE

### Header (Top)
- Database file name
- Connection status
- Live statistics (tables, records, size)

### Sidebar (Left)
- Database object tree
- Search box
- Object statistics

### Main Area (Center)
- Tabbed interface
- Multiple tabs can be open
- Drag tabs to reorder
- Close tabs with ✖️

### Status Bar (Bottom)
- Operation feedback
- Execution timing
- Row counts

---

## 📈 RECOMMENDED SCHEDULE

| Frequency | Task |
|-----------|------|
| **Weekly** | Full Optimize |
| **Monthly** | Integrity Check |
| **Before Changes** | Create Backup |
| **After Major Updates** | VACUUM + REINDEX |
| **When Queries Slow** | ANALYZE |

---

## 🎓 EXAMPLE QUERIES

### Simple SELECT
```sql
SELECT * FROM players WHERE level > 50;
```

### Count Records
```sql
SELECT COUNT(*) FROM players WHERE status = 'active';
```

### Sort Results
```sql
SELECT name, score FROM players ORDER BY score DESC LIMIT 10;
```

### Update Data
```sql
UPDATE settings SET value = 'enabled' WHERE key = 'auto_restart';
```

### Insert Data
```sql
INSERT INTO logs (message, timestamp) 
VALUES ('Server started', datetime('now'));
```

---

## ✅ SAFETY FEATURES

- ❓ **Confirmations** - Dangerous operations ask first
- 💾 **Backups** - One-click database backups
- ✅ **Integrity checks** - Verify database health
- 🔄 **Transaction support** - Changes can be rolled back
- 📊 **Statistics** - See what you're working with

---

## 🎉 YOU'RE READY!

**This database manager gives you complete control over your SQLite databases with a professional interface and powerful tools.**

**Need more details?** See `DATABASE_MANAGER_GUIDE.md`

---

*Professional Database Manager v2.0.0*
