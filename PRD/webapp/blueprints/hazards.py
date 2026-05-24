"""
Hazard API routes.
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required

from .validators import HazardQuery, validate_query_params

hazards_bp = Blueprint('hazards', __name__)


@hazards_bp.route('/api/hazards', methods=['GET'])
@login_required
def get_hazards_for_address():
    validated, err = validate_query_params(HazardQuery, request.args)
    if err:
        return err
    try:
        from services.hazard_service import get_hazards
    except ImportError:
        return jsonify({'error': 'Hazard API module not found'}), 500
    return jsonify(get_hazards(validated.lat, validated.lng))
