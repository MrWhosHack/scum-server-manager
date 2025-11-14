import sqlite3

conn = sqlite3.connect('scum_manager.db')
cursor = conn.cursor()

# Check for player "test"
cursor.execute('SELECT steam_id, display_name, status FROM players WHERE display_name LIKE ?', ('%test%',))
test_players = cursor.fetchall()
print('Players with "test" in name:')
for row in test_players:
    print(f'  SteamID: {row[0]}, Name: {row[1]}, Status: {row[2]}')

# Check online count
cursor.execute('SELECT COUNT(*) FROM players WHERE status = "online"')
online_count = cursor.fetchone()[0]
print(f'Total online players: {online_count}')

# Check all players
cursor.execute('SELECT display_name, status FROM players ORDER BY last_seen DESC LIMIT 10')
all_players = cursor.fetchall()
print('Recent players:')
for row in all_players:
    print(f'  {row[0]} - {row[1]}')

conn.close()