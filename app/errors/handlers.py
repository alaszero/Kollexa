"""Manejadores de errores globales."""
from flask import jsonify, render_template, request


def register_handlers(app):
    """Registrar error handlers en la app."""

    def is_api_request():
        return request.path.startswith('/api/')

    @app.errorhandler(400)
    def bad_request(e):
        if is_api_request():
            return jsonify({'error': 'Solicitud inválida', 'detail': str(e)}), 400
        return render_template('errors/400.html'), 400

    @app.errorhandler(401)
    def unauthorized(e):
        if is_api_request():
            return jsonify({'error': 'No autenticado'}), 401
        from flask import redirect, url_for
        return redirect(url_for('web_auth.login'))

    @app.errorhandler(403)
    def forbidden(e):
        if is_api_request():
            return jsonify({'error': 'Sin permisos para esta acción'}), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        if is_api_request():
            return jsonify({'error': 'Recurso no encontrado'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        if is_api_request():
            return jsonify({'error': 'Error interno del servidor'}), 500
        return render_template('errors/500.html'), 500
