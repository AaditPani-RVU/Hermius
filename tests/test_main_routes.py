import pytest
from app import create_app
from flask import session
from app.database.db import get_db_connection
import sqlite3
from unittest.mock import patch

@pytest.fixture
def client():
    app = create_app()
    with app.test_client() as client:
        yield client

@pytest.fixture
def init_db():
    # Initialize the database with necessary tables
    conn = sqlite3.connect('main.db')
    c = conn.cursor()

    # Create necessary tables if not already present
    c.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY,
        room_code TEXT NOT NULL,
        created_at DATETIME NOT NULL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY,
        room_number TEXT NOT NULL,
        user TEXT NOT NULL,
        encrypted_message TEXT NOT NULL,
        datetime DATETIME NOT NULL
    )
    """)

    conn.commit()
    conn.close()

    yield
    # Cleanup after tests
    conn = sqlite3.connect('main.db')
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS rooms")
    c.execute("DROP TABLE IF EXISTS messages")
    conn.commit()
    conn.close()

def test_home_create_room(client, init_db):
    """Test room creation"""
    response = client.post("/", data={
        "create": "1",
        "code": "",
        "join": ""
    })
    assert response.status_code == 302  # Redirect to room
    assert "room" in session

def test_home_join_room(client, init_db):
    """Test joining an existing room"""
    # First, create a room manually
    room_code = "abcd"
    conn = sqlite3.connect('main.db')
    c = conn.cursor()
    c.execute("INSERT INTO rooms (room_code, created_at) VALUES (?, ?)", (room_code, "2025-04-20 12:00:00"))
    conn.commit()
    conn.close()

    response = client.post("/", data={
        "join": "1",
        "code": room_code
    })
    assert response.status_code == 302  # Redirect to room
    assert "room" in session
    assert session["room"] == room_code

def test_home_room_not_exist(client, init_db):
    """Test joining a room that does not exist"""
    response = client.post("/", data={
        "join": "1",
        "code": "nonexistent"
    })
    assert b"Room does not exist." in response.data

def test_room_page(client, init_db):
    room_code = "abcd"
    with sqlite3.connect('main.db') as conn:
        c = conn.cursor()
        c.execute("INSERT INTO rooms (room_code, created_at) VALUES (?, ?)", (room_code, "2025-04-20 12:00:00"))
        c.execute("INSERT INTO messages (room_number, user, encrypted_message, datetime) VALUES (?, ?, ?, ?)",
                  (room_code, "user1", "ENCRYPTED_MESSAGE_PLACEHOLDER", "2025-04-20 12:30:00"))
        conn.commit()

    with client.session_transaction() as session:
        session["name"] = "user1"  # Simulate login

    with patch('app.utils.helpers.decrypt_message') as mock_decrypt:
        mock_decrypt.return_value = "Decrypted message"
        response = client.get(f"/room/{room_code}")
        assert response.status_code == 200
        assert b"Decrypted message" in response.data


def test_initial_messages(client, init_db):
    """Test loading initial messages for a room"""
    room_code = "abcd"
    conn = sqlite3.connect('main.db')
    c = conn.cursor()
    c.execute("INSERT INTO rooms (room_code, created_at) VALUES (?, ?)", (room_code, "2025-04-20 12:00:00"))
    c.execute("INSERT INTO messages (room_number, user, encrypted_message, datetime) VALUES (?, ?, ?, ?)", 
              (room_code, "user1", "ENCRYPTED_MESSAGE_PLACEHOLDER", "2025-04-20 12:30:00"))
    conn.commit()
    conn.close()

    response = client.get(f"/initial_messages/{room_code}")
    assert response.status_code == 200
    assert b"Decrypted message" in response.data

def test_initial_messages(client, init_db):
    room_code = "abcd"

    from app.utils.helpers import cipher_suite
    encrypted_message = cipher_suite.encrypt(b"Hello!")

    with sqlite3.connect('main.db') as conn:
        c = conn.cursor()
        c.execute("INSERT INTO rooms (room_code, created_at) VALUES (?, ?)", (room_code, "2025-04-20 12:00:00"))
        c.execute("INSERT INTO messages (room_number, user, encrypted_message, datetime) VALUES (?, ?, ?, ?)",
                  (room_code, "user1", encrypted_message.decode(), "2025-04-20 12:30:00"))
        conn.commit()

    response = client.get(f"/initial_messages/{room_code}")
    assert response.status_code == 200
    assert b"Hello!" in response.data
