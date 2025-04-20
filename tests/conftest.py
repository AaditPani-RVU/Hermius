import sys
import os
import tempfile
import pytest

# Add project root to PYTHONPATH so tests can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app

@pytest.fixture
def app():
    # Create a temporary file to use as the test database
    db_fd, db_path = tempfile.mkstemp()

    # Configure the app for testing, including the DATABASE path
    test_config = {
        "TESTING": True,
        "DATABASE": db_path,
        "WTF_CSRF_ENABLED": False,
        "MAIL_SUPPRESS_SEND": True,
    }

    # Create the Flask app with test configuration
    app = create_app(test_config=test_config)

    # Initialize the database tables
    with app.app_context():
        from app.database.db import create_tables
        create_tables()

    yield app

    # Teardown: close and remove the temporary database file
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()
