"""
Verify school location import and update
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv('DB_HOST', 'localhost'),
    port=os.getenv('DB_PORT', '5432'),
    database=os.getenv('DB_NAME', 'gnaf_db'),
    user=os.getenv('DB_USER', 'postgres'),
    password=os.getenv('DB_PASSWORD', '')
)

cursor = conn.cursor()

print("=" * 70)
print("VERIFICATION REPORT")
print("=" * 70)

# Check school_location table
print("\n1. gnaf.school_location table:")
cursor.execute("SELECT COUNT(*) FROM gnaf.school_location")
total_count = cursor.fetchone()[0]
print(f"   Total schools: {total_count}")

cursor.execute("SELECT COUNT(*) FROM gnaf.school_location WHERE latitude IS NOT NULL AND longitude IS NOT NULL")
with_coords = cursor.fetchone()[0]
print(f"   Schools with coordinates: {with_coords}")

# Sample data
print("\n   Sample records:")
cursor.execute("""
    SELECT acara_sml_id, school_name, suburb, state, latitude, longitude 
    FROM gnaf.school_location 
    WHERE latitude IS NOT NULL 
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"   - ID: {row[0]}, {row[1]}, {row[2]}, {row[3]} - ({row[4]}, {row[5]})")

# Check school_profile_2025 updates
print("\n2. gnaf.school_profile_2025 table updates:")
cursor.execute("""
    SELECT COUNT(*) 
    FROM gnaf.school_profile_2025 
    WHERE latitude IS NOT NULL AND longitude IS NOT NULL
""")
updated_count = cursor.fetchone()[0]
print(f"   Schools with coordinates: {updated_count}")

# Sample updated data
print("\n   Sample updated records:")
cursor.execute("""
    SELECT acara_sml_id, school_name, suburb, state, latitude, longitude 
    FROM gnaf.school_profile_2025 
    WHERE latitude IS NOT NULL 
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"   - ID: {row[0]}, {row[1]}, {row[2]}, {row[3]} - ({row[4]}, {row[5]})")

# Check for schools in profile but not in location
print("\n3. Data matching analysis:")
cursor.execute("""
    SELECT COUNT(*) 
    FROM gnaf.school_profile_2025 sp
    LEFT JOIN gnaf.school_location sl ON sp.acara_sml_id = sl.acara_sml_id
    WHERE sl.acara_sml_id IS NULL
""")
not_in_location = cursor.fetchone()[0]
print(f"   Schools in profile but not in location: {not_in_location}")

cursor.execute("""
    SELECT COUNT(*) 
    FROM gnaf.school_location sl
    LEFT JOIN gnaf.school_profile_2025 sp ON sp.acara_sml_id = sl.acara_sml_id
    WHERE sp.acara_sml_id IS NULL
""")
not_in_profile = cursor.fetchone()[0]
print(f"   Schools in location but not in profile: {not_in_profile}")

print("\n" + "=" * 70)

cursor.close()
conn.close()
