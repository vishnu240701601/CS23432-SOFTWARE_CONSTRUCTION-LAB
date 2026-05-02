import sqlite3
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

conn = sqlite3.connect("courier.db")
cursor = conn.cursor()

cursor.execute("""
    SELECT latitude, longitude
    FROM location_logs
    WHERE tracking_id = '45E8AA34'
    ORDER BY timestamp
""")

points = cursor.fetchall()
conn.close()

total = 0.0
for i in range(len(points) - 1):
    lat1, lon1 = points[i]
    lat2, lon2 = points[i + 1]
    total += haversine(lat1, lon1, lat2, lon2)

print("Raw distance (km):", total)
print("Rounded (3 decimals):", round(total, 3))
