import os
import sys
import pytest
import uuid
from werkzeug.security import generate_password_hash
import tempfile
import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app
from db import global_init, create_session, SqlAlchemyBase
from ORM.models import User, Survey, Question, QuestionType, Option, Answer

def get_unique_user_data():
    """Generate unique user data to avoid integrity errors."""
    unique_id = uuid.uuid4().hex[:8]
    return {
        "username": f"testuser_{unique_id}",
        "email": f"test_{unique_id}@example.com",
        "password": "password123",
    }

@pytest.fixture(scope="function", autouse=True)
def reset_db():
    """Reset database before each test."""
    # Set environment variables for testing
    os.environ["DB_TYPE"] = "sqlite"
    os.environ["DB_FILE_PATH"] = ":memory:"

    # Initialize database
    global_init()

    # Create tables
    session = create_session()
    SqlAlchemyBase.metadata.drop_all(bind=session.get_bind())
    SqlAlchemyBase.metadata.create_all(bind=session.get_bind())
    session.close()

    yield

@pytest.fixture
def app():
    """Create and configure a Flask app for testing."""
    # Create the Flask app
    app = flask_app
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "JWT_SECRET_KEY": "test_key",
        "UPLOAD_FOLDER": tempfile.mkdtemp(),
        "JWT_ACCESS_TOKEN_EXPIRES": datetime.timedelta(hours=1),
        "JWT_REFRESH_TOKEN_EXPIRES": datetime.timedelta(days=30),
    })

    # Create a test context
    with app.app_context():
        yield app

@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()

@pytest.fixture
def db_session():
    """Create a new database session for a test."""
    session = create_session()
    yield session
    session.close()

@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user_data = get_unique_user_data()
    user = User(
        username=user_data["username"],
        email=user_data["email"],
        password_hash=generate_password_hash(user_data["password"]),
        is_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    # Store the credentials for use in tests
    user.raw_password = user_data["password"]
    return user

@pytest.fixture
def admin_user(db_session):
    """Create an admin user."""
    user_data = get_unique_user_data()
    admin = User(
        username=user_data["username"],
        email=user_data["email"],
        password_hash=generate_password_hash(user_data["password"]),
        is_admin=True,
    )
    db_session.add(admin)
    db_session.commit()

    # Store the credentials for use in tests
    admin.raw_password = user_data["password"]
    return admin

@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers with JWT token."""
    response = client.post("/api/token", json={
        "username": test_user.username,
        "password": test_user.raw_password,
    })

    token = response.json["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_auth_headers(client, admin_user):
    """Get authentication headers with admin JWT token."""
    response = client.post("/api/token", json={
        "username": admin_user.username,
        "password": admin_user.raw_password,
    })

    token = response.json["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_survey(db_session, test_user):
    """Create a test survey with questions."""
    survey = Survey(
        title="Test Survey",
        description="A survey for testing",
        author_id=test_user.id,
    )
    db_session.add(survey)
    db_session.flush()

    # Text question
    q1 = Question(
        survey_id=survey.id,
        type=QuestionType.TEXT,
        text="What is your name?",
        is_required=True,
    )
    db_session.add(q1)

    # Single choice question
    q2 = Question(
        survey_id=survey.id,
        type=QuestionType.SINGLE_CHOICE,
        text="What is your favorite color?",
        is_required=True,
    )
    db_session.add(q2)
    db_session.flush()

    # Add options for single choice question
    options = ["Red", "Green", "Blue", "Yellow"]
    for opt in options:
        option = Option(question_id=q2.id, text=opt)
        db_session.add(option)

    # Multiple choice question
    q3 = Question(
        survey_id=survey.id,
        type=QuestionType.MULTIPLE_CHOICE,
        text="Which programming languages do you know?",
        is_required=False,
    )
    db_session.add(q3)
    db_session.flush()

    # Add options for multiple choice question
    languages = ["Python", "JavaScript", "Java", "C++", "Ruby"]
    for lang in languages:
        option = Option(question_id=q3.id, text=lang)
        db_session.add(option)

    db_session.commit()
    return survey
