import hashlib
import os

import files

if os.environ.get("DOTENV", False):
    from dotenv import load_dotenv
    load_dotenv()

from flask import Flask, request, redirect, url_for, render_template, flash, current_app
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
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
    answer = Answer(
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
        device_type=ua.device.family,
        os=ua.os.family,
        browser=ua.browser.family,
        language=request.accept_languages.best,
        timezone=request.form['timezone']  # Получать через JS
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
