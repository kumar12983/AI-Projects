"""
Hazard service — thin wrapper around nsw_hazard_api.
"""


def get_hazards(lat: float, lng: float) -> dict:
    from nsw_hazard_api import get_wind_region, query_eplanning_hazards

    output: dict = {'hazards': {}, 'errors': []}
    output['hazards']['Cyclone'] = get_wind_region(lat)
    hazards, hazard_errors = query_eplanning_hazards(lat, lng)
    output['hazards'].update(hazards)
    output['errors'].extend(hazard_errors)
    return output
