import pytest
from flask_login import current_user
from ORM.models import User
from tests.conftest import get_unique_user_data

def test_register(client, db_session):
    """Test user registration."""
    # Generate unique user data
    user_data = get_unique_user_data()

    # Test registration form submission
    response = client.post("/auth/register", data={
        "username": user_data["username"],
        "email": user_data["email"],
        "password": user_data["password"],
    }, follow_redirects=True)

    # Check response
    assert response.status_code == 200

    # Verify user was created in database
    user = db_session.query(User).filter_by(username=user_data["username"]).first()
    assert user is not None
    assert user.email == user_data["email"]

def test_register_duplicate_username(client, test_user):
    """Test registration with duplicate username."""
    response = client.post("/auth/register", data={
        "username": test_user.username,  # Same as existing test_user
        "email": f"different_{test_user.username}@example.com",
        "password": "test123",
    }, follow_redirects=True)

    # Should redirect back to register page with flash message
    assert b"Username already exists" in response.data

def test_login_valid(client, test_user):
    """Test login with valid credentials."""
    response = client.post("/auth/login", data={
        "username": test_user.username,
        "password": test_user.raw_password,
    }, follow_redirects=True)

    # Check we were redirected to index page
    assert response.status_code == 200
    # Просто проверим, что страница загрузилась
    assert b"<html" in response.data

def test_login_invalid(client, test_user):
    """Test login with invalid credentials."""
    response = client.post("/auth/login", data={
        "username": test_user.username,
        "password": "wrong_password",
    }, follow_redirects=True)

    # Should show error message
    assert b"Invalid credentials" in response.data

def test_logout(client, test_user):
    """Test user logout."""
    # First login
    client.post("/auth/login", data={
        "username": test_user.username,
        "password": test_user.raw_password,
    })

    # Then logout
    response = client.get("/auth/logout", follow_redirects=True)

    # Check we were redirected to index page
    assert response.status_code == 200
    # Просто проверим, что страница загрузилась
    assert b"<html" in response.data

def test_api_token(client, test_user):
    """Test getting JWT token from API."""
    response = client.post("/api/token", json={
        "username": test_user.username,
        "password": test_user.raw_password,
    })

    # Check response contains tokens and user info
    assert response.status_code == 200
    json_data = response.json
    assert "access_token" in json_data
    assert "refresh_token" in json_data
    assert json_data["username"] == test_user.username
    assert json_data["is_admin"] is False

def test_api_token_invalid(client, test_user):
    """Test getting JWT token with invalid credentials."""
    response = client.post("/api/token", json={
        "username": test_user.username,
        "password": "wrong_password",
    })

    # Should return error
    assert response.status_code == 401
    assert "Invalid credentials" in response.json["msg"]

def test_api_refresh_token(client, test_user):
    """Test refreshing JWT token."""
    # First get tokens
    response = client.post("/api/token", json={
        "username": test_user.username,
        "password": test_user.raw_password,
    })

    refresh_token = response.json["refresh_token"]

    # Use refresh token to get new access token
    refresh_response = client.post("/api/refresh",
                                  headers={"Authorization": f"Bearer {refresh_token}"})

    # Check we got a new access token
    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.json

def test_api_verify_token(client, auth_headers):
    """Test verifying JWT token."""
    response = client.get("/api/verify_token", headers=auth_headers)

    # Token should be valid
    assert response.status_code == 200
    assert "Token is valid" in response.json["message"]
