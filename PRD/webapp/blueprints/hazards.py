"""
Hazard API routes.
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required

hazards_bp = Blueprint('hazards', __name__)


@hazards_bp.route('/api/hazards', methods=['GET'])
@login_required
def get_hazards_for_address():
    """
    Get hazards that contain a given address (lat/lng)
    Example: /api/hazards?lat=-33.8688&lng=151.2093
    """
    try:
        lat = float(request.args.get('lat', ''))
        lng = float(request.args.get('lng', ''))
    except (TypeError, ValueError):
        return jsonify({'error': 'Valid lat and lng parameters required'}), 400

    try:
        from nsw_hazard_api import get_wind_region, query_eplanning_hazards
    except ImportError:
        return jsonify({'error': 'Hazard API module not found'}), 500

    output = {
        "hazards": {},
        "errors": []
    }

    output["hazards"]["Cyclone"] = get_wind_region(lat)

    hazards, hazard_errors = query_eplanning_hazards(lat, lng)
    output["hazards"].update(hazards)
    output["errors"].extend(hazard_errors)

    return jsonify(output)
