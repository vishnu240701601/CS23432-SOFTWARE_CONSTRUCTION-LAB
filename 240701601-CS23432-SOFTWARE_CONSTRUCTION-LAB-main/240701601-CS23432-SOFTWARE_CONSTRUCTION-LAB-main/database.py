import sqlite3

conn = sqlite3.connect("courier.db")
cursor = conn.cursor()

# USERS TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    email TEXT UNIQUE,
    address TEXT,
    pincode TEXT,
    password TEXT
)
""")

# STAFF TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    phone TEXT,
    email TEXT UNIQUE,
    password TEXT
)
""")

# COURIER TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS courier (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tracking_id TEXT UNIQUE,
    sender_name TEXT,
    receiver_name TEXT,
    receiver_phone TEXT,
    receiver_email TEXT,
    source TEXT,
    destination TEXT,
    assigned_staff INTEGER,
    status TEXT,
    expected_date TEXT
)
""")

# LOCATION LOGS TABLE (LIVE TRACKING)
cursor.execute("""
CREATE TABLE IF NOT EXISTS location_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tracking_id TEXT,
    latitude REAL,
    longitude REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS hub_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tracking_id TEXT,
    hub_name TEXT,
    entry_time DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")


conn.commit()
conn.close()

print("✅ Database and tables created successfully")
