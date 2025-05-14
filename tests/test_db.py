import pytest
import os
import uuid
from db import global_init, create_session, SqlAlchemyBase
from ORM.models import User, Survey, Question, QuestionType, Option, Answer

def test_db_connection():
    """Test basic database connection and session creation."""
    # Set to in-memory SQLite for testing
    os.environ["DB_TYPE"] = "sqlite"
    os.environ["DB_FILE_PATH"] = ":memory:"

    # Initialize the database
    global_init()

    # Create a session
    session = create_session()

    # Should have a working session
    assert session is not None

    # Tables should exist
    engine = session.get_bind()
    SqlAlchemyBase.metadata.create_all(engine)

    # Close the session
    session.close()

def test_create_user(db_session):
    """Test creating a user in the database."""
    # Create a unique username and email
    unique_id = uuid.uuid4().hex[:8]

    # Create a new user
    new_user = User(
        username=f"dbtest_{unique_id}",
        email=f"dbtest_{unique_id}@example.com",
        password_hash="hash_placeholder",
        is_admin=False,
    )

    # Add to database
    db_session.add(new_user)
    db_session.commit()

    # Should have an ID now
    assert new_user.id is not None

    # Fetch the user from database
    fetched_user = db_session.query(User).filter_by(username=new_user.username).first()

    # Should match
    assert fetched_user is not None
    assert fetched_user.id == new_user.id
    assert fetched_user.email == new_user.email

def test_survey_relationships(db_session):
    """Test relationships between Survey, Question, Option, and Answer."""
    # Create a user with unique data
    unique_id = uuid.uuid4().hex[:8]
    user = User(
        username=f"relation_test_{unique_id}",
        email=f"relation_{unique_id}@example.com",
        password_hash="hash_placeholder",
    )
    db_session.add(user)
    db_session.flush()

    # Create a survey
    survey = Survey(
        title="Relationship Test Survey",
        description="Testing database relationships",
        author_id=user.id,
    )
    db_session.add(survey)
    db_session.flush()

    # Create a question
    question = Question(
        survey_id=survey.id,
        type=QuestionType.SINGLE_CHOICE,
        text="Test question",
        is_required=True,
    )
    db_session.add(question)
    db_session.flush()

    # Create options
    options = []
    for i in range(3):
        option = Option(
            question_id=question.id,
            text=f"Option {i+1}",
        )
        db_session.add(option)
        options.append(option)
    db_session.flush()

    # Create an answer
    answer = Answer(
        question_id=question.id,
        user_id=user.id,
        text_response=options[0].text,
        ip_address="127.0.0.1",
        user_agent="DB Test",
        browser="Test Browser",
        device_type="Test Device",
        os="Test OS",
        language="en",
        timezone="UTC",
    )
    db_session.add(answer)
    db_session.commit()

    # Test relationships

    # User -> Surveys
    assert len(user.surveys) == 1
    assert user.surveys[0].id == survey.id

    # Survey -> Questions
    assert len(survey.questions) == 1
    assert survey.questions[0].id == question.id

    # Survey -> Author
    assert survey.author.id == user.id

    # Question -> Survey
    assert question.survey.id == survey.id

    # Question -> Options
    assert len(question.options) == 3
    assert set(o.id for o in question.options) == set(o.id for o in options)

    # Question -> Answers
    assert len(question.answers) == 1
    assert question.answers[0].id == answer.id

def test_question_types(db_session):
    """Test creating questions with different types."""
    # Create a user and survey first with unique data
    unique_id = uuid.uuid4().hex[:8]
    user = User(
        username=f"type_test_{unique_id}",
        email=f"types_{unique_id}@example.com",
        password_hash="hash_placeholder",
    )
    db_session.add(user)
    db_session.flush()

    survey = Survey(title="Types Test", description="Testing question types", author_id=user.id)
    db_session.add(survey)
    db_session.flush()

    # Create different question types and store them in a dict for later validation
    question_dict = {}
    types = [
        (QuestionType.TEXT, "Text question"),
        (QuestionType.WORD, "Word question"),
        (QuestionType.STRING, "String question"),
        (QuestionType.SINGLE_CHOICE, "Single choice question"),
        (QuestionType.MULTIPLE_CHOICE, "Multiple choice question"),
        (QuestionType.LIMITED_CHOICE, "Limited choice question"),
        (QuestionType.FILE, "File question"),
    ]

    for q_type, q_text in types:
        question = Question(
            survey_id=survey.id,
            type=q_type,
            text=q_text,
            is_required=True,
        )
        db_session.add(question)
        db_session.flush()  # Flush each question to get its ID

        # Store question in our dictionary
        question_dict[q_type] = question

        # Add options for choice questions
        if q_type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE, QuestionType.LIMITED_CHOICE]:
            # Create options for this question
            option_ids = []
            for i in range(3):
                option = Option(
                    question_id=question.id,
                    text=f"Option {i+1} for {q_type.value}",
                )
                db_session.add(option)
                db_session.flush()  # Flush to get option ID
                option_ids.append(option.id)

            # Store option IDs with question
            question_dict[f"{q_type}_option_ids"] = option_ids

    db_session.commit()

    # Check all questions were created
    questions = db_session.query(Question).filter(Question.survey_id == survey.id).all()
    assert len(questions) == len(types)

    # Check each question type
    for q_type, _ in types:
        # Check if this question type was created
        q = db_session.query(Question).get(question_dict[q_type].id)
        assert q is not None
        assert q.type == q_type

        # For choice questions, check options
        if q_type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE, QuestionType.LIMITED_CHOICE]:
            # Verify options separately using a direct query
            option_count = db_session.query(Option).filter(Option.question_id == q.id).count()
            assert option_count == 3

            # Verify each option ID exists in the database
            for option_id in question_dict[f"{q_type}_option_ids"]:
                option = db_session.query(Option).get(option_id)
                assert option is not None
                assert option.question_id == q.id
