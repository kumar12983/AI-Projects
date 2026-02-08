import psycopg2, os, time
from dotenv import load_dotenv

load_dotenv()
c = psycopg2.connect(host=os.getenv('DB_HOST', 'localhost'), 
                     database=os.getenv('DB_NAME', 'gnaf_db'), 
                     user=os.getenv('DB_USER', 'postgres'), 
                     password=os.getenv('DB_PASSWORD', ''), 
                     port=int(os.getenv('DB_PORT', '5432')))

# Set autocommit for CONCURRENT index creation
c.set_session(autocommit=True)
cur = c.cursor()

print('=' * 80)
print('CREATING MISSING SPATIAL INDEX')
print('=' * 80)
print('Creating GIST spatial index on gnaf.address_default_geocode.geom...')
print('This may take 2-3 minutes for 16.7 million rows...')
print('Please wait...\n')

start = time.time()

try:
    cur.execute('CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_address_default_geocode_geom ON gnaf.address_default_geocode USING GIST (geom)')
    elapsed = time.time() - start
    print(f'✓ Index created successfully in {elapsed:.1f} seconds')
    print(f'✓ Index name: idx_address_default_geocode_geom')
    print('\nThis index will dramatically improve spatial query performance!')
    
except Exception as e:
    print(f'Error: {e}')
    print('Index may already exist or there was an issue.')

# Verify the index was created
cur.execute("""
    SELECT indexname, pg_size_pretty(pg_relation_size(schemaname||'.'||indexname)) as size
    FROM pg_indexes 
    WHERE schemaname='gnaf' 
    AND tablename='address_default_geocode' 
    AND indexname='idx_address_default_geocode_geom'
""")

result = cur.fetchone()
if result:
    print(f'\n✓ Index verified: {result[0]}')
    print(f'✓ Index size: {result[1]}')
else:
    print('\n⚠ Index not found in pg_indexes')

c.close()

print('\n' + '=' * 80)
print('INDEX CREATION COMPLETE')
print('=' * 80)
