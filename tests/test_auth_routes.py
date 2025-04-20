import pytest
import sys
import os

# Set correct path for app imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
 # Make sure this function exists

from app.database.db import create_tables  # Ensure this function is defined in your db module

@pytest.fixture
def client():
    # Set up test configuration
    test_config = {
        "TESTING": True,
        "SECRET_KEY": "test",  # Add your secret key
        "DATABASE": ":memory:",  # Use an in-memory SQLite database for testing
    }
    
    # Create the app with the test configuration
    app = create_app(test_config=test_config)

    # Set up the application context for the app
    with app.app_context():
        # Make sure the database tables are created
        create_tables()  # Ensure this function is inside the app context too
        # Set up the test client within the application context
        yield app.test_client()

    # After the test, you can do any necessary cleanup, if needed



def test_signup_login_logout(client):
    # Step 1: Signup
    response = client.post("/signup", data={
        "username": "testuser",
        "email": "test@example.com",
        "password": "Test@1234",
        "confirm_password": "Test@1234"
    }, follow_redirects=True)

    # Assert the signup was successful (check for the "Account created" or "Welcome" message)
    assert b"Account created" in response.data or b"Welcome" in response.data, "Signup failed"

    # Step 2: Login
    response = client.post("/login", data={
        "username": "testuser",  # You are using username for login, ensure this matches your app's logic
        "password": "Test@1234"
    }, follow_redirects=True)

    # Assert login was successful (check for the "Logged in successfully" or "Welcome" message)
    assert b"Logged in successfully" in response.data or b"Welcome" in response.data, "Login failed"

    # Step 3: Logout
    response = client.get("/logout", follow_redirects=True)

    # Assert logout was successful (check for the "Logged out" or "Sign in" message)
    assert b"Logged out" in response.data or b"Sign in" in response.data, "Logout failed"


def test_signup_duplicate_username(client):
    # First signup
    client.post("/signup", data={
        "username": "duplicate",
        "email": "dup@example.com",
        "password": "pass1234",
        "confirm_password": "pass1234"
    })

    # Second signup with same username
    response = client.post("/signup", data={
        "username": "duplicate",
        "email": "dup2@example.com",
        "password": "pass1234",
        "confirm_password": "pass1234"
    }, follow_redirects=True)

    # Assert duplicate username error message
    assert b"Username already exists" in response.data or b"already taken" in response.data, \
        "Duplicate username not handled properly"


def test_profile_requires_login(client):
    response = client.get("/user_profile", follow_redirects=True)
    if b"Login required" not in response.data and b"Please login" not in response.data:
        pytest.fail("Unauthenticated access to profile was not blocked")

def test_modify_account_requires_login(client):
    response = client.get("/modify_account", follow_redirects=True)
    if b"You need to be logged in" not in response.data and b"Please login" not in response.data:
        pytest.fail("Unauthenticated access to modify_account was not blocked")
