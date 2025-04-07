import hashlib
import os
import datetime
import files

if os.environ.get("DOTENV", False):
    from dotenv import load_dotenv
    load_dotenv()

from flask import Flask, request, redirect, url_for, render_template, flash, current_app, jsonify
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, verify_jwt_in_request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_swagger_ui import get_swaggerui_blueprint
from db import global_init, create_session
from ORM.models import User, Survey, Question, Option, Answer, AnswerOption

from user_agents import parse

from survey import survey_bp
from auth import auth_bp
from api import api_bp

app = Flask(__name__)
app.secret_key = hashlib.sha256(os.urandom(24)).hexdigest()
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(survey_bp)
app.register_blueprint(api_bp, url_prefix='/api')

# Swagger configuration
SWAGGER_URL = '/api/docs'  # URL for exposing Swagger UI
API_URL = '/static/swagger.json'  # Our API url (can of course be a local resource)

# Call factory function to create our blueprint
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={  # Swagger UI config overrides
        'app_name': "Questionnaire Service API"
    }
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

# JWT Configuration
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', hashlib.sha256(os.urandom(24)).hexdigest())
app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
print(F"JWT_SECRET_KEY: {JWT_SECRET_KEY}")
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = datetime.timedelta(days=30)
jwt = JWTManager(app)

login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

app.config['UPLOAD_FOLDER'] = files.UPLOAD_FOLDER


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
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/survey/<int:id>/submit', methods=['POST'])
def submit_survey(id):
    ua = parse(request.user_agent.string)
    
    # Try to get user_id from JWT if available
    user_id = None
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
    except:
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
        timezone=request.form.get('timezone', request.json.get('timezone') if request.is_json else None)
    )
    # ... обработка ответов


@app.route('/survey/<int:id>/stats')
@login_required
def survey_stats(id):
    db_session = create_session()
    survey = db_session.query(Survey).get(id)

    stats = []
    for question in survey.questions:
        stat = {
            'question': question,
            'answers_count': len(question.answers)
        }
        # ... специфическая логика для каждого типа вопроса
        stats.append(stat)

    return render_template('stats.html', stats=stats)


# Инициализация БД
global_init()

if __name__ == '__main__':
    app.run(debug=True)
