# app/sockets/handlers.py
from flask_socketio import emit, join_room, leave_room, send
from flask import session
import sqlite3
from datetime import datetime
import random

from app.extensions import socketio  # ✅ Use your actual SocketIO instance
from app.utils.helpers import encrypt_message
from app.state import (
    rooms,
    add_user_to_room,
    remove_user_from_room,
    update_room_activity,
    get_active_users_in_room,
)

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

@socketio.on("disconnect_request")
def disconnect_request():
    room = session.get("room")
    name = session.get("name")

    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]

    remove_user_from_room(room, name)

    send({"name": name, "message": "has left the room"}, to=room)

    emit("force_disconnect")

@socketio.on("join_room")
def handle_join(data):
    room = data.get("room")

    if "username" in session and session["username"]:
        username = session["username"]
    elif "name" not in session or not session["name"]:
        session["name"] = f"Anonymous {random.randint(1, 1000)}"
        username = session["name"]
    else:
        username = session["name"]

    session["room"] = room
    session["name"] = username

    join_room(room)
    add_user_to_room(room, username)

    emit("server_message", {"msg": f"{username} has joined the room."}, room=room)
    emit("update_user_list", list(get_active_users_in_room(room)), room=room)

@socketio.on("leave_room")
def handle_leave(data):
    room = data.get("room")
    username = data.get("username", "Anonymous")

    leave_room(room)
    remove_user_from_room(room, username)

    emit("server_message", {"msg": f"{username} has left the room."}, room=room)
    emit("update_user_list", list(get_active_users_in_room(room)), room=room)

@socketio.on("get_users")
def handle_get_users(data):
    room = data.get("room")
    if room:
        emit("update_user_list", list(get_active_users_in_room(room)), room=room)

@socketio.on("typing")
def handle_typing(data):
    room = data.get("room")
    username = data.get("username")
    emit("user_typing", {"username": username}, room=room, include_self=False)

@socketio.on("stop_typing")
def handle_stop_typing(data):
    room = data.get("room")
    username = data.get("username")
    emit("user_stopped_typing", {"username": username}, room=room, include_self=False)

@socketio.on("send_message")
def handle_send_message(data):
    room = session.get("room")
    username = session.get("name")

    if not room or not username or not data.get("message"):
        return

    message = data["message"]
    encrypted_message = encrypt_message(message)

    try:
        conn = sqlite3.connect('main.db')
        c = conn.cursor()
        c.execute("""
            INSERT INTO messages (room_number, user, encrypted_message, datetime)
            VALUES (?, ?, ?, ?)
        """, (room, username, encrypted_message, datetime.now()))
        conn.commit()
        message_id = c.lastrowid
    except sqlite3.Error:
        return
    finally:
        conn.close()

    update_room_activity(room)

    formatted_time = datetime.now().strftime("%I:%M %p")
    emit("receive_message", {
        "username": username,
        "message": message,
        "time": formatted_time,
        "message_id": message_id
    }, to=room)

# ✅ This is now just a dummy function — no need to pass or use socketio
def register_socketio_events():
    pass
