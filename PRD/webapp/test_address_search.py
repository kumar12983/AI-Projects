"""
Test script to debug the address search API endpoint
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'gnaf_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', '5432'))
}

def test_address_search():
    """Test the address search for school 41319 with street BURDETT and suburb HORNSBY"""
    
    acara_sml_id = 41319
    street = 'BURDETT'
    suburb = 'HORNSBY'
    limit = 100
    offset = 0
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get school location
    print(f"Fetching school location for acara_sml_id: {acara_sml_id}")
    cursor.execute("""
        SELECT 
            latitude,
            longitude
        FROM gnaf.school_geometry
        WHERE acara_sml_id = %s
        LIMIT 1
    """, (acara_sml_id,))
    
    school_location = cursor.fetchone()
    if not school_location:
        print("ERROR: School not found!")
        return
    
    school_lat = float(school_location['latitude'])
    school_lng = float(school_location['longitude'])
    print(f"School location: lat={school_lat}, lng={school_lng}")
    
    # Build filter conditions
    filter_conditions = []
    filter_params = []
    
    if street:
        filter_conditions.append("sl.street_name ILIKE %s")
        filter_params.append('%' + str(street) + '%')
    
    if suburb:
        filter_conditions.append("l.locality_name ILIKE %s")
        filter_params.append('%' + str(suburb) + '%')
    
    additional_where = ""
    if filter_conditions:
        additional_where = "AND " + " AND ".join(filter_conditions)
    
    # Execute the query
    query = f"""
        SELECT
            ad.address_detail_pid as gnaf_id,
            COALESCE(ad.number_first_prefix || '', '') ||
            COALESCE(ad.number_first::text || '', '') ||
            COALESCE(ad.number_first_suffix || ' ', ' ') ||
            COALESCE(sl.street_name || ' ', '') ||
            COALESCE(st.name || ', ', ', ') ||
            COALESCE(l.locality_name || ' ', ' ') ||
            COALESCE(s.state_abbreviation || ' ', ' ') ||
            COALESCE(ad.postcode || '', '') AS full_address,
            ad.number_first,
            ad.number_first_suffix,
            ad.number_last,
            ad.number_last_suffix,
            ad.flat_number,
            ft.name as flat_type,
            sl.street_name,
            st.name as street_type,
            l.locality_name,
            s.state_abbreviation,
            ad.postcode,
            ad.confidence,
            adg.latitude,
            adg.longitude,
            adg.geocode_type_code,
            -- Distance in km (calculated using geography for accuracy)
            ROUND(
                (ST_Distance(
                    adg.geom::geography,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                ) / 1000.0)::numeric,
                2
            ) as distance_km
        FROM gnaf.address_default_geocode adg
        INNER JOIN gnaf.address_detail ad
            ON ad.address_detail_pid = adg.address_detail_pid
        LEFT JOIN gnaf.flat_type_aut ft
            ON ad.flat_type_code = ft.code
        LEFT JOIN gnaf.street_locality sl
            ON ad.street_locality_pid = sl.street_locality_pid
        LEFT JOIN gnaf.street_type_aut st
            ON sl.street_type_code = st.code
        LEFT JOIN gnaf.locality l
            ON ad.locality_pid = l.locality_pid
        LEFT JOIN gnaf.state s
            ON l.state_pid = s.state_pid
        WHERE adg.geom IS NOT NULL
            -- Fast spatial index scan using GIST index on geom
            AND ST_DWithin(
                adg.geom,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                0.045  -- approximately 5km in degrees at Australian latitudes
            )
            {additional_where}
        ORDER BY 
            adg.geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        LIMIT %s OFFSET %s
    """
    
    # Build parameters
    query_params = [
        school_lng, school_lat,  # for distance calculation
        school_lng, school_lat,  # for ST_DWithin
    ] + filter_params + [
        school_lng, school_lat,  # for KNN ordering (<-> operator)
        limit, offset
    ]
    
    print(f"\nExecuting query with params: {query_params}")
    print(f"Additional WHERE clause: {additional_where}")
    
    try:
        cursor.execute(query, query_params)
        addresses = cursor.fetchall()
        
        print(f"\nFound {len(addresses)} addresses before filtering")
        
        # Filter to exact 5km
        filtered_addresses = [addr for addr in addresses if addr['distance_km'] <= 5.0]
        print(f"After 5km filter: {len(filtered_addresses)} addresses")
        
        # Show first 5 results
        for i, addr in enumerate(filtered_addresses[:5], 1):
            print(f"{i}. {addr['full_address']} - {addr['distance_km']}km")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    test_address_search()
