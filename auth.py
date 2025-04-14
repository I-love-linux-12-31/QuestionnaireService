# auth.py
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from db import create_session
from ORM.models import User

auth_bp = Blueprint("auth", __name__, template_folder="templates")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        db_session = create_session()
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        if db_session.query(User).filter(User.username == username).first():
            flash("Username already exists")
            return redirect(url_for("auth.register"))

        if db_session.query(User).filter(User.email == email).first():
            flash("Email already registered")
            return redirect(url_for("auth.register"))

        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
        )

        db_session.add(new_user)
        db_session.commit()
        login_user(new_user)
        return redirect(url_for("index"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db_session = create_session()
        user = db_session.query(User).filter(User.username == request.form["username"]).first()

        if not user or not check_password_hash(user.password_hash, request.form["password"]):
            flash("Invalid credentials")
            return redirect(url_for("auth.login"))

        login_user(user)
        return redirect(url_for("index"))

    return render_template("login.html")

@auth_bp.route("/logout")
@ login_required
def logout():
    logout_user()
    return redirect(url_for("index"))
