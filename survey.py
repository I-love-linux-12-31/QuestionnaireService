# survey.py
"""
Surveys module
"""
import os

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app  # , current_app
from flask_login import login_required, current_user, AnonymousUserMixin
from werkzeug.utils import secure_filename

from db import create_session
from ORM.models import Survey, Question, QuestionType, Option, Answer, AnswerOption

from user_agents import parse

from files import allowed_file

survey_bp = Blueprint("survey", __name__, template_folder="templates", url_prefix="/surveys")


@survey_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    db_session = create_session()

    if request.method == "POST":
        try:
            # Create a survey
            new_survey = Survey(
                title=request.form["survey_title"],
                description=request.form["survey_description"],
                author_id=current_user.id,
            )
            db_session.add(new_survey)
            db_session.flush()  # To get the ID of the new survey

            # Process questions
            question_index = 0
            while True:
                q_prefix = f"questions[{question_index}]"
                if f"{q_prefix}[text]" not in request.form:
                    break

                question = Question(
                    text=request.form[f"{q_prefix}[text]"],
                    type=QuestionType(request.form[f"{q_prefix}[type]"]),
                    is_required=bool(request.form.get(f"{q_prefix}[required]")),
                    survey_id=new_survey.id,
                )

                # Process answer options for choice types
                if question.type in [QuestionType.SINGLE_CHOICE,
                                     QuestionType.MULTIPLE_CHOICE,
                                     QuestionType.LIMITED_CHOICE]:
                    options = request.form.getlist(f"{q_prefix}[options][]")
                    for opt_text in options:
                        if opt_text.strip():
                            question.options.append(Option(text=opt_text))

                # Choice limit for LIMITED_CHOICE
                if question.type == QuestionType.LIMITED_CHOICE:
                    question.choice_limit = int(request.form.get(f"{q_prefix}[limit]", 1))

                db_session.add(question)
                question_index += 1

            db_session.commit()
            flash("Survey created successfully!", "success")
            return redirect(url_for("survey.view", id=new_survey.id))

        except Exception as e:
            db_session.rollback()
            flash(f"Error creating survey: {str(e)}", "danger")

    return render_template("survey/create.html")


@survey_bp.route("/<int:id>")
def view(id):
    db_session = create_session()
    survey = db_session.query(Survey).get(id)
    is_owner = False
    if current_user.is_authenticated:
        is_owner = survey.author_id == current_user.id
    return render_template("survey/view.html", survey=survey, is_owner=is_owner)

@survey_bp.route("/my")
@login_required
def user_surveys():
    db_session = create_session()
    surveys = db_session.query(Survey).filter(
        Survey.author_id == current_user.id,
    ).order_by(
        Survey.created_at.desc(),
    ).all()
    return render_template("survey/list.html", surveys=surveys)


@survey_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    db_session = create_session()
    survey = db_session.query(Survey).get(id)

    if not survey or survey.author_id != current_user.id:
        # abort(403)
        db_session.close()
        return "Access Denied", 403

    if request.method == "POST":
        try:
            # Update basic data
            survey.title = request.form["survey_title"]
            survey.description = request.form["survey_description"]
            survey.require_login = "require_login" in request.form

            # Delete old questions and their options
            for question in survey.questions:
                db_session.delete(question)

            # Add new questions (similar to create)
            question_index = 0
            while True:
                q_prefix = f"questions[{question_index}]"
                if f"{q_prefix}[text]" not in request.form:
                    break

                question = Question(
                    text=request.form[f"{q_prefix}[text]"],
                    type=QuestionType(request.form[f"{q_prefix}[type]"]),
                    is_required=bool(request.form.get(f"{q_prefix}[required]")),
                    survey_id=survey.id,
                )

                # Process options for choice questions
                if question.type in [QuestionType.SINGLE_CHOICE,
                                     QuestionType.MULTIPLE_CHOICE,
                                     QuestionType.LIMITED_CHOICE]:
                    options = request.form.getlist(f"{q_prefix}[options][]")
                    for opt_text in options:
                        if opt_text.strip():
                            question.options.append(Option(text=opt_text))

                # Choice limit for LIMITED_CHOICE
                if question.type == QuestionType.LIMITED_CHOICE:
                    question.choice_limit = int(request.form.get(f"{q_prefix}[limit]", 1))

                db_session.add(question)
                question_index += 1

            db_session.commit()
            flash("Survey updated successfully", "success")
            return redirect(url_for("survey.view", id=id))

        except Exception as e:
            db_session.rollback()
            flash(f"Error: {str(e)}", "danger")

    return render_template("survey/create.html", survey=survey)


@survey_bp.route("/<int:id>/take", methods=["GET", "POST"])
def take_survey(id):
    db_session = create_session()
    survey = db_session.query(Survey).get(id)

    # Check authorization
    if survey.require_login and isinstance(current_user, AnonymousUserMixin):
        return redirect(url_for("auth.login", next=request.url))

    # Check previous responses
    if current_user.is_authenticated:
        has_answered = (db_session.query(Answer)
                        .filter(Answer.user_id == current_user.id)
                        .join(Question)
                        .filter(Question.survey_id == id)
                        .first()
                        )

    else:
    # Check by IP (simplified)
        has_answered = db_session.query(
            Answer,
        ).filter(
            Answer.ip_address == request.remote_addr,
        ).join(Question).filter(Question.survey_id == id).first()

    if has_answered:
        flash("You have already taken this survey", "warning")
        return redirect(url_for("survey.view", id=id))

    if request.method == "POST":
        try:
            # Collect metadata
            ua = parse(request.user_agent.string)
            answer_data = {
                "ip_address": request.remote_addr,
                "user_agent": request.user_agent.string,
                "device_type": ua.device.family,
                "os": ua.os.family,
                "browser": ua.browser.family,
                "language": request.accept_languages.best,
                "timezone": request.form.get("timezone", "UTC"),
                "user_id": current_user.id if current_user.is_authenticated else None,
            }

            # Process each question
            print("DEBUG")
            print(request.form)
            print("FILES")
            print(request.files)

            for question in survey.questions:
                answer = Answer(question_id=question.id, **answer_data)

                if question.type == QuestionType.FILE:
                    file = request.files.get(f"q_{question.id}")
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(
                            current_app.config["UPLOAD_FOLDER"],
                            filename,
                        ))
                        answer.file_path = filename
                else:
                    # Process other question types

                    # ... save logic

                    if question.type in [
                        QuestionType.SINGLE_CHOICE,
                        QuestionType.MULTIPLE_CHOICE,
                        QuestionType.LIMITED_CHOICE,
                    ]:
                        answer = None

                        values = request.form.getlist(f"q_{question.id}")
                        # request.form.get(f"q_{question.id}")
                        print("values!", values)
                        for value in values:
                            _answer = Answer(question_id=question.id, **answer_data)

                            # value = request.form.get(f"q_{question.id}")
                            value = int(value)
                            try:
                                _answer.text_response = db_session.query(
                                    Option,
                                ).filter(
                                    Option.id == value,
                                    Option.question_id == question.id,
                                ).first().text
                            except Exception as e:
                                print(1, e, e.__class__.__name__)
                                raise e

                            try:
                                db_session.add(_answer)
                            except Exception as e:
                                print(2, e, e.__class__.__name__)
                                raise e

                    else:
                        value = request.form.get(f"q_{question.id}")
                        print(value)
                        answer.text_response = value

                if answer:
                    db_session.add(answer)



            db_session.commit()

            flash("Thank you for your participation!", "success")
            return redirect(url_for("survey.view", id=id))

        except Exception as e:
            db_session.rollback()
            print(e)
            print(e.__class__.__name__, dir(e))
            flash(f"Error: {str(e)}", "danger")

    return render_template("survey/take.html", survey=survey, QuestionType=QuestionType)


@survey_bp.route("/<int:survey_id>/delete", methods=["GET", "POST"])
@login_required
def delete(survey_id):
    db_session = create_session()
    survey = db_session.query(Survey).filter(
        Survey.id == survey_id,
        Survey.author_id == current_user.id,
    ).first()

    if not survey:
        db_session.close()
        return redirect(url_for("survey.user_surveys"))

    if request.method == "POST":
        db_session.delete(survey)
        db_session.commit()
        flash("Survey deleted", "success")
        return redirect(url_for("survey.user_surveys"))

    return render_template("survey/delete.html", survey=survey)
