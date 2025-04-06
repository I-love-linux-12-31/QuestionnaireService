# api.py
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

from db import create_session
from ORM.models import User

api_bp = Blueprint('api', __name__)
