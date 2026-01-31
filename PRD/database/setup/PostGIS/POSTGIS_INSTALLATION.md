# PostGIS Installation Guide for Windows

PostGIS is required to use geospatial features with your GNAF database.

## Step 1: Check Your PostgreSQL Version

Open PowerShell or Command Prompt and run:

```powershell
psql --version
```

Or connect to your database and run:

```sql
SELECT version();
```

## Step 2: Install PostGIS

### Method 1: Stack Builder (Easiest)

1. **Open Stack Builder:**
   - Press Windows key, search for "Stack Builder"
   - Or navigate to: `C:\Program Files\PostgreSQL\[version]\bin\StackBuilder.exe`

2. **Select PostgreSQL Installation:**
   - Choose your PostgreSQL version from dropdown
   - Click "Next"

3. **Select PostGIS:**
   - Expand "Spatial Extensions"
   - Check ☑ "PostGIS X.X Bundle for PostgreSQL X.X"
   - Click "Next"

4. **Download and Install:**
   - Choose download directory
   - Click "Next" to download
   - Follow installation wizard
   - Accept default settings

### Method 2: Direct Download

1. **Download PostGIS:**
   - Visit: https://postgis.net/windows_downloads/
   - Or: https://download.osgeo.org/postgis/windows/
   - Download version matching your PostgreSQL (e.g., `postgis-bundle-pg16-3.4.1-1.zip`)

2. **Run Installer:**
   - Extract the downloaded file
   - Run the `.exe` installer
   - Follow the installation wizard
   - Select your PostgreSQL installation directory

3. **Components to Install:**
   - ☑ PostGIS (required)
   - ☑ GDAL (recommended)
   - ☑ raster drivers (optional)
   - ☑ topology (optional)

## Step 3: Verify Installation

After installation, restart PostgreSQL service:

```powershell
# Restart PostgreSQL service
Restart-Service postgresql-x64-16  # Adjust version number

# Or use Services app (services.msc)
```

Then connect to your database and verify:

```sql
-- Connect to your database
\c gnaf_db

-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Check version
SELECT PostGIS_Version();
SELECT PostGIS_Full_Version();
```

Expected output:
```
 postgis_version 
-----------------
 3.4 USE_GEOS=1 USE_PROJ=1 USE_STATS=1
```

## Step 4: Run GNAF Geospatial Setup

Once PostGIS is installed and verified:

```sql
\i C:/Users/kumar/Documents/workspace/realestate/gnaf_geospatial_setup.sql
```

## Troubleshooting

### Error: "extension postgis is not available"
- PostGIS is not installed correctly
- Try Stack Builder method above
- Ensure you downloaded correct version for your PostgreSQL

### Error: "could not load library"
- PostgreSQL service needs restart
- Run: `Restart-Service postgresql-x64-16` (adjust version)

### Error: "permission denied"
- You need superuser privileges
- Connect as postgres user:
  ```powershell
  psql -U postgres -d gnaf_db
  ```

### Can't Find Stack Builder
- Not installed with your PostgreSQL version
- Use Method 2 (Direct Download) instead

## Alternative: Use Docker with PostGIS

If installation is difficult, consider using Docker:

```powershell
# Pull PostGIS image
docker pull postgis/postgis:16-3.4

# Run PostgreSQL with PostGIS
docker run -d -p 5432:5432 --name gnaf-postgis -e POSTGRES_PASSWORD=yourpassword postgis/postgis:16-3.4
```

## Next Steps

After successful installation:
1. Run the setup script: `gnaf_geospatial_setup.sql`
2. Try example queries: `gnaf_geospatial_queries.sql`
3. Build your own spatial queries!

## Resources

- PostGIS Official: https://postgis.net/
- PostGIS Documentation: https://postgis.net/documentation/
- PostGIS Windows Downloads: https://postgis.net/windows_downloads/
