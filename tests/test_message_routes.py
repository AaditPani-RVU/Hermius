import os
import tempfile
import pytest
from flask import Flask, session
from werkzeug.utils import secure_filename
from app.routes.message_routes import message_routes  # Make sure this path is correct
from app.database.db import get_db_connection


@pytest.fixture
def test_app():
    app = Flask(__name__)
    app.secret_key = 'test_secret_key'
    app.config['TESTING'] = True
    app.config['UPLOAD_FOLDER'] = os.path.join(tempfile.gettempdir(), "uploads")

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Register blueprint
    app.register_blueprint(message_routes)

    # Use a temporary database
    db_fd, db_path = tempfile.mkstemp()
    app.config['DATABASE'] = db_path

    with app.app_context():
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT,
                content TEXT,
                created_at TEXT,
                room TEXT
            )
        ''')
        conn.commit()

    yield app

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(test_app):
    return test_app.test_client()


# -------------------------
# Test cases for message_routes
# -------------------------

def test_initial_messages_empty(client):
    with client.session_transaction() as sess:
        sess["name"] = "testuser"
    response = client.get("/initial_messages/testroom")
    assert response.status_code == 200
    assert response.is_json
    assert response.json == {"messages": []}


