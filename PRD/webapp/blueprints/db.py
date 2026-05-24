"""
Shared database utilities for all blueprints.
Import DB_CONFIG, get_db_connection, is_coordinate_like, and _STREET_TYPE_TO_CODE from here.
"""
import os
import re

import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'gnaf_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', '5432'))
}

# Maps user-supplied street type suffix (abbreviation or full name) → GNAF street_type_code value
# GNAF stores full names as street_type_code (e.g. 'ROAD'), abbreviations in street_type_aut.name ('RD')
_STREET_TYPE_TO_CODE: dict[str, str] = {
    'ACCS': 'ACCESS', 'ALLY': 'ALLEY', 'ALWY': 'ALLEYWAY', 'APP': 'APPROACH', 'ARC': 'ARCADE',
    'AV': 'AVENUE', 'AVE': 'AVENUE', 'BCH': 'BEACH', 'BWLK': 'BOARDWALK', 'BVD': 'BOULEVARD',
    'BVDE': 'BOULEVARDE', 'BDGE': 'BRIDGE', 'BDWY': 'BROADWAY', 'BSWY': 'BUSWAY',
    'BYPA': 'BYPASS', 'CSWY': 'CAUSEWAY', 'CTR': 'CENTRE', 'CH': 'CHASE', 'CIR': 'CIRCLE',
    'CCT': 'CIRCUIT', 'CL': 'CLOSE', 'CON': 'CONCOURSE', 'CNR': 'CORNER', 'CSO': 'CORSO',
    'CT': 'COURT', 'CTYD': 'COURTYARD', 'CR': 'CRESCENT', 'CRES': 'CRESCENT',
    'DE': 'DEVIATION', 'DR': 'DRIVE', 'DVWY': 'DRIVEWAY', 'ENT': 'ENTRANCE',
    'ESP': 'ESPLANADE', 'EST': 'ESTATE', 'EXP': 'EXPRESSWAY', 'FWY': 'FREEWAY',
    'GWY': 'GATEWAY', 'GLEN': 'GLEN', 'GRA': 'GRANGE', 'GRN': 'GREEN', 'GR': 'GROVE',
    'HTS': 'HEIGHTS', 'HWY': 'HIGHWAY', 'HILL': 'HILL', 'JNC': 'JUNCTION',
    'LN': 'LANE', 'LANE': 'LANE', 'LNWY': 'LANEWAY', 'LINK': 'LINK', 'LOOP': 'LOOP',
    'MALL': 'MALL', 'MEWS': 'MEWS', 'MTWY': 'MOTORWAY', 'PDE': 'PARADE', 'PARK': 'PARK',
    'PWY': 'PARKWAY', 'PKWY': 'PARKWAY', 'PSGE': 'PASSAGE', 'PATH': 'PATH',
    'PWAY': 'PATHWAY', 'PL': 'PLACE', 'PLZA': 'PLAZA', 'PNT': 'POINT',
    'PREC': 'PRECINCT', 'PROM': 'PROMENADE', 'QY': 'QUAY', 'RAMP': 'RAMP',
    'RES': 'RESERVE', 'RTT': 'RETREAT', 'RDGE': 'RIDGE', 'RISE': 'RISE',
    'RVR': 'RIVER', 'RD': 'ROAD', 'RDS': 'ROADS', 'RDWY': 'ROADWAY',
    'ROW': 'ROW', 'RUN': 'RUN', 'SQ': 'SQUARE', 'ST': 'STREET', 'STRP': 'STRIP',
    'TCE': 'TERRACE', 'TRK': 'TRACK', 'TRL': 'TRAIL', 'TUNL': 'TUNNEL',
    'VALE': 'VALE', 'VLLY': 'VALLEY', 'VIEW': 'VIEW', 'VWS': 'VIEWS',
    'VLGE': 'VILLAGE', 'VSTA': 'VISTA', 'WALK': 'WALK', 'WKWY': 'WALKWAY',
    'WTWY': 'WATERWAY', 'WAY': 'WAY', 'WHRF': 'WHARF', 'WD': 'WOOD',
}
# Also accept full names as input (e.g. user types 'BINGARA ROAD')
for _c in list(_STREET_TYPE_TO_CODE.values()):
    _STREET_TYPE_TO_CODE.setdefault(_c, _c)


def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None


def is_coordinate_like(value):
    """
    Check if a string looks like a coordinate (latitude/longitude)
    Returns True if it's likely a coordinate that should be rejected
    """
    if not value:
        return False

    try:
        num = float(value)
        if '.' in value and (
            (-90 <= num <= 90) or
            (-180 <= num <= 180)
        ):
            return True
    except (ValueError, TypeError):
        pass

    return False
