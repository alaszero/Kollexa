"""Health check endpoint."""
from datetime import datetime, timezone
from flask import jsonify, current_app
from app.api import api_bp
from app.extensions import db, csrf


@api_bp.route('/health', methods=['GET'])
@csrf.exempt
def health_check():
    """Health check para verificar que el sistema funciona."""
    status = 'healthy'
    checks = {}

    # Verificar BD
    try:
        db.session.execute(db.text('SELECT 1'))
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {str(e)}'
        status = 'unhealthy'

    return jsonify({
        'status': status,
        'version': current_app.config.get('VERSION', 'unknown'),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'checks': checks,
    }), 200 if status == 'healthy' else 503
