import sqlite3
try:
    conn = sqlite3.connect('scum_manager.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables = cursor.fetchall()
    print('Tables:', tables)

    if ('players',) in tables:
        cursor.execute('SELECT COUNT(*) FROM players')
        count = cursor.fetchone()[0]
        print('Player count:', count)

        if count > 0:
            cursor.execute('SELECT steam_id, display_name, char_name, status FROM players LIMIT 3')
            players = cursor.fetchall()
            print('Sample players:', players)
        else:
            print('No players in database')
    else:
        print('No players table found')

    conn.close()
except Exception as e:
    print('Error:', e)