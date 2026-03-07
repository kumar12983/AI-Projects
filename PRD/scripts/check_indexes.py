"""Check existing indexes on school_catchments table"""
import psycopg2
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent.parent / 'webapp' / '.env')
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'gnaf_db'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', '5432'))
}

conn = None
cursor = None

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("=" * 70)
    print("Current Indexes on gnaf.school_catchments")
    print("=" * 70)
    
    cursor.execute("""
        SELECT 
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = 'gnaf'
        AND tablename = 'school_catchments'
        ORDER BY indexname;
    """)
    
    results = cursor.fetchall()
    
    if results:
        print(f"\nFound {len(results)} indexes:\n")
        for row in results:
            print(f"Index: {row[0]}")
            print(f"  Definition: {row[1][:100]}...")
            print()
    else:
        print("\n⚠️  No indexes found!")
    
    # Check for expected indexes
    expected_indexes = [
        'idx_school_catchments_state',
        'idx_school_catchments_entity_code',
        'idx_school_catchments_centroid',
        'idx_school_catchments_boundary_year',
        'idx_school_catchments_state_type',
        'idx_school_catchments_name_trgm',
        'idx_school_catchments_geom'
    ]
    
    existing_index_names = [row[0] for row in results]
    missing_indexes = [idx for idx in expected_indexes if idx not in existing_index_names]
    
    print("=" * 70)
    if missing_indexes:
        print(f"❌ Missing {len(missing_indexes)} indexes:")
        for idx in missing_indexes:
            print(f"  - {idx}")
        print("\n👉 Need to run: add_victoria_support_indexes.sql")
    else:
        print("✅ All expected indexes exist!")
    print("=" * 70)
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
