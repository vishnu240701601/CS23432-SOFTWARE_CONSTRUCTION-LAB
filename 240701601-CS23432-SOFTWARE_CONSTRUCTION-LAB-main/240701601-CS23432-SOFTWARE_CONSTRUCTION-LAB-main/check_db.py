import sqlite3

conn = sqlite3.connect("courier.db")
cursor = conn.cursor()

print("LATEST LOCATION LOGS:\n")

cursor.execute("""
SELECT tracking_id, latitude, longitude, timestamp
FROM location_logs
ORDER BY timestamp DESC
LIMIT 10
""")

rows = cursor.fetchall()

for r in rows:
    print(r)

conn.close()
