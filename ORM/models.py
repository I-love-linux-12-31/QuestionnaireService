from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime, Enum, VARCHAR
from sqlalchemy.orm import relationship
from flask_login import UserMixin
from db import SqlAlchemyBase
import enum


class QuestionType(enum.Enum):
    TEXT = "text"
    WORD = "word"
    STRING = "string"
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    LIMITED_CHOICE = "limited_choice"
    FILE = "file"


class User(SqlAlchemyBase, UserMixin):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(VARCHAR(64), unique=True)
    email = Column(VARCHAR(120), unique=True)
    password_hash = Column(VARCHAR(162))
    created_at = Column(DateTime, default=datetime.now)
    is_admin = Column(Boolean, default=False)
    surveys = relationship('Survey', backref='author')


class Survey(SqlAlchemyBase):
    __tablename__ = 'surveys'

    id = Column(Integer, primary_key=True)
    title = Column(VARCHAR(100))
    description = Column(Text)
    author_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    questions = relationship('Question', backref='survey')
    require_login = Column(Boolean, default=False)  # Новое поле


class Question(SqlAlchemyBase):
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True)
    survey_id = Column(Integer, ForeignKey('surveys.id'))
    type = Column(Enum(QuestionType))
    text = Column(VARCHAR(500))
    is_required = Column(Boolean, default=False)
    choice_limit = Column(Integer, nullable=True)
    options = relationship('Option', backref='question')


class Option(SqlAlchemyBase):
    __tablename__ = 'options'

    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('questions.id'))
    text = Column(VARCHAR(200))


class Answer(SqlAlchemyBase):
    __tablename__ = 'answers'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    question_id = Column(Integer, ForeignKey('questions.id'))
    text_response = Column(Text, nullable=True)
    file_path = Column(VARCHAR(300), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(VARCHAR(46))
    user_agent = Column(VARCHAR(200))
    browser = Column(VARCHAR(200))
    device_type = Column(VARCHAR(50))
    os = Column(VARCHAR(50))
    language = Column(VARCHAR(10))
    timezone = Column(VARCHAR(50))
    options = relationship('Option', secondary='answer_options')


class AnswerOption(SqlAlchemyBase):
    __tablename__ = 'answer_options'

    answer_id = Column(Integer, ForeignKey('answers.id'), primary_key=True)
    option_id = Column(Integer, ForeignKey('options.id'), primary_key=True)