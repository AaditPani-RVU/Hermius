from flask import Flask, render_template, request, session, redirect, url_for, jsonify, flash
from flask_mail import Mail, Message
from flask_socketio import join_room, leave_room, send, SocketIO, emit
import random
from string import ascii_uppercase
from datetime import datetime
import sqlite3
import os
from dotenv import load_dotenv
from lib import caesar_encrypt, caesar_decrypt

app = Flask(__name__)
app.config["SECRET_KEY"] = 'the_most_random_thing'

load_dotenv()
MAIL_SERVER = os.getenv('MAIL_SERVER')
MAIL_PORT = int(os.getenv('MAIL_PORT'))
MAIL_USE_TLS = os.getenv('MAIL_USE_TLS') == 'True'
MAIL_USE_SSL = os.getenv('MAIL_USE_SSL') == 'True'
MAIL_USERNAME = os.getenv('MAIL_USERNAME')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
app.config['MAIL_SERVER'] = MAIL_SERVER
app.config['MAIL_PORT'] = MAIL_PORT
app.config['MAIL_USE_TLS'] = MAIL_USE_TLS
app.config['MAIL_USE_SSL'] = MAIL_USE_SSL
app.config['MAIL_USERNAME'] = MAIL_USERNAME
app.config['MAIL_PASSWORD'] = MAIL_PASSWORD

mail = Mail(app)
socketio = SocketIO(app)
rooms = {}
conn = sqlite3.connect('main.db', check_same_thread=False)
c = conn.cursor()
# Add this to create the `rooms` table
def create_tables():
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        member_since TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_number TEXT,
        user TEXT,
        encrypted_message TEXT,
        datetime TEXT,
        FOREIGN KEY (user) REFERENCES users (username)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_code TEXT UNIQUE NOT NULL,
        created_at TEXT
    )''')

    conn.commit()

create_tables()

# Update the generate_unique_code function to check the database
def generate_unique_code(length):
    while True:
        code = "".join(random.choice(ascii_uppercase) for _ in range(length))
        existing_room = c.execute("SELECT * FROM rooms WHERE room_code = ?", (code,)).fetchone()
        if not existing_room:
            break
    return code

@app.route("/", methods=["POST", "GET"])
def home():
    if request.method == "POST":
        name = session.get('username') or f'Anonymous {random.randint(1, 1000)}'
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create") == "1"

        print(f"POST Request: join={join}, create={create}, code={code}")

        if join and not code:
            return render_template("home.html", error="Please enter a room code.", code=code)

        conn = sqlite3.connect('main.db')
        c = conn.cursor()
        if create:
            room = generate_unique_code(4)
            print(f"Generated Room Code: {room}")

            try:
                c.execute("INSERT INTO rooms (room_code, created_at) VALUES (?, ?)", (room, datetime.now()))
                conn.commit()
                print(f"Room {room} inserted into database.")

                # Ensure the new room is added to the active rooms dictionary
                rooms[room] = {"members": 0, "messages": []}

            except sqlite3.Error as e:
                print(f"Database Error: {e}")
                conn.close()
                return render_template("home.html", error=f"Database error: {str(e)}", code=code)

        else:
            c.execute("SELECT * FROM rooms WHERE room_code = ?", (code,))
            existing_room = c.fetchone()
            print(f"Existing Room Query Result: {existing_room}")

            if not existing_room:
                conn.close()
                return render_template("home.html", error="Room does not exist.", code=code)

        conn.close()
        session["room"] = room
        session["name"] = name
        print(f"Redirecting to room {room}...")
        return redirect(url_for("room", room_code=room))

    return render_template("home.html", username=session.get('username'))



# Update the room route to retrieve messages from the database
@app.route("/room/<room_code>")
def room(room_code):
    session["room"] = room_code

    # Open a fresh DB connection for retrieval
    conn = sqlite3.connect('main.db')
    c = conn.cursor()

    room = c.execute("SELECT * FROM rooms WHERE room_code = ?", (room_code,)).fetchone()

    if not room:
        conn.close()
        flash("Room does not exist.", "error")
        return redirect(url_for("home"))

    # Fetch stored messages from the database
    c.execute("SELECT user, encrypted_message, datetime FROM messages WHERE room_number=? ORDER BY datetime", (room_code,))
    encrypted_messages = c.fetchall()

    print(f"[DEBUG] Fetched raw messages from DB: {encrypted_messages}")

    conn.close()  # Close connection after fetching

    decrypted_messages = []
    for user, encrypted_message, timestamp in encrypted_messages:
        decrypted_message = caesar_decrypt(encrypted_message)
        print(f"[DEBUG] Decrypting message: {encrypted_message} -> {decrypted_message}")
        decrypted_messages.append({"user": user, "message": decrypted_message, "time": timestamp})

    print(f"[DEBUG] Final decrypted messages: {decrypted_messages}")

    return render_template("room.html", code=room_code, messages=decrypted_messages)

@app.route("/initial_messages/<room_code>")
def initial_messages(room_code):
    conn = sqlite3.connect("main.db")
    c = conn.cursor()
    
    # Fetch messages from the database
    c.execute("SELECT user, encrypted_message, datetime FROM messages WHERE room_number=? ORDER BY datetime", (room_code,))
    raw_messages = c.fetchall()
    conn.close()
    
    # Debug: Print fetched messages
    print(f"[DEBUG] Fetched messages for {room_code}: {raw_messages}")
    
    # Decrypt messages
    messages = []
    for user, encrypted_message, timestamp in raw_messages:
        if user is None:
            user = "Anonymous"

        decrypted_message = caesar_decrypt(encrypted_message)
        messages.append({"user": user, "message": decrypted_message, "time": timestamp})
    
    return jsonify(messages)

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/tos')
def tos():
    return render_template('tos.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == "POST":
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not username or not email or not password:
            flash('Please fill out all fields.', 'error')
            return redirect(url_for('signup'))

        try:
            c.execute('INSERT INTO users (username, email, password, member_since) VALUES (?, ?, ?, ?)', (username, email, password, datetime.now()))
            conn.commit()
            session['username'] = username
            flash('User registered successfully!', 'success')
            return redirect(url_for('home'))
        except sqlite3.IntegrityError:
            flash('Error: Username or email already exists.', 'error')
            return redirect(url_for('signup'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')


        if not username or not password:
            flash('Please fill out all fields.', 'error')
            return redirect(url_for('login'))

        user = c.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and user[3]==password:
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))

@app.route('/user_profile', methods=['GET'])
def user_profile():
    if 'username' not in session:
        flash('You need to be logged in to access this page.', 'error')
        return redirect(url_for('login'))

    username = session['username']
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()

    member_since = datetime.strptime(user[4], '%Y-%m-%d %H:%M:%S')
    return render_template('user_profile.html', user=username, email=user[2], member_since=member_since)

@app.route('/active_rooms', methods=['GET'])
def active_rooms():
    active_rooms_list = list(rooms.keys())
    return jsonify(active_rooms=active_rooms_list, count=len(active_rooms_list))

@app.route("/get_users/<room>")
def get_users(room):
    c.execute("SELECT DISTINCT user FROM messages WHERE room_number=?", (room,))
    users = c.fetchall()
    return jsonify(users=[user[0] for user in users], count=len(users))

@app.route('/active_users', methods=['GET'])
def active_users():
    total_users = sum(room["members"] for room in rooms.values())
    return jsonify(active_users=total_users)

@socketio.on("message")
def message(data):
    room = session.get("room")
    if not room:
        return 

    content = {
        "name": session.get("name"),
        "message": data["data"]
    }

    encrypted_message = caesar_encrypt(data["data"])

    print(f"[DEBUG] Saving message in room {room}: {data['data']} (Encrypted: {encrypted_message})")

    # Open a fresh DB connection for insertion
    conn = sqlite3.connect('main.db')
    c = conn.cursor()

    try:
        c.execute("INSERT INTO messages (room_number, user, encrypted_message, datetime) VALUES (?, ?, ?, ?)",
                  (room, session.get("username"), encrypted_message, datetime.now()))
        conn.commit()  # Ensure the database saves changes
        print("[DEBUG] Message inserted successfully.")
    except sqlite3.Error as e:
        print(f"[ERROR] Database Error: {e}")
    finally:
        conn.close()  # Always close connection after use
    
    send(content, to=room) 
    print(f"[DEBUG] {session.get('name')} said: {data['data']}")

@app.route('/modify_account', methods=['GET', 'POST'])
def modify_account():
    if 'username' not in session:
        flash('You need to be logged in to access this page.', 'error')
        return redirect(url_for('login'))

    username = session['username']

    if request.method == "POST":
        new_username = request.form.get('new_username')
        new_email = request.form.get('new_email')
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')


        if new_username:
            c.execute('UPDATE users SET username = ? WHERE username = ?', (new_username, username))
            session['username'] = new_username
            flash('Username updated successfully!', 'success')


        if new_email:
            c.execute('UPDATE users SET email = ? WHERE username = ?', (new_email, username))
            flash('Email updated successfully!', 'success')

        if old_password and new_password and confirm_password:
            user = c.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            if user and user[3] == old_password:
                if new_password == confirm_password:
                    c.execute('UPDATE users SET password = ? WHERE username = ?', (new_password, username))
                    flash('Password updated successfully!', 'success')
                else:
                    flash('New passwords do not match.', 'error')
            else:
                flash('Old password is incorrect.', 'error')

        conn.commit()

        return redirect(url_for('modify_account'))
    return render_template("modify_account.html", username=username)

    

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'username' not in session:
        flash('You need to be logged in to delete your account.', 'error')
        return redirect(url_for('login'))

    username = session['username']

    c.execute('DELETE FROM users WHERE username = ?', (username,))
    c.execute('DELETE FROM messages WHERE user = ?', (username,))
    conn.commit()

    session.clear()
    flash('Your account has been successfully deleted.', 'success')
    return redirect(url_for('home'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    name = ''
    email = ''
    if 'username' in session:
        name = session['username']
        user_email = c.execute('SELECT email FROM users WHERE username = ?', (name,)).fetchone()
        email = user_email[0] if user_email else ''

    if request.method == 'POST':
        contact_name = request.form.get('name')
        contact_email = request.form.get('email')
        message = request.form.get('message')

        if not contact_name or not contact_email or not message:
            flash('Please fill out all fields.', 'error')
            return redirect(url_for('contact'))

        # Compose the email
        msg = Message(subject=f"New Contact Form Submission from {contact_name}",
                      sender=app.config['MAIL_USERNAME'],
                      recipients=['learnwithmegh@gmail.com', 'aadi.pani@gmail.com', 'ayushvinayemail@gmail.com'],  # Replace with your email address
                      body=f"Name: {contact_name}\nEmail: {contact_email}\n\nMessage:\n{message}")

        try:
            mail.send(msg)
            flash('Your message has been sent successfully!', 'success')
        except Exception as e:
            flash(f'An error occurred while sending the email: {str(e)}', 'error')

        return redirect(url_for('contact'))

    return render_template('contact.html', name=name, email=email)


@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    send({"name": name, "message": "has entered the room!"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketio.on("disconnect_request")
def disconnect_request():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]

    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")


    socketio.emit("force_disconnect")

if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
