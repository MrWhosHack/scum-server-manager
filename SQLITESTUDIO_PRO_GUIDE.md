# 🗄️ SQLiteStudio Professional - User Guide

## ✨ What's New - SUPER EASY EDITING!

This is the **complete rebuilt version** of the database manager, designed specifically to make editing **incredibly easy** for users. Based directly on SQLiteStudio's best features!

---

## 🎯 Key Features

### ✏️ **1. EASY ROW EDITING - The Game Changer!**

**No more struggling with inline editing!** Now when you want to edit data:

#### **Insert New Row** (➕)
1. Select a table from the dropdown
2. Click the **"➕ Insert Row"** button (green, can't miss it!)
3. A beautiful dialog pops up with:
   - **Smart input fields** for each column
   - **Type indicators** (shows INTEGER, TEXT, etc.)
   - **Primary key markers** (🔑)
   - **Required field markers** (*)
   - **Auto-generated IDs** (you don't touch them!)
   
4. Fill in the fields (easy as a web form!)
5. Click **"💾 Save"** - Done! ✅

**Input Types:**
- **Numbers**: Spinboxes with up/down arrows
- **Decimals**: Decimal spinboxes for precise values
- **Text**: Single-line text boxes
- **Long Text**: Multi-line text areas (perfect for notes, descriptions)
- **Dates**: Date picker with calendar popup
- **Times**: Time picker
- **BLOBs**: Read-only (binary data indicator)

#### **Edit Existing Row** (✏️)
1. **Double-click any row** in the table, OR
2. Select a row and click **"✏️ Edit Row"** button (blue)
3. Same beautiful dialog appears, pre-filled with current values
4. Change what you want
5. Click **"💾 Save"** - Updated! ✅

#### **Delete Rows** (🗑️)
1. Select one or more rows (Ctrl+Click for multiple)
2. Click **"🗑️ Delete"** button (red) or press **Delete** key
3. Confirm the deletion
4. Gone! ✅

#### **Duplicate Row** (📋)
1. Select a row
2. Go to **Edit menu** → **Duplicate Row** (or Ctrl+D)
3. Creates a copy with new ID automatically
4. Duplicated! ✅

---

### 📊 **2. DATA BROWSER**

The main workspace for viewing and managing your data:

**Features:**
- **Table selector** dropdown - switch between tables instantly
- **Filter box** (🔍) - type to search across all columns
- **Sortable columns** - click headers to sort (up/down arrows appear)
- **Row selection** - single or multiple (Ctrl/Shift+Click)
- **Alternating row colors** - easier to read
- **Context menu** - right-click for quick actions

**Controls:**
- 🔄 **Refresh** - reload current table data
- ➕ **Insert Row** - open insert dialog (GREEN button)
- ✏️ **Edit Row** - open edit dialog (BLUE button)
- 🗑️ **Delete** - remove selected rows (RED button)
- 🔍 **Filter** - search/filter data in real-time

**Keyboard Shortcuts:**
- `Ctrl+N` - Insert new row
- `Ctrl+E` - Edit selected row
- `Ctrl+D` - Duplicate row
- `Delete` - Delete selected rows
- `Ctrl+F` - Focus filter box
- `F5` - Refresh table

---

### 💻 **3. SQL EDITOR**

Professional SQL query editor for power users:

**Features:**
- **Multi-line editor** with monospace font (Consolas)
- **Query history** - dropdown of previous queries
- **Execution results** - displayed in grid below
- **Row count indicator** - shows number of results
- **Auto-commit** - changes are saved automatically

**Controls:**
- ▶️ **Execute (F5)** - run the SQL query
- 🧹 **Clear** - clear editor
- 📝 **Format** - auto-format SQL keywords
- 📚 **History** - load previous queries

**Example Queries:**
```sql
-- SELECT data
SELECT * FROM players WHERE score > 1000 LIMIT 100;

-- INSERT new row
INSERT INTO players (name, email, score) VALUES ('John Doe', 'john@example.com', 500);

-- UPDATE existing data
UPDATE players SET score = score + 100 WHERE id = 5;

-- DELETE rows
DELETE FROM players WHERE is_active = 0;

-- JOIN tables
SELECT p.name, SUM(g.points_earned) as total_points
FROM players p
JOIN game_sessions g ON p.id = g.player_id
GROUP BY p.name
ORDER BY total_points DESC;
```

---

### 🏗️ **4. DATABASE STRUCTURE**

Visual schema viewer showing your entire database structure:

**Displays:**
- **Tables** (📊) - all user tables
  - **Columns** (📄) - with types and constraints
  - **Primary Keys** (🔑) - marked clearly
- **Views** (👁️) - virtual tables
- **Indexes** (🔍) - performance indexes

**Features:**
- **Full DDL** - complete CREATE TABLE statements
- **Export schema** - save as .sql file
- **Filter navigator** - search for specific objects
- **Expand/collapse** - organize your view

---

### 🧹 **5. DATABASE TOOLS**

Professional maintenance and utility tools:

#### **Database Menu**
- 📂 **Open Database** - switch to different .db file
- 🔄 **Refresh** (F5) - reload all data
- 📤 **Export Database** - full database export
- 📥 **Import CSV** - import data from CSV
- 🚪 **Close** (Ctrl+W) - close manager

#### **Table Menu**
- 🆕 **Create Table** - design new tables
- ✏️ **Alter Table** - modify table structure
- 🗑️ **Drop Table** - delete table
- 📤 **Export Table** - export to CSV
- 📥 **Import to Table** - import CSV data

#### **Edit Menu**
- ➕ **Insert Row** (Ctrl+N)
- ✏️ **Edit Row** (Ctrl+E)
- 📋 **Duplicate Row** (Ctrl+D)
- 🗑️ **Delete Row(s)** (Delete)
- 🔍 **Find** (Ctrl+F)

#### **Tools Menu**
- 🧹 **VACUUM** - reclaim unused space, defragment
- 🔄 **REINDEX** - rebuild indexes for better performance
- 📊 **ANALYZE** - update query planner statistics
- ✅ **Integrity Check** - verify database health
- 💾 **Backup Database** - create backup copy

---

## 🎨 **6. PROFESSIONAL INTERFACE**

Based on SQLiteStudio's design principles:

**Visual Design:**
- **Dark theme** - VS Code inspired, easy on eyes
- **Color coding**:
  - 🟢 Green buttons = Create/Insert
  - 🔵 Blue buttons = Edit/Modify
  - 🔴 Red buttons = Delete/Remove
  - ⚪ Gray buttons = Neutral actions
- **Icons everywhere** - visual indicators for all actions
- **Tooltips** - hover for help
- **Status bar** - connection status, database info

**Layout:**
- **Left panel**: Database navigator
- **Right panel**: Main workspace (tabs)
- **Tabs**: Data Browser, SQL Editor, Structure
- **Resizable splitters** - customize your workspace
- **Maximizable** - use full screen if needed

---

## 🚀 **Quick Start Guide**

### **First Time Use**

1. **Open Database**
   - From SCUM Server Manager: Click "Database" button
   - Select your .db file (e.g., `test_editing.db`)
   - Manager opens automatically

2. **Browse Data**
   - Select a table from dropdown
   - Data loads in the grid
   - Use filter to search
   - Click headers to sort

3. **Add New Data**
   - Click green **"➕ Insert Row"** button
   - Dialog opens with easy form
   - Fill in fields (skip auto-IDs!)
   - Click **"💾 Save"**
   - New row appears instantly!

4. **Edit Data**
   - **Double-click any row**
   - Same dialog opens with current values
   - Change what you need
   - Click **"💾 Save"**
   - Changes appear instantly!

5. **Delete Data**
   - Select row(s)
   - Click red **"🗑️ Delete"** button
   - Confirm deletion
   - Rows removed instantly!

---

## 💡 **Pro Tips**

### **Editing Tips**
1. **Auto-increment IDs**: Don't touch them! They're set automatically.
2. **Required fields**: Look for the `*` marker - these must be filled.
3. **Type validation**: The input fields match the column type - no more type errors!
4. **NULL values**: Leave fields empty if you want NULL (for nullable columns).
5. **Text areas**: For TEXT columns, you get a multi-line editor - perfect for long content.

### **Navigation Tips**
1. **Double-click tables** in navigator to load them
2. **Use F5** to refresh everything
3. **Ctrl+F** to jump to filter
4. **Tab key** works in dialogs to move between fields
5. **Enter** in filter applies it instantly

### **Performance Tips**
1. **Use filters** when working with large tables
2. **Run ANALYZE** after bulk changes
3. **VACUUM** to reclaim space
4. **Regular backups** before major changes
5. **Check integrity** if you suspect issues

### **Data Safety**
1. **Always backup** before bulk deletions
2. **Test queries** in SQL Editor first
3. **Use transactions** for multiple changes
4. **Check foreign keys** before deleting parent rows
5. **Export before ALTER TABLE** operations

---

## 📋 **Common Tasks**

### **Add a Customer Record**
1. Select `customers` table
2. Click **"➕ Insert Row"**
3. Fill in:
   - Name: John Smith
   - Email: john@example.com
   - Phone: 555-1234
4. Click **"💾 Save"**
5. Done! ✅

### **Update a Score**
1. Find player in `players` table
2. **Double-click the row**
3. Change `score` field to new value
4. Click **"💾 Save"**
5. Updated! ✅

### **Delete Old Records**
1. Either:
   - **Option A**: Use filter to find old records, select all, delete
   - **Option B**: Use SQL Editor:
     ```sql
     DELETE FROM old_table WHERE date < '2023-01-01';
     ```
2. Confirm
3. Deleted! ✅

### **Export Data to Excel**
1. Select table
2. **Table** menu → **Export Table**
3. Save as `.csv`
4. Open CSV in Excel
5. Done! ✅

### **Find Specific Data**
1. Type in filter box: "john"
2. All rows with "john" anywhere show up
3. Click column header to sort results
4. Found! ✅

---

## ⌨️ **Complete Keyboard Shortcuts**

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | Insert new row |
| `Ctrl+E` | Edit selected row |
| `Ctrl+D` | Duplicate row |
| `Delete` | Delete selected rows |
| `Ctrl+F` | Find/Filter |
| `F5` | Refresh / Execute SQL |
| `Ctrl+W` | Close window |
| `Ctrl+O` | Open database |
| `Ctrl+S` | Save query (SQL Editor) |

---

## ❓ **FAQ**

**Q: Why can't I edit the ID field?**
A: It's an auto-increment primary key. The database sets it automatically!

**Q: How do I insert NULL?**
A: Leave the field empty for nullable columns.

**Q: Can I edit multiple rows at once?**
A: Use SQL Editor for bulk updates:
```sql
UPDATE table SET column = value WHERE condition;
```

**Q: How do I see all my changes?**
A: Click **🔄 Refresh** or press **F5**.

**Q: Can I undo a delete?**
A: No! Always backup first. Use **Tools** → **Backup Database**.

**Q: How do I search multiple columns?**
A: Type in the filter box - it searches ALL columns!

**Q: What if my database is corrupted?**
A: Use **Tools** → **Integrity Check** to diagnose.

---

## 🆚 **vs SQLiteStudio Comparison**

| Feature | SQLiteStudio Pro | Original SQLiteStudio |
|---------|------------------|----------------------|
| Easy editing dialogs | ✅ YES - Beautiful! | ❌ Inline only |
| Smart input fields | ✅ Type-specific | ❌ Generic |
| Built-in | ✅ No install needed | ❌ Separate download |
| Dark theme | ✅ Professional | ⚠️ Limited |
| Integration | ✅ Direct in app | ❌ External |
| Auto-save | ✅ Instant | ⚠️ Manual |
| Modern UI | ✅ 2024 design | ⚠️ Older |

---

## 🎉 **Summary**

**SQLiteStudio Professional** is a complete, professional-grade SQLite database manager built directly into your application. The new **easy editing dialogs** make data management simple and intuitive for everyone!

**Key Advantages:**
1. ✅ **Easy editing** - Beautiful dialogs, not clunky inline editing
2. ✅ **Type-smart** - Right input for each column type
3. ✅ **Visual indicators** - See what's required, what's a key
4. ✅ **No installation** - Built right in
5. ✅ **Professional** - All the features you expect
6. ✅ **Modern** - 2024 interface design

**Get Started:**
Just click the **Database** button in your SCUM Server Manager and select a `.db` file!

---

*Built with ❤️ for easy database management*
