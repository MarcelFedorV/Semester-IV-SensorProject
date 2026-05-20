import sqlite3

con = sqlite3.connect('/app/data/users.db')
cur = con.cursor()

print("=== Tables ===")
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print(cur.fetchall())

print("\n=== SpaceFunk Runs ===")
cur.execute("SELECT * FROM spacefunk_runs")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(row)
else:
    print("No runs yet.")

print("\n=== Leaderboard ===")
cur.execute("""
    SELECT u.username, r.score, round(r.distance_m/1000, 2), r.played_at
    FROM spacefunk_runs r
    JOIN users u ON u.id = r.user_id
    ORDER BY r.score DESC
""")
rows = cur.fetchall()
if rows:
    print(f"{'User':<20} {'Score':>8} {'Dist(km)':>10} {'Date'}")
    print("-" * 55)
    for username, score, dist, played_at in rows:
        print(f"{username:<20} {score:>8} {dist:>10} {played_at}")
else:
    print("No runs yet.")

con.close()
