#
"""
Main file. App entry point.
"""
import hashlib
import os
import datetime
import files
import json
from collections import Counter

if os.environ.get("DOTENV", False):
    from dotenv import load_dotenv
    load_dotenv()

from flask import Flask, request, redirect, url_for, render_template, flash, current_app, jsonify
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_swagger_ui import get_swaggerui_blueprint
from db import global_init, create_session
from ORM.models import User, Survey, Question, QuestionType, Option, Answer, AnswerOption

from user_agents import parse

from survey import survey_bp
from auth import auth_bp
from api import api_bp

app = Flask(__name__)
app.secret_key = hashlib.sha256(os.urandom(24)).hexdigest()
app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(survey_bp)
app.register_blueprint(api_bp, url_prefix="/api")

# Add JSON filter for templates
app.jinja_env.filters['tojson'] = lambda obj: json.dumps(obj)

# Swagger configuration
SWAGGER_URL = "/api/docs"  # URL for exposing Swagger UI
API_URL = "/static/swagger.json"  # Our API url (can of course be a local resource)

# Call factory function to create our blueprint
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={  # Swagger UI config overrides
        "app_name": "Questionnaire Service API",
    },
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

# JWT Configuration
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", hashlib.sha256(os.urandom(24)).hexdigest())
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
print(F"JWT_SECRET_KEY: {JWT_SECRET_KEY}")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(hours=1)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = datetime.timedelta(days=30)
jwt = JWTManager(app)

login_manager = LoginManager(app)
login_manager.login_view = "auth.login"

app.config["UPLOAD_FOLDER"] = files.UPLOAD_FOLDER


@login_manager.user_loader
def load_user(user_id):
    db_session = create_session()
    return db_session.query(User).get(int(user_id))

@app.teardown_appcontext
def shutdown_session(exception=None):
    # db_session.remove()
    # db_session.close()
    pass

# Главная страница
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/survey/<int:id>/submit", methods=["POST"])
def submit_survey(id):
    ua = parse(request.user_agent.string)

    # Try to get user_id from JWT if available
    user_id = None
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
    except Exception as e:
        # If JWT is not available, check if user is logged in through flask-login
        if current_user.is_authenticated:
            user_id = current_user.id

    answer = Answer(
        user_id=user_id,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
        device_type=ua.device.family,
        os=ua.os.family,
        browser=ua.browser.family,
        language=request.accept_languages.best,
        timezone=request.form.get("timezone", request.json.get("timezone") if request.is_json else None),
    )
    # ... обработка ответов


# API endpoint to get survey data for editing
@app.route("/api/survey/<int:id>/edit-data")
@login_required
def get_survey_edit_data(id):
    db_session = create_session()
    survey = db_session.query(Survey).get(id)
    
    # Check permission
    if not survey or survey.author_id != current_user.id:
        return jsonify({"error": "Access denied"}), 403
        
    # Prepare survey data
    survey_data = {
        "id": survey.id,
        "title": survey.title,
        "description": survey.description,
        "require_login": survey.require_login,
        "questions": []
    }
    
    for question in survey.questions:
        question_data = {
            "id": question.id,
            "text": question.text,
            "type": question.type.value,
            "required": question.is_required,
        }
        
        if question.type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE, QuestionType.LIMITED_CHOICE]:
            question_data["options"] = [option.text for option in question.options]
            
            if question.type == QuestionType.LIMITED_CHOICE:
                question_data["limit"] = question.choice_limit
                
        survey_data["questions"].append(question_data)
        
    return jsonify(survey_data)


# API endpoint to get survey stats data
@app.route("/api/survey/<int:id>/stats-data")
@login_required
def get_survey_stats_data(id):
    db_session = create_session()
    survey = db_session.query(Survey).get(id)
    
    # Check permission
    if not survey or (survey.author_id != current_user.id and not current_user.is_admin):
        return jsonify({"error": "Access denied"}), 403
        
    # Get all answers for this survey
    all_answers = []
    for question in survey.questions:
        all_answers.extend(question.answers)
    
    # Calculate total unique respondents by IP address
    total_responses = len(set([answer.ip_address for answer in all_answers])) if all_answers else 0
    
    # Get all unique devices (browsers) that took the survey
    all_browsers = Counter([answer.browser for answer in all_answers])
    all_os = Counter([answer.os for answer in all_answers])
    all_devices = Counter([answer.device_type for answer in all_answers])
    
    stats = []
    
    for question in survey.questions:
        answers = question.answers
        
        # Basic stats for all question types
        question_stat = {
            "id": question.id,
            "text": question.text,
            "type": question.type.value,
            "answers_count": len(answers),
            "response_rate": f"{len(answers) / total_responses * 100:.1f}%" if total_responses > 0 else "0%"
        }
        
        # Type-specific statistics
        if question.type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE, QuestionType.LIMITED_CHOICE]:
            # Count responses for each option
            option_counts = Counter([answer.text_response for answer in answers])
            
            # Calculate percentages
            option_stats = []
            labels = []
            values = []
            
            for option in question.options:
                count = option_counts.get(option.text, 0)
                percentage = (count / len(answers) * 100) if answers else 0
                option_stats.append({
                    "option": option.text,
                    "count": count,
                    "percentage": f"{percentage:.1f}%"
                })
                
                # For chart data
                labels.append(option.text)
                values.append(count)
            
            question_stat["option_stats"] = option_stats
            question_stat["chart_labels"] = labels
            question_stat["chart_values"] = values
            
        elif question.type == QuestionType.TEXT:
            # For text responses, provide some basic stats
            avg_length = sum(len(answer.text_response or "") for answer in answers) / len(answers) if answers else 0
            question_stat["text_stats"] = {
                "avg_length": round(avg_length, 1),
                "responses": [answer.text_response for answer in answers]
            }
            
        elif question.type == QuestionType.FILE:
            # For file uploads, count types
            file_types = Counter([os.path.splitext(answer.file_path or "")[1].lower() 
                               for answer in answers if answer.file_path])
            question_stat["file_stats"] = {
                "file_types": dict(file_types),
                "file_paths": [answer.file_path for answer in answers if answer.file_path]
            }
            
        stats.append(question_stat)
    
    survey_data = {
        "id": survey.id,
        "title": survey.title,
        "description": survey.description,
        "created_at": survey.created_at.strftime('%d.%m.%Y %H:%M'),
        "total_responses": total_responses,
        "browsers": dict(all_browsers),
        "operating_systems": dict(all_os),
        "devices": dict(all_devices),
        "stats": stats
    }
    
    return jsonify(survey_data)


@app.route("/survey/<int:id>/stats")
@login_required
def survey_stats(id):
    db_session = create_session()
    survey = db_session.query(Survey).get(id)
    
    # Check permission - only the survey creator or admin can view stats
    if not survey or (survey.author_id != current_user.id and not current_user.is_admin):
        flash("You don't have permission to view these statistics", "danger")
        return redirect(url_for('index'))

    stats = []
    
    # Get all answers for this survey
    all_answers = []
    for question in survey.questions:
        all_answers.extend(question.answers)
    
    # Calculate total unique respondents by IP address
    total_responses = len(set([answer.ip_address for answer in all_answers])) if all_answers else 0
    
    # Get all unique devices (browsers) that took the survey
    all_browsers = Counter([answer.browser for answer in all_answers])
    all_os = Counter([answer.os for answer in all_answers])
    all_devices = Counter([answer.device_type for answer in all_answers])
    
    for question in survey.questions:
        answers = question.answers
        
        # Basic stats for all question types
        question_stat = {
            "question": question,
            "answers_count": len(answers),
            "response_rate": f"{len(answers) / total_responses * 100:.1f}%" if total_responses > 0 else "0%"
        }
        
        # Type-specific statistics
        if question.type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE, QuestionType.LIMITED_CHOICE]:
            # Count responses for each option
            option_counts = Counter([answer.text_response for answer in answers])
            
            # Calculate percentages
            option_stats = []
            labels = []
            values = []
            
            for option in question.options:
                count = option_counts.get(option.text, 0)
                percentage = (count / len(answers) * 100) if answers else 0
                option_stats.append({
                    "option": option.text,
                    "count": count,
                    "percentage": f"{percentage:.1f}%"
                })
                
                # For chart data
                labels.append(option.text)
                values.append(count)
            
            question_stat["option_stats"] = option_stats
            question_stat["chart_labels"] = json.dumps(labels)
            question_stat["chart_values"] = json.dumps(values)
            
        elif question.type == QuestionType.TEXT:
            # For text responses, provide some basic stats
            avg_length = sum(len(answer.text_response or "") for answer in answers) / len(answers) if answers else 0
            question_stat["text_stats"] = {
                "avg_length": round(avg_length, 1),
                "responses": [answer.text_response for answer in answers]
            }
            
        elif question.type == QuestionType.FILE:
            # For file uploads, count types
            file_types = Counter([os.path.splitext(answer.file_path or "")[1].lower() 
                               for answer in answers if answer.file_path])
            question_stat["file_stats"] = {
                "file_types": dict(file_types),
                "file_paths": [answer.file_path for answer in answers if answer.file_path]
            }
            
        stats.append(question_stat)
    
    survey_meta = {
        "total_responses": total_responses,
        "browsers": dict(all_browsers),
        "operating_systems": dict(all_os),
        "devices": dict(all_devices)
    }
    
    return render_template("survey/stats.html", survey=survey, stats=stats, survey_meta=survey_meta)


# Инициализация БД
global_init()

if __name__ == "__main__":
    app.run(debug=True)
