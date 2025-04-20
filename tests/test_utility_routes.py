from unittest.mock import patch, MagicMock

def test_faq_page(client):
    response = client.get('/faq')
    assert response.status_code == 200
    assert b"FAQ" in response.data  # Adjust if you have specific text in template

def test_tos_page(client):
    response = client.get('/tos')
    assert response.status_code == 200
    assert b"Terms" in response.data  # Adjust to match your actual HTML

def test_privacy_policy_page(client):
    response = client.get('/privacy_policy')
    assert response.status_code == 200
    assert b"Privacy" in response.data

def test_contact_page_get(client):
    response = client.get('/contact')
    assert response.status_code == 200
    assert b"Contact" in response.data  # Adjust based on your template

@patch('app.routes.utility_routes.mail.send')  # Path to mail.send
def test_contact_form_post_success(mock_send, client):
    data = {
        "name": "Test User",
        "email": "test@example.com",
        "message": "Hello there!"
    }
    response = client.post('/contact', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Your message has been sent successfully!" in response.data
    mock_send.assert_called_once()

@patch('app.routes.utility_routes.mail.send', side_effect=Exception("Mail error"))
def test_contact_form_post_failure(mock_send, client):
    data = {
        "name": "Test User",
        "email": "test@example.com",
        "message": "Hello there!"
    }
    response = client.post('/contact', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b"An error occurred while sending the email" in response.data

def test_contact_form_post_incomplete(client):
    data = {
        "name": "",
        "email": "test@example.com",
        "message": ""
    }
    response = client.post('/contact', data=data, follow_redirects=True)
    assert b"Please fill out all fields." in response.data

@patch('app.routes.utility_routes.get_db_connection')
def test_get_users(mock_db, client):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [('user1',), ('user2',)]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_db.return_value = mock_conn

    response = client.get('/get_users/room1')
    assert response.status_code == 200
    assert response.json == {'users': ['user1', 'user2'], 'count': 2}

@patch('app.routes.utility_routes.get_db_connection')
def test_get_messages(mock_db, client):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [('user1', 'Hello'), ('user2', 'Hi')]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_db.return_value = mock_conn

    response = client.get('/get_messages/room1')
    assert response.status_code == 200
    assert response.json == {
        "messages": [{"user": "user1", "message": "Hello"}, {"user": "user2", "message": "Hi"}]
    }

def test_active_rooms(client):
    from app.state import rooms
    rooms.clear()
    rooms['room1'] = True
    rooms['room2'] = True

    response = client.get('/active_rooms')
    assert response.status_code == 200
    assert response.json["count"] == 2
    assert "room1" in response.json["active_rooms"]

def test_active_users_total(client):
    response = client.get('/active_users')
    assert response.status_code == 200
    assert "count" in response.json

def test_active_users_room(client):
    from app.state import room_users
    room_users['testroom'] = {'user1', 'user2'}
    response = client.get('/active_users/testroom')
    assert response.status_code == 200
    assert response.json == {'room': 'testroom', 'count': 2}
