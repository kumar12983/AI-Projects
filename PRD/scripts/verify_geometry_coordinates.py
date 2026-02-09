"""
Verify school_geometry coordinates match school_location
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
print("SCHOOL GEOMETRY COORDINATE VERIFICATION")
print("=" * 70)

# Check school_geometry stats
print("\n1. School Geometry Table:")
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(latitude) as with_coords,
        COUNT(geom_5km_buffer) as with_buffer
    FROM gnaf.school_geometry
""")
sg_stats = cursor.fetchone()
print(f"   Total schools: {sg_stats[0]}")
print(f"   Schools with coordinates: {sg_stats[1]}")
print(f"   Schools with 5km buffer: {sg_stats[2]}")

# Check coordinate match between tables
print("\n2. Coordinate Match Verification:")
cursor.execute("""
    SELECT COUNT(*) 
    FROM gnaf.school_geometry sg
    INNER JOIN gnaf.school_profile_2025 pf ON sg.acara_sml_id = pf.acara_sml_id
    WHERE sg.latitude = pf.latitude 
    AND sg.longitude = pf.longitude
""")
matching = cursor.fetchone()[0]
print(f"   Coordinates matching between geometry & profile: {matching}")

# Sample comparison
print("\n3. Sample Coordinate Comparison:")
cursor.execute("""
    SELECT 
        sg.acara_sml_id,
        sg.school_name,
        sg.latitude as sg_lat,
        sg.longitude as sg_lon,
        pf.latitude as pf_lat,
        pf.longitude as pf_lon,
        sl.latitude as sl_lat,
        sl.longitude as sl_lon
    FROM gnaf.school_geometry sg
    INNER JOIN gnaf.school_profile_2025 pf ON sg.acara_sml_id = pf.acara_sml_id
    INNER JOIN gnaf.school_location sl ON sg.acara_sml_id = sl.acara_sml_id
    WHERE sg.latitude IS NOT NULL
    LIMIT 5
""")

print("   Format: school_geometry | school_profile_2025 | school_location")
for row in cursor.fetchall():
    print(f"   {row[1][:30]:30} | ID: {row[0]}")
    print(f"      Geometry:  {row[2]:.6f}, {row[3]:.6f}")
    print(f"      Profile:   {row[4]:.6f}, {row[5]:.6f}")
    print(f"      Location:  {row[6]:.6f}, {row[7]:.6f}")
    match = "✓ MATCH" if (row[2] == row[4] == row[6] and row[3] == row[5] == row[7]) else "✗ MISMATCH"
    print(f"      {match}")
    print()

# Check buffer validity
print("4. 5km Buffer Geometry Validation:")
cursor.execute("""
    SELECT 
        ST_GeometryType(geom_5km_buffer) as geom_type,
        COUNT(*) as count
    FROM gnaf.school_geometry
    WHERE geom_5km_buffer IS NOT NULL
    GROUP BY ST_GeometryType(geom_5km_buffer)
""")
for row in cursor.fetchall():
    print(f"   {row[0]}: {row[1]} schools")

print("\n" + "=" * 70)

cursor.close()
conn.close()
