from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secretkey"

import math
import qrcode
import os

from flask import jsonify


@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.get_json()
    tracking_id = data['tracking_id']
    latitude = data['latitude']
    longitude = data['longitude']
    log_hub_entry(tracking_id, latitude, longitude)

    conn = sqlite3.connect("courier.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO location_logs (tracking_id, latitude, longitude)
        VALUES (?,?,?)
    """, (tracking_id, latitude, longitude))
    conn.commit()
    conn.close()

    return jsonify({"status": "Location updated"})

HUBS = {
    "Chennai Hub": (13.0827, 80.2707),
    "Coimbatore Hub": (11.0168, 76.9558),
    "Madurai Hub": (9.9252, 78.1198),
    "Trichy Hub": (10.7905, 78.7047),
    "Salem Hub": (11.6643, 78.1460)
}
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * \
        math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calculate_total_distance(tracking_id):
    conn = sqlite3.connect("courier.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT latitude, longitude FROM location_logs
        WHERE tracking_id=?
        ORDER BY timestamp
    """, (tracking_id,))
    points = cursor.fetchall()
    conn.close()

    total = 0
    for i in range(len(points)-1):
        total += haversine(
            points[i][0], points[i][1],
            points[i+1][0], points[i+1][1]
        )
    return total

@app.route('/get_live_stats/<tracking_id>')
def get_live_stats(tracking_id):
    tracking_id = tracking_id.upper()

    # latest location
    conn = sqlite3.connect("courier.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT latitude, longitude
        FROM location_logs
        WHERE tracking_id=?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (tracking_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return jsonify({
            "total_distance": 0,
            "nearest_hub": "N/A",
            "hub_distance": 0
        })

    lat, lon = row

    total_distance = calculate_total_distance(tracking_id)
    nearest, hub_distance = nearest_hub(lat, lon)

    conn.close()

    return jsonify({
        "total_distance": round(total_distance, 3),
        "nearest_hub": nearest,
        "hub_distance": hub_distance
    })



def nearest_hub(lat, lon):
    nearest = None
    min_dist = float('inf')

    for hub, coords in HUBS.items():
        dist = haversine(lat, lon, coords[0], coords[1])
        if dist < min_dist:
            min_dist = dist
            nearest = hub

    return nearest, round(min_dist, 2)


@app.route('/staff_update', methods=['GET', 'POST'])
def staff_update():
    return render_template('staff_update.html')


@app.route('/get_latest_location/<tracking_id>')
def get_latest_location(tracking_id):
    tracking_id = tracking_id.upper()
    conn = sqlite3.connect("courier.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT latitude, longitude
        FROM location_logs
        WHERE tracking_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (tracking_id,))

    row = cursor.fetchone()
    conn.close()

    if row and row[0] is not None and row[1] is not None:
        return jsonify({"lat": row[0], "lon": row[1]})
    else:
        return jsonify({"lat": 0, "lon": 0})

@app.route('/get_live_metrics/<tracking_id>')
def get_live_metrics(tracking_id):
    tracking_id = tracking_id.upper()

    conn = sqlite3.connect("courier.db")
    cursor = conn.cursor()

    # latest location
    cursor.execute("""
        SELECT latitude, longitude
        FROM location_logs
        WHERE tracking_id=?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (tracking_id,))
    loc = cursor.fetchone()

    if not loc:
        conn.close()
        return jsonify({
            "total_distance": 0,
            "nearest_hub": "N/A",
            "hub_distance": 0
        })

    lat, lon = loc

    # calculations
    total_distance = calculate_total_distance(tracking_id)
    hub, hub_distance = nearest_hub(lat, lon)

    conn.close()

    return jsonify({
        "total_distance": total_distance,
        "nearest_hub": hub,
        "hub_distance": hub_distance
    })



@app.route('/auto_location_update', methods=['POST'])
def auto_location_update():
    data = request.get_json()\

    tracking_id = data['tracking_id'].upper()
    lat = float(data['latitude'])
    lon = float(data['longitude'])
    print("AUTO GPS DATA RECEIVED:", tracking_id, lat, lon)
    conn = sqlite3.connect(
        "courier.db",
        timeout=10,           # ⬅ IMPORTANT
        check_same_thread=False
    )
    cursor = conn.cursor()

    # Save history
    cursor.execute("""
        INSERT INTO location_logs (tracking_id, latitude, longitude, timestamp)
        VALUES (?, ?, ?, datetime('now'))
    """, (tracking_id, lat, lon))

    # Update current location (same as manual update)
    cursor.execute("""
        UPDATE courier
        SET latitude = ?, longitude = ?
        WHERE tracking_id = ?
    """, (lat, lon, tracking_id))

    conn.commit()
    conn.close()
    log_hub_entry(tracking_id, lat, lon)
    return jsonify({"status": "ok"})




@app.route('/manual_update', methods=['POST'])
def manual_update():
    tracking_id = request.form['tracking_id']
    latitude = float(request.form['latitude'])
    longitude = float(request.form['longitude'])
    log_hub_entry(tracking_id, latitude, longitude)

    conn = sqlite3.connect("courier.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO location_logs (tracking_id, latitude, longitude)
        VALUES (?,?,?)
    """, (tracking_id, latitude, longitude))
    cursor.execute("""
        UPDATE courier
        SET latitude=?, longitude=?
        WHERE tracking_id=?
    """, (lat, lon, tracking_id))

    conn.commit()
    conn.close()

    return "Location updated successfully"


def get_delivery_history(tracking_id):
    conn = sqlite3.connect("courier.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT hub_name, entry_time FROM hub_entries
        WHERE tracking_id=?
        ORDER BY entry_time
    """, (tracking_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows



@app.route("/")
def home():
    return render_template("entry.html")

@app.route('/register', methods=['GET','POST'])
def user_register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        email = request.form['email']
        address = request.form['address']
        pincode = request.form['pincode']
        password = request.form['password']

        conn = sqlite3.connect("courier.db")
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (name, phone, email, address, pincode, password) VALUES (?,?,?,?,?,?)",
                           (name, phone, email, address, pincode, password))
            conn.commit()
            conn.close()
            return "✅ Registration successful. You can now login."
        except sqlite3.IntegrityError:
            return "❌ Email already registered."

    return render_template('user_register.html')

@app.route('/user_login', methods=['GET','POST'])
def user_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect("courier.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = user[0]   # store user id in session
            return redirect('/user_dashboard')
        else:
            return "❌ Invalid credentials"

    return render_template('user_login.html')

@app.route('/staff_login', methods=['GET','POST'])
def staff_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect("courier.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM staff WHERE email=? AND password=?", (email, password))
        staff = cursor.fetchone()
        conn.close()

        if staff:
            session['staff'] = staff[0]   # staff id
            return redirect('/staff_update')
        else:
            return "❌ Invalid staff credentials"

    return render_template('staff_login.html')

@app.route('/admin_login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Hardcoded credentials
        if username=="admin" and password=="admin123":
            session['admin'] = True
            return redirect('/admin_dashboard')
        else:
            return "❌ Invalid admin credentials"

    return render_template('admin_login.html')


@app.route('/staff_dashboard')
def staff_dashboard():
    if 'staff' not in session:
        return redirect('/staff_login')
    return render_template('staff_tracking.html')



@app.route('/admin_dashboard', methods=['GET','POST'])
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/admin_login')

    conn = sqlite3.connect("courier.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM staff")
    staff_list = cursor.fetchall()
    conn.close()

    if request.method == 'POST':
        sender_name = request.form['sender_name']
        receiver_name = request.form['receiver_name']
        receiver_phone = request.form['receiver_phone']
        receiver_email = request.form['receiver_email']
        source = request.form['source']
        destination = request.form['destination']
        assigned_staff = request.form['assigned_staff']
        expected_date = request.form['expected_date']
        status = "Booked"

        # Generate tracking ID
        tracking_id = os.urandom(4).hex()  # 8 character ID

        # Insert into database
        conn = sqlite3.connect("courier.db")
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO courier (tracking_id, sender_name, receiver_name, receiver_phone, receiver_email, source, destination, assigned_staff, status, expected_date)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (tracking_id, sender_name, receiver_name, receiver_phone, receiver_email, source, destination, assigned_staff, status, expected_date))
        conn.commit()
        conn.close()

        # Generate QR code
        qr_img = qrcode.make(tracking_id)
        qr_path = os.path.join("static/qr_codes", f"{tracking_id}.png")
        qr_img.save(qr_path)

        # For simulation: we just display email content
        email_message = f"""
        Dear {receiver_name},

        Your courier has been created.
        Tracking ID: {tracking_id}
        Sender: {sender_name}
        Source: {source}
        Destination: {destination}
        Assigned Staff ID: {assigned_staff}
        """

        return render_template("courier_created.html", tracking_id=tracking_id, qr_path=qr_path, email_message=email_message)

    return render_template("admin_dashboard.html", staff_list=staff_list)

@app.route('/user_dashboard')
def user_dashboard():
    if 'user' not in session:
        return redirect('/user_login')

    return render_template('user_dashboard.html')

@app.route('/track_courier', methods=['GET', 'POST'])
def track_courier():
    if 'user' not in session:
        return redirect('/user_login')

    if request.method == 'POST':
        tracking_id = request.form['tracking_id']

        conn = sqlite3.connect("courier.db")
        cursor = conn.cursor()

        #  Fetch courier basic details
        cursor.execute("""
            SELECT * FROM courier WHERE tracking_id=?
        """, (tracking_id,))
        courier = cursor.fetchone()

        if not courier:
            conn.close()
            return render_template(
                "tracking_result.html",
                courier=None
            )

        # 2️⃣ Fetch latest location
        cursor.execute("""
            SELECT latitude, longitude
            FROM location_logs
            WHERE tracking_id=?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (tracking_id,))
        location = cursor.fetchone()

        latitude = location[0] if location else 0
        longitude = location[1] if location else 0

        # 3️⃣ Calculate total distance travelled
        total_distance = calculate_total_distance(tracking_id)

        # 4️⃣ Find nearest hub
        if location:
            nearest, hub_distance = nearest_hub(latitude, longitude)
        else:
            nearest, hub_distance = "N/A", 0

        # 5️⃣ Fetch delivery / hub entry history
        cursor.execute("""
            SELECT hub_name, entry_time
            FROM hub_entries
            WHERE tracking_id=?
            ORDER BY entry_time
        """, (tracking_id,))
        history = cursor.fetchall()

        conn.close()

        # 6️⃣ Send everything to UI
        return render_template(
            "tracking_result.html",
            courier=courier,
            latitude=latitude,
            longitude=longitude,
            total_distance=total_distance,
            nearest_hub=nearest,
            hub_distance=hub_distance,
            history=history
        )

    return render_template("track_courier.html")



def log_hub_entry(tracking_id, lat, lon):
    hub, dist = nearest_hub(lat, lon)

    if dist <= 2:  # within 2 km
        conn = sqlite3.connect("courier.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO hub_entries (tracking_id, hub_name)
            VALUES (?,?)
        """, (tracking_id, hub))
        conn.commit()
        conn.close()

@app.route('/get_route_points/<tracking_id>')
def get_route_points(tracking_id):
    tracking_id = tracking_id.upper()

    conn = sqlite3.connect("courier.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT latitude, longitude
        FROM location_logs
        WHERE tracking_id = ?
        ORDER BY timestamp
    """, (tracking_id,))

    rows = cursor.fetchall()
    conn.close()

    return jsonify([
        {"lat": row[0], "lon": row[1]}
        for row in rows
        if row[0] and row[1]
    ])


@app.route('/analytics/<tracking_id>')
def analytics(tracking_id):
    conn = sqlite3.connect("courier.db")
    cursor = conn.cursor()

    # Total distance
    total_distance = calculate_total_distance(tracking_id)

    # Total updates
    cursor.execute("""
        SELECT COUNT(*) FROM location_logs WHERE tracking_id=?
    """, (tracking_id,))
    total_updates = cursor.fetchone()[0]

    # Hub stats
    cursor.execute("""
        SELECT hub_name, COUNT(*)
        FROM hub_entries
        WHERE tracking_id=?
        GROUP BY hub_name
    """, (tracking_id,))
    hub_stats = cursor.fetchall()
    hub_count = len(hub_stats)

    # Recent logs
    cursor.execute("""
        SELECT latitude, longitude, timestamp
        FROM location_logs
        WHERE tracking_id=?
        ORDER BY timestamp DESC
        LIMIT 5
    """, (tracking_id,))
    recent_logs = cursor.fetchall()

    # Nearest hub (latest)
    cursor.execute("""
        SELECT latitude, longitude
        FROM location_logs
        WHERE tracking_id=?
        ORDER BY timestamp DESC
        LIMIT 1
    """, (tracking_id,))
    loc = cursor.fetchone()

    if loc:
        nearest_hub, _ = nearest_hub(loc[0], loc[1])
    else:
        nearest_hub = "N/A"

    conn.close()

    return render_template(
        "analytics_dashboard.html",
        total_distance=total_distance,
        total_updates=total_updates,
        nearest_hub=nearest_hub,
        hub_count=hub_count,
        hub_stats=hub_stats,
        recent_logs=recent_logs
    )



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
