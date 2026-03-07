#!/usr/bin/env python3
"""
Get School Catchments for an Address

This script demonstrates how to query school catchments for a given address
using latitude/longitude coordinates and state.

Usage:
    python get_catchments_for_address.py --lat -37.822245 --lng 145.014316 --state VIC
    python get_catchments_for_address.py --address "55 YARRA BVD, RICHMOND, VIC 3121"

Requirements:
    pip install psycopg2-binary python-dotenv
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'gnaf_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')


def get_school_catchments(lat, lng, state='NSW'):
    """
    Get all school catchments that contain the given address coordinates
    
    Args:
        lat (float): Latitude
        lng (float): Longitude
        state (str): State abbreviation (NSW, VIC, etc.)
    
    Returns:
        list: List of school catchment dictionaries
    """
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Query school catchments
        query = """
            SELECT DISTINCT
                school_id,
                school_name,
                campus_name,
                school_type,
                state,
                year_level_code,
                boundary_year,
                centroid_lat,
                centroid_lng,
                -- Distance from address to school centroid (km)
                ROUND(
                    ST_Distance(
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                        ST_SetSRID(ST_MakePoint(centroid_lng, centroid_lat), 4326)::geography
                    ) / 1000, 2
                ) AS distance_km,
                -- Catchment area (km²)
                ROUND((ST_Area(geometry::geography) / 1000000)::numeric, 2) AS area_km2,
                -- Year level flags
                kindergart, year1, year2, year3, year4, year5, year6,
                year7, year8, year9, year10, year11, year12,
                -- Metadata
                data_source
            FROM gnaf.school_catchments
            WHERE state = %s
            AND ST_Contains(
                geometry,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            )
            ORDER BY school_type, school_name
        """
        
        cursor.execute(query, (lng, lat, state, lng, lat))
        schools = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return schools
        
    except Exception as e:
        print(f"Database error: {e}")
        return []


def display_results(schools, lat, lng, state):
    """Display school catchment results in a formatted way"""
    
    print("=" * 80)
    print(f"School Catchments for Address")
    print("=" * 80)
    print(f"Coordinates: {lat}, {lng}")
    print(f"State: {state}")
    print(f"\nFound {len(schools)} school catchment(s)")
    print("=" * 80)
    
    if not schools:
        print("\n⚠️  No school catchments found for this address")
        print("   This could mean:")
        print("   - The address is outside all school catchment zones")
        print("   - The state data is not loaded in the database")
        print("   - The coordinates are incorrect")
        return
    
    # Group by school type
    by_type = {}
    for school in schools:
        school_type = school['school_type']
        if school_type not in by_type:
            by_type[school_type] = []
        by_type[school_type].append(school)
    
    # Display grouped results
    for school_type in sorted(by_type.keys()):
        print(f"\n{school_type} SCHOOLS:")
        print("-" * 80)
        
        for school in by_type[school_type]:
            print(f"\n  ✓ {school['school_name']}")
            
            if school['campus_name']:
                print(f"    Campus: {school['campus_name']}")
            
            if school['year_level_code']:
                print(f"    Year Level: {school['year_level_code']}")
            
            # Show year level flags
            year_levels = []
            if school.get('kindergart') == 'Y':
                year_levels.append('K')
            for year in range(1, 13):
                if school.get(f'year{year}') == 'Y':
                    year_levels.append(str(year))
            if year_levels:
                print(f"    Years Offered: {', '.join(year_levels)}")
            
            print(f"    School ID: {school['school_id']}")
            print(f"    Distance to School: {school['distance_km']} km")
            print(f"    Catchment Area: {school['area_km2']} km²")
            print(f"    Data Source: {school['data_source']}")


def main():
    """Main function with command-line argument parsing"""
    
    parser = argparse.ArgumentParser(
        description='Get school catchments for an address by coordinates'
    )
    parser.add_argument('--lat', type=float, help='Latitude')
    parser.add_argument('--lng', type=float, help='Longitude')
    parser.add_argument('--state', type=str, default='NSW', help='State (NSW, VIC, etc.)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    
    args = parser.parse_args()
    
    # Validate inputs
    if not args.lat or not args.lng:
        # Example addresses
        print("Please provide latitude and longitude coordinates.\n")
        print("Examples:")
        print("  # Richmond, VIC")
        print("  python get_catchments_for_address.py --lat -37.822245 --lng 145.014316 --state VIC")
        print("\n  # Hornsby, NSW")
        print("  python get_catchments_for_address.py --lat -33.7044 --lng 151.0993 --state NSW")
        print("\n  # Melbourne CBD, VIC")
        print("  python get_catchments_for_address.py --lat -37.8136 --lng 144.9631 --state VIC")
        return
    
    # Get school catchments
    schools = get_school_catchments(args.lat, args.lng, args.state)
    
    # Display results
    if args.json:
        import json
        print(json.dumps([dict(s) for s in schools], indent=2, default=str))
    else:
        display_results(schools, args.lat, args.lng, args.state)


if __name__ == '__main__':
    main()
