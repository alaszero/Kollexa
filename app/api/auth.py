"""Endpoints de autenticación API."""
from flask import request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.api import api_bp
from app.services.auth_service import authenticate_user
from app.utils.audit import log_action
from app.extensions import db, csrf


@api_bp.route('/auth/login', methods=['POST'])
@csrf.exempt
def api_login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Se requiere JSON con username y password'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Username y password son requeridos'}), 400

    user = authenticate_user(username, password)
    if not user:
        return jsonify({'error': 'Credenciales inválidas'}), 401

    token = create_access_token(identity=user.id)
    log_action('auth.login', entity_type='user', entity_id=user.id, user_id=user.id)
    db.session.commit()

    return jsonify({
        'data': {
            'token': token,
            'user': user.to_dict(include_permissions=True),
        }
    }), 200


@api_bp.route('/auth/me', methods=['GET'])
@jwt_required()
def api_me():
    user_id = get_jwt_identity()
    from app.models.user import User
    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    return jsonify({
        'data': user.to_dict(include_permissions=True)
    }), 200
