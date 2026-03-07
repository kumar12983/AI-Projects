#!/usr/bin/env python3
"""
Test script to verify the school catchment fix for Victoria addresses
Tests the Richmond, VIC address from the screenshot: 55 YARRA BVD, RICHMOND, VIC 3121
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection parameters
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'gnaf_db')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')


def test_victoria_catchment():
    """Test school catchment query for Richmond, VIC address"""
    
    # Coordinates for 55 YARRA BVD, RICHMOND, VIC 3121 (from screenshot)
    lat = -37.822245
    lng = 145.014316
    state = 'VIC'
    
    print("=" * 70)
    print("Testing School Catchment Fix for Victoria")
    print("=" * 70)
    print(f"\nAddress: 55 YARRA BVD, RICHMOND, VIC 3121")
    print(f"Coordinates: {lat}, {lng}")
    print(f"State: {state}")
    
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
        
        # First, check if VIC data exists
        print("\n" + "-" * 70)
        print("Step 1: Checking for Victoria data in database")
        print("-" * 70)
        
        cursor.execute("""
            SELECT state, COUNT(*) as count 
            FROM gnaf.school_catchments 
            GROUP BY state 
            ORDER BY state
        """)
        state_counts = cursor.fetchall()
        
        if state_counts:
            print("\nSchool catchments by state:")
            for row in state_counts:
                print(f"  {row['state']:3s}: {row['count']:,} catchments")
        else:
            print("\n⚠️  WARNING: No school catchment data found in database!")
            return
        
        # Check if VIC data exists
        vic_exists = any(row['state'] == 'VIC' for row in state_counts)
        if not vic_exists:
            print("\n⚠️  WARNING: No Victoria catchment data found!")
            print("    Victoria data needs to be loaded using load_victoria_catchments.py")
            return
        
        # Test the actual query
        print("\n" + "-" * 70)
        print("Step 2: Testing catchment query for Richmond address")
        print("-" * 70)
        
        query = """
            SELECT DISTINCT
                school_id,
                school_name,
                campus_name,
                school_type,
                state,
                year_level_code
            FROM gnaf.school_catchments
            WHERE state = %s
            AND ST_Contains(
                geometry,
                ST_SetSRID(ST_MakePoint(%s, %s), 4326)
            )
            ORDER BY school_type, school_name
        """
        
        cursor.execute(query, (state, lng, lat))
        schools = cursor.fetchall()
        
        print(f"\nFound {len(schools)} school catchments for this address:")
        
        if schools:
            for school in schools:
                print(f"\n  ✓ {school['school_name']}")
                if school['campus_name']:
                    print(f"    Campus: {school['campus_name']}")
                print(f"    Type: {school['school_type']}")
                if school['year_level_code']:
                    print(f"    Year Level: {school['year_level_code']}")
                print(f"    School ID: {school['school_id']}")
        else:
            print("\n  ⚠️  No school catchments found for this address")
            print("     This could mean:")
            print("     1. The address is outside all school catchment zones")
            print("     2. The coordinates are incorrect")
            print("     3. Victoria data is not loaded properly")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        if schools:
            print("✓ TEST PASSED - School catchments found!")
        else:
            print("⚠️  TEST INCOMPLETE - No catchments found (see reasons above)")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    test_victoria_catchment()
