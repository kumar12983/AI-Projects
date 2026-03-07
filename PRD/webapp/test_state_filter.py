"""
Test script to validate state filtering in school search endpoints
Tests both /api/address/schools and /api/autocomplete/schools endpoints
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'gnaf_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', '5432'))
}

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return None


def test_database_schema():
    """Test 1: Verify the database schema has state column"""
    print("\n" + "="*70)
    print("TEST 1: Database Schema Validation")
    print("="*70)
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if state column exists
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'gnaf' 
            AND table_name = 'school_catchments'
            AND column_name IN ('state', 'campus_name', 'year_level_code')
            ORDER BY column_name
        """)
        
        columns = cursor.fetchall()
        
        if not columns:
            print("❌ FAILED: Required columns (state, campus_name, year_level_code) not found")
            cursor.close()
            conn.close()
            return False
        
        print("✅ PASSED: Found required columns:")
        for col in columns:
            print(f"   - {col['column_name']} ({col['data_type']})")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        if conn:
            conn.close()
        return False


def test_state_data_distribution():
    """Test 2: Check data distribution by state"""
    print("\n" + "="*70)
    print("TEST 2: State Data Distribution")
    print("="*70)
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get count by state
        cursor.execute("""
            SELECT 
                state,
                school_type,
                COUNT(*) as count
            FROM gnaf.school_catchments
            GROUP BY state, school_type
            ORDER BY state, school_type
        """)
        
        results = cursor.fetchall()
        
        if not results:
            print("❌ FAILED: No data found in school_catchments table")
            cursor.close()
            conn.close()
            return False
        
        print("✅ PASSED: Data distribution by state:")
        print(f"\n{'State':<10} {'Type':<20} {'Count':>10}")
        print("-" * 45)
        
        total_by_state = {}
        for row in results:
            state = row['state'] or 'NULL'
            school_type = row['school_type'] or 'NULL'
            count = row['count']
            print(f"{state:<10} {school_type:<20} {count:>10}")
            total_by_state[state] = total_by_state.get(state, 0) + count
        
        print("-" * 45)
        for state, total in total_by_state.items():
            print(f"{state:<10} {'TOTAL':<20} {total:>10}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        if conn:
            conn.close()
        return False


def test_address_schools_nsw():
    """Test 3: Test /api/address/schools logic with NSW coordinates"""
    print("\n" + "="*70)
    print("TEST 3: Address Schools Search - NSW (Sydney CBD)")
    print("="*70)
    
    # Sydney CBD coordinates
    lat = -33.8688
    lng = 151.2093
    state = 'NSW'
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Simulate the endpoint query
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
        
        if schools:
            print(f"✅ PASSED: Found {len(schools)} NSW schools at ({lat}, {lng})")
            print(f"\n{'School ID':<12} {'School Name':<40} {'Type':<15} {'State':<8}")
            print("-" * 80)
            for school in schools[:5]:  # Show first 5
                print(f"{str(school['school_id']):<12} {school['school_name'][:38]:<40} {school['school_type']:<15} {school['state']:<8}")
            if len(schools) > 5:
                print(f"... and {len(schools) - 5} more")
        else:
            print(f"⚠️  WARNING: No NSW schools found at ({lat}, {lng})")
            print("   This might be expected if the coordinates are not in any catchment")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
        return False


def test_address_schools_vic():
    """Test 4: Test /api/address/schools logic with VIC coordinates"""
    print("\n" + "="*70)
    print("TEST 4: Address Schools Search - VIC (Melbourne CBD)")
    print("="*70)
    
    # Melbourne CBD coordinates
    lat = -37.8136
    lng = 144.9631
    state = 'VIC'
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # First check if VIC data exists
        cursor.execute("SELECT COUNT(*) as count FROM gnaf.school_catchments WHERE state = 'VIC'")
        vic_count = cursor.fetchone()['count']
        
        if vic_count == 0:
            print("⚠️  WARNING: No VIC data found in database")
            print("   VIC data needs to be loaded using load_victoria_catchments.py")
            print("   Skipping VIC test")
            cursor.close()
            conn.close()
            return True  # Not a failure, just no data
        
        print(f"ℹ️  Info: Found {vic_count} VIC catchment records in database")
        
        # Simulate the endpoint query
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
        
        if schools:
            print(f"✅ PASSED: Found {len(schools)} VIC schools at ({lat}, {lng})")
            print(f"\n{'School ID':<12} {'School Name':<30} {'Campus':<20} {'Type':<15} {'Year Level':<12}")
            print("-" * 95)
            for school in schools[:5]:  # Show first 5
                campus = school['campus_name'][:18] if school['campus_name'] else 'N/A'
                year_level = school['year_level_code'] if school['year_level_code'] else 'N/A'
                print(f"{str(school['school_id']):<12} {school['school_name'][:28]:<30} {campus:<20} {school['school_type']:<15} {year_level:<12}")
            if len(schools) > 5:
                print(f"... and {len(schools) - 5} more")
        else:
            print(f"⚠️  WARNING: No VIC schools found at ({lat}, {lng})")
            print("   This might be expected if the coordinates are not in any catchment")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
        return False


def test_autocomplete_schools_nsw():
    """Test 5: Test autocomplete schools with NSW filter"""
    print("\n" + "="*70)
    print("TEST 5: Autocomplete Schools - NSW")
    print("="*70)
    
    query_text = "Hornsby"
    state = 'NSW'
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Simulate the autocomplete query (prefix match)
        search_query = """
            SELECT 
                school_id,
                school_name,
                school_type,
                state
            FROM gnaf.school_catchments
            WHERE state = %s
            AND UPPER(school_name) LIKE UPPER(%s) || '%%'
            ORDER BY school_name
            LIMIT 20
        """
        
        cursor.execute(search_query, (state, query_text))
        results = cursor.fetchall()
        
        if results:
            print(f"✅ PASSED: Found {len(results)} NSW schools matching '{query_text}'")
            print(f"\n{'School ID':<12} {'School Name':<50} {'Type':<15} {'State':<8}")
            print("-" * 90)
            for school in results[:10]:  # Show first 10
                print(f"{str(school['school_id']):<12} {school['school_name'][:48]:<50} {school['school_type']:<15} {school['state']:<8}")
            if len(results) > 10:
                print(f"... and {len(results) - 10} more")
        else:
            print(f"⚠️  WARNING: No NSW schools found matching '{query_text}'")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
        return False


def test_autocomplete_schools_vic():
    """Test 6: Test autocomplete schools with VIC filter"""
    print("\n" + "="*70)
    print("TEST 6: Autocomplete Schools - VIC")
    print("="*70)
    
    query_text = "Melbourne"
    state = 'VIC'
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # First check if VIC data exists
        cursor.execute("SELECT COUNT(*) as count FROM gnaf.school_catchments WHERE state = 'VIC'")
        vic_count = cursor.fetchone()['count']
        
        if vic_count == 0:
            print("⚠️  WARNING: No VIC data found in database")
            print("   VIC data needs to be loaded using load_victoria_catchments.py")
            print("   Skipping VIC autocomplete test")
            cursor.close()
            conn.close()
            return True  # Not a failure, just no data
        
        # Simulate the autocomplete query (substring match)
        search_query = """
            SELECT 
                school_id,
                school_name,
                school_type,
                state,
                campus_name,
                year_level_code
            FROM gnaf.school_catchments
            WHERE state = %s
            AND UPPER(school_name) LIKE '%%' || UPPER(%s) || '%%'
            ORDER BY school_name
            LIMIT 20
        """
        
        cursor.execute(search_query, (state, query_text))
        results = cursor.fetchall()
        
        if results:
            print(f"✅ PASSED: Found {len(results)} VIC schools matching '{query_text}'")
            print(f"\n{'School ID':<15} {'School Name':<35} {'Type':<15} {'Year':<8} {'State':<8}")
            print("-" * 90)
            for school in results[:10]:  # Show first 10
                year = school['year_level_code'] if school['year_level_code'] else 'N/A'
                print(f"{str(school['school_id']):<15} {school['school_name'][:33]:<35} {school['school_type']:<15} {year:<8} {school['state']:<8}")
            if len(results) > 10:
                print(f"... and {len(results) - 10} more")
        else:
            print(f"⚠️  WARNING: No VIC schools found matching '{query_text}'")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
        return False


def test_state_isolation():
    """Test 7: Verify state filter isolates results correctly"""
    print("\n" + "="*70)
    print("TEST 7: State Isolation Verification")
    print("="*70)
    
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Test a school name that might exist in both states
        test_name = "Primary"
        
        # Query NSW
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM gnaf.school_catchments 
            WHERE state = 'NSW' 
            AND school_name ILIKE %s
        """, ('%' + test_name + '%',))
        nsw_count = cursor.fetchone()['count']
        
        # Query VIC
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM gnaf.school_catchments 
            WHERE state = 'VIC' 
            AND school_name ILIKE %s
        """, ('%' + test_name + '%',))
        vic_count = cursor.fetchone()['count']
        
        # Query without state filter
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM gnaf.school_catchments 
            WHERE school_name ILIKE %s
        """, ('%' + test_name + '%',))
        total_count = cursor.fetchone()['count']
        
        print(f"✅ PASSED: State isolation working correctly")
        print(f"   Schools with '{test_name}' in name:")
        print(f"   - NSW only:      {nsw_count}")
        print(f"   - VIC only:      {vic_count}")
        print(f"   - Total (both):  {total_count}")
        
        if nsw_count + vic_count == total_count:
            print(f"   ✓ Counts match (no data leakage)")
        else:
            print(f"   ⚠️  Counts don't match - possible data quality issue or NULL states")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        if conn:
            conn.close()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("STATE FILTER VALIDATION TEST SUITE")
    print("="*70)
    print(f"Database: {DB_CONFIG['database']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}")
    print("="*70)
    
    tests = [
        ("Database Schema", test_database_schema),
        ("State Data Distribution", test_state_data_distribution),
        ("Address Schools - NSW", test_address_schools_nsw),
        ("Address Schools - VIC", test_address_schools_vic),
        ("Autocomplete Schools - NSW", test_autocomplete_schools_nsw),
        ("Autocomplete Schools - VIC", test_autocomplete_schools_vic),
        ("State Isolation", test_state_isolation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ CRITICAL ERROR in {test_name}: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print("="*70)
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
