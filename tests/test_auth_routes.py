import pytest
import sys
import os

# Set the correct path for app imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.database.db import create_tables  # Ensure this function is defined in your db module

@pytest.fixture
def client():
    # Set up test configuration with in-memory SQLite database for testing
    test_config = {
        "TESTING": True,
        "SECRET_KEY": "test",  # You can use a mock secret key here
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
    # (Note: Since we are using an in-memory database, it will be discarded after each test)


import random
import string

def generate_random_username(length=8):
    """Generate a random string of letters and digits."""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def test_signup_login_logout(client):
    # Step 1: Generate a unique username
    random_username = generate_random_username()

    # Step 2: Signup with the unique username
    response = client.post("/signup", data={
        "username": random_username,
        "email": f"{random_username}@example.com",  # Ensure unique email as well
        "password": "Test@1237",
        "confirm_password": "Test@1237"
    }, follow_redirects=True)

    # Check if the response was a redirect (status code 200 after redirection)
    assert response.status_code == 200, f"Signup failed with status code {response.status_code}"

    # Print the response data to inspect the HTML content
    print(response.data.decode())

    # Check for the expected messages in the final redirected page (after redirect)
    assert b"Account created" in response.data or b"Welcome" in response.data, "Signup failed"



def test_signup_duplicate_username(client):
    # First signup attempt with a unique username
    client.post("/signup", data={
        "username": "duplicate",
        "email": "dup@example.com",
        "password": "pass1234",
        "confirm_password": "pass1234"
    })

    # Second signup with the same username to trigger a duplicate username error
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
    # Test to check that unauthenticated users cannot access the profile page
    response = client.get("/user_profile", follow_redirects=True)
    # Assert that login is required
    assert b"Login required" in response.data or b"Please login" in response.data, \
        "Unauthenticated access to profile was not blocked"


def test_modify_account_requires_login(client):
    # Test to check that unauthenticated users cannot access the modify account page
    response = client.get("/modify_account", follow_redirects=True)
    # Assert that login is required
    assert b"You need to be logged in" in response.data or b"Please login" in response.data, \
        "Unauthenticated access to modify_account was not blocked"
