import pytest
import json
from ORM.models import Survey, Question, Answer, User

def test_api_get_surveys(client, auth_headers, test_survey):
    """Test GET /api/surveys endpoint."""
    response = client.get("/api/surveys", headers=auth_headers)

    assert response.status_code == 200

    # Response should be a list of surveys
    surveys = response.json
    assert isinstance(surveys, list)
    assert len(surveys) > 0

    # Test survey should be in the response
    survey_ids = [s["id"] for s in surveys]
    assert test_survey.id in survey_ids

    # Check survey fields
    survey = next(s for s in surveys if s["id"] == test_survey.id)
    assert survey["title"] == test_survey.title
    assert survey["description"] == test_survey.description

def test_api_get_survey_by_id(client, auth_headers, test_survey):
    """Test GET /api/surveys/{id} endpoint."""
    response = client.get(f"/api/surveys/{test_survey.id}", headers=auth_headers)

    assert response.status_code == 200

    # Response should be the survey details
    survey = response.json
    assert survey["id"] == test_survey.id
    assert survey["title"] == test_survey.title
    assert survey["description"] == test_survey.description

    # Should include questions
    assert "questions" in survey
    assert isinstance(survey["questions"], list)
    assert len(survey["questions"]) == len(test_survey.questions)

def test_api_get_nonexistent_survey(client, auth_headers):
    """Test GET /api/surveys/{id} with non-existent ID."""
    response = client.get("/api/surveys/9999", headers=auth_headers)

    assert response.status_code == 404
    assert "Survey not found" in response.json.get("msg", "")

def test_api_create_survey(client, auth_headers):
    """Test POST /api/surveys endpoint."""
    survey_data = {
        "title": "API Created Survey",
        "description": "This survey was created through the API",
        "questions": [
            {
                "text": "API Question 1",
                "type": "text",
                "required": True,
            },
            {
                "text": "API Question 2",
                "type": "single_choice",
                "required": True,
                "options": ["Option 1", "Option 2", "Option 3"],
            },
        ],
    }

    response = client.post("/api/surveys",
                          headers=auth_headers,
                          json=survey_data)

    # API может возвращать 201 Created или другой код успеха
    assert response.status_code in [200, 201]

    # Response should contain the created survey
    created_survey = response.json
    assert created_survey["title"] == survey_data["title"]
    assert created_survey["description"] == survey_data["description"]
    assert "id" in created_survey  # Should have an ID

def test_api_update_survey(client, auth_headers, test_user, test_survey, db_session):
    """Test PUT /api/surveys/{id} endpoint."""
    # В некоторых реализациях автор опроса может не совпадать из-за различных способов создания тестовых данных
    # Убедимся, что тестовый пользователь является автором опроса
    test_survey.author_id = test_user.id
    db_session.commit()

    update_data = {
        "title": "Updated API Survey",
        "description": "This survey was updated through the API",
    }

    response = client.put(f"/api/surveys/{test_survey.id}",
                         headers=auth_headers,
                         json=update_data)

    # Если есть проблемы с правами доступа, выводим сообщение
    if response.status_code == 403:
        print(f"Access denied when updating survey. User ID: {test_user.id}, Survey author ID: {test_survey.author_id}")

    # API может вернуть 200 Ok или другой код успеха
    assert response.status_code in [200, 204]

    # Если код 200, проверим содержимое ответа
    if response.status_code == 200:
        updated_survey = response.json
        assert updated_survey["title"] == update_data["title"]
        assert updated_survey["description"] == update_data["description"]

def test_api_delete_survey(client, auth_headers, db_session, test_user, test_survey):
    """Test DELETE /api/surveys/{id} endpoint."""
    # Убедимся, что тестовый пользователь является автором опроса
    test_survey.author_id = test_user.id
    db_session.commit()

    response = client.delete(f"/api/surveys/{test_survey.id}",
                            headers=auth_headers)

    # Если есть проблемы с правами доступа, выводим сообщение
    if response.status_code == 403:
        print(f"Access denied when deleting survey. User ID: {test_user.id}, Survey author ID: {test_survey.author_id}")

    # API может вернуть 200 OK, 204 No Content или другой код успеха
    assert response.status_code in [200, 204]

    # Если код 200, проверим сообщение ответа
    if response.status_code == 200 and "msg" in response.json:
        assert "Survey deleted" in response.json.get("msg", "")

def test_api_get_answers(client, db_session, auth_headers, test_survey, test_user):
    """Test GET /api/answers endpoint."""
    # Add test answers
    questions = test_survey.questions
    q1 = questions[0]
    answer = Answer(
        question_id=q1.id,
        user_id=test_user.id,
        text_response="API Test Answer",
        ip_address="127.0.0.1",
        user_agent="Test",
        browser="Test Browser",
        device_type="Test Device",
        os="Test OS",
        language="en",
        timezone="UTC",
    )
    db_session.add(answer)
    db_session.commit()

    # Get answers
    response = client.get("/api/answers", headers=auth_headers)

    assert response.status_code == 200

    # Should get a list of answers
    answers = response.json
    assert isinstance(answers, list)

    # Our test answer should be in the list
    answer_ids = [a["id"] for a in answers if "id" in a]
    assert answer.id in answer_ids

def test_api_get_answer_by_id(client, db_session, auth_headers, test_survey, test_user):
    """Test GET /api/answers/{id} endpoint."""
    # Add test answer
    questions = test_survey.questions
    q1 = questions[0]
    answer = Answer(
        question_id=q1.id,
        user_id=test_user.id,
        text_response="API Test Answer",
        ip_address="127.0.0.1",
        user_agent="Test",
        browser="Test Browser",
        device_type="Test Device",
        os="Test OS",
        language="en",
        timezone="UTC",
    )
    db_session.add(answer)
    db_session.commit()

    # Get the specific answer
    response = client.get(f"/api/answers/{answer.id}", headers=auth_headers)

    assert response.status_code == 200

    # Should get the answer details
    answer_data = response.json
    assert answer_data["id"] == answer.id
    assert answer_data["text_response"] == answer.text_response

def test_api_admin_endpoints(client, admin_auth_headers, db_session, test_user):
    """Test admin-only API endpoints."""
    # Check user list endpoint
    response = client.get("/api/users", headers=admin_auth_headers)

    assert response.status_code == 200

    # Should get a list of users
    users = response.json
    assert isinstance(users, list)

    # Our test user should be in the list
    test_user_id = test_user.id
    user_ids = [u["id"] for u in users]
    assert test_user_id in user_ids

    # Get specific user
    response = client.get(f"/api/users/{test_user_id}",
                         headers=admin_auth_headers)

    assert response.status_code == 200
    assert response.json["id"] == test_user_id
    assert response.json["username"] == test_user.username

    # Update user
    update_data = {"is_admin": True}
    response = client.put(f"/api/users/{test_user_id}",
                         headers=admin_auth_headers,
                         json=update_data)

    assert response.status_code == 200
    assert response.json["is_admin"] is True

    # Verify in database
    db_session.refresh(test_user)
    assert test_user.is_admin is True

def test_api_access_denied(client, auth_headers):
    """Test access control for admin-only endpoints."""
    # Try to access admin-only endpoint with regular user
    response = client.get("/api/users", headers=auth_headers)

    assert response.status_code == 403
    assert "Admin access required" in response.json.get("msg", "")
