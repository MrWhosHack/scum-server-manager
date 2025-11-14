# 🗄️ Professional Database Manager - Complete Guide

## Overview

Your SCUM Server Manager now includes a **complete, professional-grade SQLite database management system** that rivals and exceeds SQLiteStudio - all built-in with zero external dependencies!

## 🚀 Features

### ✅ Better than SQLiteStudio

Our database manager includes ALL SQLiteStudio features plus enhancements:

#### 📊 **Data Browser**
- View all tables in an intuitive grid interface
- **Inline editing** - Double-click any cell to edit
- **Real-time filtering** - Search across all columns
- **Add/Delete rows** with one click
- **Export to CSV** with full data preservation
- **Copy to clipboard** for easy data sharing
- **Sorting** by any column
- **Pagination** for large datasets
- Shows row counts and statistics

#### 💻 **SQL Editor**
- Professional code editor for SQL queries
- **Multi-query execution** - Run multiple queries at once
- **Query history** - Access previous queries instantly
- **Syntax formatting** - Auto-format SQL code
- **Save queries** to files for reuse
- **Export results** to CSV
- **Copy results** to clipboard
- **Tabbed results** - Multiple result sets side-by-side
- **Execution timing** - See how fast your queries run
- Handles SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, etc.

#### 📋 **Schema Designer**
- Visual display of complete database schema
- View CREATE TABLE statements
- See all indexes, views, and triggers
- **Export schema** to SQL file
- Timestamp tracking
- Easy modification suggestions

#### 🛠️ **Database Tools**
- **VACUUM** - Reclaim unused space, optimize file size
- **REINDEX** - Rebuild all indexes for better performance
- **ANALYZE** - Update query optimizer statistics
- **Integrity Check** - Verify database health
- **Full Optimize** - Run all optimizations at once
- **Backup/Restore** - Safe database backups
- **Clone Database** - Create exact copies
- **Detailed Statistics** - File size, record counts, object counts

### 🎨 **Professional UI**
- **VS Code Dark Theme** - Beautiful, modern interface
- **Smooth animations** - Polished user experience
- **Tabbed interface** - Work on multiple tasks simultaneously
- **Resizable panels** - Customize your workspace
- **Context menus** - Right-click for quick actions
- **Keyboard shortcuts** - F5 to execute queries
- **Status feedback** - Always know what's happening

## 📖 How to Use

### Opening the Database Manager

1. Launch SCUM Server Manager
2. Click **"🗄️ Open SQLite Studio"** button (or menu item)
3. The professional database manager opens instantly!

### Working with Data

#### Browse Tables
1. Go to **"📊 Data Browser"** tab
2. Select a table from the dropdown
3. View all data in the grid
4. Double-click any cell to edit
5. Click **"➕ Add Row"** to insert new records
6. Click **"🗑️ Delete Row"** to remove selected records
7. Use the search box to filter data instantly

**Pro Tips:**
- Click column headers to sort
- Use Ctrl+C to copy selected cells
- Export button saves entire table to CSV

#### Execute SQL Queries
1. Go to **"💻 SQL Editor"** tab
2. Type your SQL query
3. Press **F5** or click **"▶️ Execute"**
4. Results appear in a new tab below
5. Multiple queries? Separate with semicolons!

**Example Queries:**
```sql
-- Find all online players
SELECT * FROM players WHERE status = 'online';

-- Update server settings
UPDATE config SET value = '128' WHERE setting = 'max_players';

-- Get player statistics
SELECT 
    player_name,
    COUNT(*) as kills,
    MAX(score) as high_score
FROM player_stats
GROUP BY player_name
ORDER BY kills DESC
LIMIT 10;
```

**Pro Tips:**
- Use query history dropdown to rerun previous queries
- Save frequently used queries with **"💾 Save Query"**
- Export results to CSV for analysis in Excel
- Format SQL button cleans up your code

#### View Schema
1. Go to **"📋 Schema Designer"** tab
2. See all CREATE statements
3. Copy schema for documentation
4. Use as reference for queries

#### Maintain Database
1. Go to **"🛠️ Database Tools"** tab
2. Click **"⚡ Full Optimize"** for complete maintenance
3. Or run individual operations:
   - **VACUUM** after deleting lots of data
   - **REINDEX** if queries feel slow
   - **ANALYZE** before complex queries
   - **Integrity Check** if you suspect corruption

**Recommended Schedule:**
- Run **Full Optimize** weekly
- Run **Integrity Check** monthly
- Create **Backups** before major changes

### Sidebar Navigation

The left sidebar shows your complete database structure:

- 📋 **Tables** - All database tables
  - Right-click for options: Browse, Schema, Export, Drop
  - Double-click to open in Data Browser
  - See column names and types
  
- 📇 **Indexes** - Performance indexes
  
- 👁️ **Views** - Saved query views

- ⚡ **Triggers** - Automatic actions

## 🎯 Common Tasks

### Task: Export Player Data
1. Open Data Browser
2. Select "players" table
3. Click **"📤 Export"**
4. Choose CSV format
5. Save file
6. Open in Excel/Google Sheets!

### Task: Find Specific Records
1. Open Data Browser
2. Select table
3. Type search term in filter box
4. Results filter instantly!

### Task: Optimize Database After Updates
1. Open Database Tools
2. Click **"⚡ Full Optimize"**
3. Wait for success message
4. Done! Database is faster and smaller.

### Task: Backup Before Major Changes
1. Open Database Tools
2. Click **"💾 Create Backup"**
3. Choose location and filename
4. Backup created!
5. Make your changes safely

### Task: Check Database Health
1. Open Database Tools
2. Click **"✅ Integrity Check"**
3. See if database is healthy
4. Fix any issues if needed

## 🔥 Advanced Features

### Multi-Query Execution
Execute multiple queries in one go:
```sql
DELETE FROM temp_logs WHERE date < '2024-01-01';
VACUUM;
ANALYZE;
SELECT COUNT(*) FROM logs;
```

All four queries execute in sequence!

### Query Results Management
- Each query creates a new result tab
- Keep multiple results open simultaneously
- Close tabs you don't need (X button)
- Export any result set to CSV

### Real-Time Statistics
The header shows live stats:
- Number of tables
- Total records across all tables
- Database file size
- All updated automatically!

### Context Menu Power
Right-click on any table in the sidebar:
- **Browse Data** - Jump directly to data browser
- **Show Schema** - View CREATE TABLE statement
- **Export to CSV** - Quick export
- **Drop Table** - Delete table (careful!)

### Search and Filter
- Sidebar search: Find tables/views quickly
- Data browser filter: Search within table data
- Both search as you type!

## 🛡️ Safety Features

### Confirmations
- Deleting rows requires confirmation
- Dropping tables requires double confirmation
- No accidental data loss!

### Backups
- One-click backup creation
- Timestamped backup files
- Clone database for testing

### Integrity Checks
- PRAGMA integrity_check
- Verifies database health
- Catches corruption early

## 📊 Performance

### Optimization
- Built-in VACUUM reduces file size
- REINDEX rebuilds indexes for speed
- ANALYZE helps query optimizer
- Full Optimize does all three!

### Large Datasets
- Sorting and filtering are fast
- Pagination handles millions of rows
- Export streams data efficiently

## 🎨 Customization

### Window Layout
- Resize sidebar by dragging divider
- Resize editor/results by dragging splitter
- Arrange to your preference!

### Tab Management
- Close unused tabs
- Reorder tabs by dragging
- Open multiple data browsers

## 🆚 Comparison: Our Manager vs SQLiteStudio

| Feature | Our Manager | SQLiteStudio |
|---------|-------------|--------------|
| Installation | ✅ Built-in | ❌ Separate download |
| Launch Speed | ✅ Instant | ❌ Slow startup |
| Dark Theme | ✅ Professional | ⚠️ Basic |
| Data Editing | ✅ Inline | ✅ Yes |
| SQL Editor | ✅ Advanced | ✅ Yes |
| Multi-Query | ✅ Yes | ⚠️ Limited |
| Query History | ✅ Built-in | ✅ Yes |
| Export | ✅ CSV, JSON | ✅ Multiple formats |
| Schema View | ✅ Yes | ✅ Yes |
| Tools | ✅ Comprehensive | ✅ Yes |
| Integration | ✅ Perfect | ❌ External |
| Performance | ✅ Optimized | ⚠️ Heavy |
| Cost | ✅ Free | ✅ Free |

**Verdict: Our manager is better!** ✨

## 🐛 Troubleshooting

### Database Won't Open
- **Solution**: Check file permissions
- **Solution**: Ensure file isn't locked by another program
- **Solution**: Verify file isn't corrupted (try backup)

### Queries Are Slow
1. Run **ANALYZE** in Database Tools
2. Run **REINDEX** to rebuild indexes
3. Check query - add WHERE clauses
4. Consider adding indexes

### Can't Edit Data
- Some tables may be read-only
- Check table permissions
- Verify database isn't opened elsewhere

### Results Not Showing
- Ensure query is SELECT statement
- Check for syntax errors
- Look at status bar for error messages

## 💡 Pro Tips

1. **Use F5** to quickly execute queries
2. **Right-click tables** for quick access to common operations
3. **Export before major changes** - always have a backup!
4. **Run Full Optimize weekly** - keeps database healthy
5. **Use query history** - don't retype common queries
6. **Filter data** instead of scrolling - much faster!
7. **Watch the status bar** - it tells you what's happening
8. **Multiple result tabs** - compare query results side-by-side
9. **ANALYZE before complex queries** - makes them faster
10. **Integrity check monthly** - catch issues early!

## 🎓 Learning SQL

### Basic Queries
```sql
-- Select all data
SELECT * FROM table_name;

-- Select specific columns
SELECT column1, column2 FROM table_name;

-- Filter results
SELECT * FROM players WHERE level > 50;

-- Sort results
SELECT * FROM players ORDER BY score DESC;

-- Limit results
SELECT * FROM players LIMIT 10;
```

### Advanced Queries
```sql
-- Count records
SELECT COUNT(*) FROM players WHERE status = 'active';

-- Group by
SELECT faction, COUNT(*) as player_count 
FROM players 
GROUP BY faction;

-- Join tables
SELECT p.name, s.score 
FROM players p
JOIN scores s ON p.id = s.player_id;

-- Subqueries
SELECT * FROM players 
WHERE id IN (SELECT player_id FROM bans);
```

### Data Modification
```sql
-- Insert
INSERT INTO logs (message, timestamp) 
VALUES ('Server started', datetime('now'));

-- Update
UPDATE players 
SET status = 'inactive' 
WHERE last_seen < date('now', '-30 days');

-- Delete
DELETE FROM temp_data WHERE processed = 1;
```

## 📞 Support

Having issues? The database manager includes:
- Status messages for every operation
- Error dialogs with detailed information
- Execution timing for performance tracking
- Row counts for data operations

All feedback appears in the status bar at the bottom!

## 🎉 Conclusion

You now have a **complete, professional database management system** built directly into your SCUM Server Manager. No external tools needed, no downloads, no setup - just pure power at your fingertips!

**Enjoy your new SQLiteStudio replacement!** 🚀

---

*Professional Database Manager v2.0.0*  
*Part of SCUM Server Manager Pro*
