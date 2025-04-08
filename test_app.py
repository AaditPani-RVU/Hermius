import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index(client):
    """Ensure the index route returns 200 or redirects."""
    response = client.get('/')
    assert response.status_code in (200, 302)

def test_login_page(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'login' in response.data.lower()

def test_signup_page(client):
    response = client.get('/signup')
    assert response.status_code == 200
    assert b'sign up' in response.data.lower()
