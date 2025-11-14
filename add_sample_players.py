import sqlite3
import os
from datetime import datetime, timedelta
import random

# Path to the database
db_path = r"c:\Users\micha\Desktop\SCUM\scum_manager.db"

# Sample player data
sample_players = [
    {
        'steam_id': '76561198000000001',
        'display_name': 'TestPlayer1',
        'char_name': 'Survivor_001',
        'ip_address': '192.168.1.100',
        'first_seen': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S'),
        'last_seen': (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S'),
        'total_playtime': 14400,  # 4 hours in seconds
        'is_admin': 0,
        'is_banned': 0,
        'ban_reason': None
    },
    {
        'steam_id': '76561198000000002',
        'display_name': 'TestPlayer2',
        'char_name': 'Explorer_002',
        'ip_address': '192.168.1.101',
        'first_seen': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d %H:%M:%S'),
        'last_seen': (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
        'total_playtime': 7200,   # 2 hours in seconds
        'is_admin': 0,
        'is_banned': 0,
        'ban_reason': None
    },
    {
        'steam_id': '76561198000000003',
        'display_name': 'AdminPlayer',
        'char_name': 'Admin_003',
        'ip_address': '192.168.1.102',
        'first_seen': (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d %H:%M:%S'),
        'last_seen': (datetime.now() - timedelta(minutes=30)).strftime('%Y-%m-%d %H:%M:%S'),
        'total_playtime': 28800,  # 8 hours in seconds
        'is_admin': 1,
        'is_banned': 0,
        'ban_reason': None
    },
    {
        'steam_id': '76561198000000004',
        'display_name': 'BannedPlayer',
        'char_name': 'Trouble_004',
        'ip_address': '192.168.1.103',
        'first_seen': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d %H:%M:%S'),
        'last_seen': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
        'total_playtime': 3600,   # 1 hour in seconds
        'is_admin': 0,
        'is_banned': 1,
        'ban_reason': 'Griefing'
    },
    {
        'steam_id': '76561198000000005',
        'display_name': 'RegularPlayer',
        'char_name': 'Citizen_005',
        'ip_address': '192.168.1.104',
        'first_seen': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
        'last_seen': (datetime.now() - timedelta(hours=6)).strftime('%Y-%m-%d %H:%M:%S'),
        'total_playtime': 10800,  # 3 hours in seconds
        'is_admin': 0,
        'is_banned': 0,
        'ban_reason': None
    }
]

def add_sample_players():
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check current player count
        cursor.execute("SELECT COUNT(*) FROM players")
        current_count = cursor.fetchone()[0]
        print(f"Current players in database: {current_count}")

        # Add sample players
        for player in sample_players:
            # Check if player already exists
            cursor.execute("SELECT steam_id FROM players WHERE steam_id = ?", (player['steam_id'],))
            if cursor.fetchone():
                print(f"Player {player['display_name']} already exists, skipping...")
                continue

            # Insert player
            cursor.execute('''
                INSERT INTO players
                (steam_id, display_name, char_name, ip_address, first_seen, last_seen,
                 total_playtime, is_admin, is_banned, ban_reason, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'offline')
            ''', (
                player['steam_id'], player['display_name'], player['char_name'],
                player['ip_address'], player['first_seen'], player['last_seen'],
                player['total_playtime'], player['is_admin'], player['is_banned'],
                player['ban_reason']
            ))

            # Add a sample session for each player
            cursor.execute('''
                INSERT INTO player_sessions
                (steam_id, session_start, session_end, ip_address, duration)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                player['steam_id'],
                player['first_seen'],
                player['last_seen'],
                player['ip_address'],
                player['total_playtime']
            ))

            print(f"Added player: {player['display_name']} (SteamID: {player['steam_id']})")

        conn.commit()
        conn.close()

        # Verify the additions
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM players")
        new_count = cursor.fetchone()[0]
        print(f"Players in database after addition: {new_count}")
        conn.close()

        print("✅ Sample players added successfully!")
        print("Now run the SCUM application and check the Players tab - you should see the sample players when the server is offline.")

    except Exception as e:
        print(f"❌ Error adding sample players: {e}")

if __name__ == "__main__":
    add_sample_players()