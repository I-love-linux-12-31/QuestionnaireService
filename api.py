# api.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required,
    get_jwt_identity, get_jwt, verify_jwt_in_request
)
from werkzeug.security import check_password_hash
from functools import wraps
from db import create_session
from ORM.models import User, Survey, Question, Option, Answer, AnswerOption

api_bp = Blueprint('api', __name__)

# Custom decorators for access control
def admin_required():
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("is_admin"):
                return fn(*args, **kwargs)
            return jsonify({"msg": "Admin access required"}), 403
        return decorator
    return wrapper

def check_answer_access():
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            
            # Admin has full access
            if claims.get("is_admin"):
                return fn(*args, **kwargs)
            
            answer_id = kwargs.get('id')
            if not answer_id:
                # If listing answers, the route function will handle filtering
                return fn(*args, **kwargs)
            
            db_session = create_session()
            answer = db_session.query(Answer).get(answer_id)
            
            if not answer:
                return jsonify({"msg": "Answer not found"}), 404
            
            # User can access only their own answers
            if answer.user_id and answer.user_id == claims.get("id"):
                return fn(*args, **kwargs)
            
            # Survey author can read answers to their surveys
            question = db_session.query(Question).get(answer.question_id)
            if question and question.survey.author_id == claims.get("id"):
                # Check if this is a read operation
                if request.method == "GET":
                    return fn(*args, **kwargs)
                return jsonify({"msg": "Survey authors can only read answers"}), 403
                
            return jsonify({"msg": "Access denied"}), 403
        return decorator
    return wrapper

# Тестовый эндпоинт для проверки JWT токена
@api_bp.route('/verify_token', methods=['GET'])
@jwt_required()
def verify_token():
    # Получаем идентификатор пользователя из JWT
    current_user_id = get_jwt_identity()
    # Получаем все claims (утверждения) из JWT
    claims = get_jwt()
    
    # Возвращаем информацию для проверки
    return jsonify({
        "message": "Token is valid and processed correctly",
        "identity": current_user_id,
        "claims": claims,
        "authorization_header": request.headers.get('Authorization', 'Not provided')
    }), 200

# Authentication routes
@api_bp.route('/token', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400
    
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    
    if not username or not password:
        return jsonify({"msg": "Missing username or password"}), 400
    
    db_session = create_session()
    user = db_session.query(User).filter(User.username == username).first()
    
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"msg": "Invalid credentials"}), 401
    
    # Create tokens with additional claims - ensuring user.id is a string
    access_token = create_access_token(
        identity=str(user.id),  # Convert to string to avoid "Subject must be a string" error
        additional_claims={
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "id": user.id
        }
    )
    refresh_token = create_refresh_token(
        identity=str(user.id),  # Convert to string to avoid "Subject must be a string" error
        additional_claims={
            "username": user.username,
            "is_admin": user.is_admin,
            "id": user.id
        }
    )
    
    return jsonify(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        username=user.username,
        is_admin=user.is_admin
    ), 200

@api_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    
    db_session = create_session()
    # Преобразуем current_user_id обратно в int, т.к. мы сохраняли его как строку
    try:
        user_id = int(current_user_id)
        user = db_session.query(User).get(user_id)
    except (ValueError, TypeError):
        return jsonify({"msg": "Invalid user ID"}), 400
    
    if not user:
        return jsonify({"msg": "User not found"}), 404
    
    access_token = create_access_token(
        identity=str(user.id),  # Convert to string to avoid "Subject must be a string" error
        additional_claims={
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "id": user.id
        }
    )
    
    return jsonify(access_token=access_token), 200

# User API endpoints (admin only)
@api_bp.route('/users', methods=['GET'])
@admin_required()
def get_users():
    db_session = create_session()
    users = db_session.query(User).all()
    result = [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "created_at": user.created_at.isoformat(),
            "is_admin": user.is_admin
        } for user in users
    ]
    return jsonify(result), 200

@api_bp.route('/users/<int:id>', methods=['GET'])
@admin_required()
def get_user(id):
    db_session = create_session()
    user = db_session.query(User).get(id)
    
    if not user:
        return jsonify({"msg": "User not found"}), 404
    
    result = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at.isoformat(),
        "is_admin": user.is_admin
    }
    return jsonify(result), 200

@api_bp.route('/users/<int:id>', methods=['PUT'])
@admin_required()
def update_user(id):
    db_session = create_session()
    user = db_session.query(User).get(id)
    
    if not user:
        return jsonify({"msg": "User not found"}), 404
    
    data = request.json
    if 'username' in data:
        user.username = data['username']
    if 'email' in data:
        user.email = data['email']
    if 'is_admin' in data:
        user.is_admin = data['is_admin']
    
    db_session.commit()
    
    result = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at.isoformat(),
        "is_admin": user.is_admin
    }
    return jsonify(result), 200

@api_bp.route('/users/<int:id>', methods=['DELETE'])
@admin_required()
def delete_user(id):
    db_session = create_session()
    user = db_session.query(User).get(id)
    
    if not user:
        return jsonify({"msg": "User not found"}), 404
    
    db_session.delete(user)
    db_session.commit()
    
    return jsonify({"msg": "User deleted"}), 200

# Survey API endpoints
@api_bp.route('/surveys', methods=['GET'])
@jwt_required()
def get_surveys():
    db_session = create_session()
    surveys = db_session.query(Survey).all()
    result = [
        {
            "id": survey.id,
            "title": survey.title,
            "description": survey.description,
            "author_id": survey.author_id,
            "created_at": survey.created_at.isoformat(),
            "is_active": survey.is_active,
            "require_login": survey.require_login
        } for survey in surveys
    ]
    return jsonify(result), 200

@api_bp.route('/surveys/<int:id>', methods=['GET'])
@jwt_required()
def get_survey(id):
    db_session = create_session()
    survey = db_session.query(Survey).get(id)
    
    if not survey:
        return jsonify({"msg": "Survey not found"}), 404
    
    result = {
        "id": survey.id,
        "title": survey.title,
        "description": survey.description,
        "author_id": survey.author_id,
        "created_at": survey.created_at.isoformat(),
        "is_active": survey.is_active,
        "require_login": survey.require_login,
        "questions": []
    }
    
    for question in survey.questions:
        q = {
            "id": question.id,
            "type": question.type.value,
            "text": question.text,
            "is_required": question.is_required,
            "choice_limit": question.choice_limit,
            "options": []
        }
        
        for option in question.options:
            q["options"].append({
                "id": option.id,
                "text": option.text
            })
        
        result["questions"].append(q)
    
    return jsonify(result), 200

@api_bp.route('/surveys', methods=['POST'])
@jwt_required()
def create_survey():
    current_user_id = get_jwt_identity()
    db_session = create_session()
    
    data = request.json
    new_survey = Survey(
        title=data['title'],
        description=data.get('description', ''),
        author_id=current_user_id,
        is_active=data.get('is_active', True),
        require_login=data.get('require_login', False)
    )
    
    db_session.add(new_survey)
    db_session.commit()
    
    return jsonify({
        "id": new_survey.id,
        "title": new_survey.title,
        "description": new_survey.description,
        "author_id": new_survey.author_id,
        "created_at": new_survey.created_at.isoformat(),
        "is_active": new_survey.is_active,
        "require_login": new_survey.require_login
    }), 201

@api_bp.route('/surveys/<int:id>', methods=['PUT'])
@jwt_required()
def update_survey(id):
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    
    db_session = create_session()
    survey = db_session.query(Survey).get(id)
    
    if not survey:
        return jsonify({"msg": "Survey not found"}), 404
    
    # Only allow survey author or admin to update
    if survey.author_id != current_user_id and not claims.get("is_admin"):
        return jsonify({"msg": "Access denied"}), 403
    
    data = request.json
    if 'title' in data:
        survey.title = data['title']
    if 'description' in data:
        survey.description = data['description']
    if 'is_active' in data:
        survey.is_active = data['is_active']
    if 'require_login' in data:
        survey.require_login = data['require_login']
    
    db_session.commit()
    
    return jsonify({
        "id": survey.id,
        "title": survey.title,
        "description": survey.description,
        "author_id": survey.author_id,
        "created_at": survey.created_at.isoformat(),
        "is_active": survey.is_active,
        "require_login": survey.require_login
    }), 200

@api_bp.route('/surveys/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_survey(id):
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    
    db_session = create_session()
    survey = db_session.query(Survey).get(id)
    
    if not survey:
        return jsonify({"msg": "Survey not found"}), 404
    
    # Only allow survey author or admin to delete
    if survey.author_id != current_user_id and not claims.get("is_admin"):
        return jsonify({"msg": "Access denied"}), 403
    
    db_session.delete(survey)
    db_session.commit()
    
    return jsonify({"msg": "Survey deleted"}), 200

# Answer API endpoints with access control
@api_bp.route('/answers', methods=['GET'])
@jwt_required()
def get_answers():
    current_user_id = get_jwt_identity()
    claims = get_jwt()
    is_admin = claims.get("is_admin", False)
    
    db_session = create_session()
    query = db_session.query(Answer)
    
    # Filter based on access rights
    if not is_admin:
        # Get surveys where the user is the author
        authored_surveys = db_session.query(Survey).filter(Survey.author_id == current_user_id).all()
        authored_survey_ids = [s.id for s in authored_surveys]
        
        # Get questions from those surveys
        questions_from_authored_surveys = db_session.query(Question).filter(
            Question.survey_id.in_(authored_survey_ids)
        ).all()
        questions_ids = [q.id for q in questions_from_authored_surveys]
        
        # User can see their own answers or answers to their surveys
        query = query.filter(
            (Answer.user_id == current_user_id) | 
            (Answer.question_id.in_(questions_ids))
        )
    
    answers = query.all()
    result = []
    
    for answer in answers:
        answer_data = {
            "id": answer.id,
            "user_id": answer.user_id,
            "question_id": answer.question_id,
            "text_response": answer.text_response,
            "file_path": answer.file_path,
            "created_at": answer.created_at.isoformat(),
            "ip_address": answer.ip_address,
            "browser": answer.browser,
            "device_type": answer.device_type,
            "os": answer.os,
            "selected_options": []
        }
        
        # Get the selected options for this answer
        for option in answer.options:
            answer_data["selected_options"].append({
                "id": option.id,
                "text": option.text
            })
        
        result.append(answer_data)
    
    return jsonify(result), 200

@api_bp.route('/answers/<int:id>', methods=['GET'])
@check_answer_access()
def get_answer(id):
    db_session = create_session()
    answer = db_session.query(Answer).get(id)
    
    if not answer:
        return jsonify({"msg": "Answer not found"}), 404
    
    answer_data = {
        "id": answer.id,
        "user_id": answer.user_id,
        "question_id": answer.question_id,
        "text_response": answer.text_response,
        "file_path": answer.file_path,
        "created_at": answer.created_at.isoformat(),
        "ip_address": answer.ip_address,
        "browser": answer.browser,
        "device_type": answer.device_type,
        "os": answer.os,
        "selected_options": []
    }
    
    # Get the selected options for this answer
    for option in answer.options:
        answer_data["selected_options"].append({
            "id": option.id,
            "text": option.text
        })
    
    return jsonify(answer_data), 200

@api_bp.route('/answers/<int:id>', methods=['PUT'])
@check_answer_access()
def update_answer(id):
    current_user_id = get_jwt_identity()
    
    db_session = create_session()
    answer = db_session.query(Answer).get(id)
    
    if not answer:
        return jsonify({"msg": "Answer not found"}), 404
    
    data = request.json
    
    if 'text_response' in data:
        answer.text_response = data['text_response']
    
    if 'selected_options' in data:
        # Clear existing option associations
        db_session.query(AnswerOption).filter(AnswerOption.answer_id == id).delete()
        
        # Add new option associations
        for option_id in data['selected_options']:
            option = db_session.query(Option).get(option_id)
            if option and option.question_id == answer.question_id:
                answer.options.append(option)
    
    db_session.commit()
    
    answer_data = {
        "id": answer.id,
        "user_id": answer.user_id,
        "question_id": answer.question_id,
        "text_response": answer.text_response,
        "file_path": answer.file_path,
        "created_at": answer.created_at.isoformat(),
        "selected_options": [{"id": o.id, "text": o.text} for o in answer.options]
    }
    
    return jsonify(answer_data), 200

@api_bp.route('/answers/<int:id>', methods=['DELETE'])
@check_answer_access()
def delete_answer(id):
    db_session = create_session()
    answer = db_session.query(Answer).get(id)
    
    if not answer:
        return jsonify({"msg": "Answer not found"}), 404
    
    # First delete answer_options relationships
    db_session.query(AnswerOption).filter(AnswerOption.answer_id == id).delete()
    
    # Then delete the answer
    db_session.delete(answer)
    db_session.commit()
    
    return jsonify({"msg": "Answer deleted"}), 200
