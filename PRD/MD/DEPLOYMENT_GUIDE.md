# GNAF Web Application - Deployment Guide

**Version:** 2.0  
**Last Updated:** January 26, 2026  
**Application:** Australian Address Lookup & Property Research Platform

---

## Table of Contents

1. [Overview](#overview)
2. [Pre-requisites](#pre-requisites)
3. [Solution Architecture](#solution-architecture)
4. [GNAF Data Setup](#gnaf-data-setup)
5. [Database Configuration](#database-configuration)
6. [Application Setup](#application-setup)
7. [Optional: School Catchment Integration](#optional-school-catchment-integration)
8. [Production Deployment](#production-deployment)
9. [Maintenance & Operations](#maintenance--operations)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### What is this Application?

A comprehensive web-based platform for searching and analyzing Australian addresses using the Geocoded National Address File (GNAF) dataset. The application provides:

- **15+ million address records** across all Australian states/territories
- **Real-time address search** with autocomplete
- **Geocoded coordinates** with distance calculations from state CBDs
- **Property links** to RealEstate.com.au and Domain.com.au (vertical equal-width buttons)
- **Google Maps integration** with pin-drop functionality
- **Hero images** on all pages for visual appeal (1200x400px Unsplash photos)
- **Professional typography** with Google Sans primary font
- **Responsive mobile design** optimized for tablets (768px) and phones (480px)
- **School catchment search** (NSW only, optional) - Find all addresses within a school catchment area
- **Interactive catchment maps** with boundary visualization using Leaflet.js
- **Performance-optimized** queries (<2s response time)

### Technology Stack

- **Backend:** Python 3.13, Flask 3.1.2
- **Database:** PostgreSQL 16+ with PostGIS extension
- **Frontend:** HTML5, CSS3, Vanilla JavaScript, Leaflet.js 1.9.4
- **Typography:** Google Sans (primary font), Momo (signature font for quotes)
- **Images:** Unsplash API (hero images, 1200x400px)
- **Data Processing:** pandas, geopandas, psycopg2
- **Spatial Analysis:** PostGIS (for school catchments)
- **Mapping:** Leaflet.js (OpenStreetMap tiles)
- **Design:** Professional corporate theme with responsive mobile layout

---

## Pre-requisites

### Hardware Requirements

**Minimum (Development):**
- CPU: 4 cores
- RAM: 16 GB
- Storage: 100 GB free space (SSD recommended)
- Network: Stable internet connection for data download

**Recommended (Production):**
- CPU: 8+ cores
- RAM: 32 GB
- Storage: 200 GB SSD (GNAF data + indexes ~40-50 GB)
- Network: High-speed connection, static IP

### Software Requirements

#### 1. Operating System
- **Windows:** Windows 10/11, Windows Server 2019+
- **Linux:** Ubuntu 20.04+, CentOS 8+, Debian 11+
- **macOS:** macOS 11+ (for development)

#### 2. PostgreSQL Database

**Installation:**

**Windows:**
```powershell
# Download from https://www.postgresql.org/download/windows/
# Or use Chocolatey
choco install postgresql
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

**Required Version:** PostgreSQL 12+ (PostgreSQL 16 recommended)

**Configuration:**
- Port: 5432 (default)
- User: postgres
- Password: Set during installation

#### 3. Python Environment

**Installation:**

**Windows:**
```powershell
# Download from https://www.python.org/downloads/
# Or use Chocolatey
choco install python313
```

**Linux:**
```bash
sudo apt install python3.13 python3-pip python3-venv
```

**Required Version:** Python 3.10+ (Python 3.13 recommended)

#### 4. Git (Optional, for version control)

```powershell
# Windows
choco install git

# Linux
sudo apt install git
```

---

## Solution Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Web Browser                              │
│  (Chrome, Firefox, Safari, Edge)                                │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP/HTTPS
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    Flask Web Server                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Static Files (HTML, CSS, JS)                            │  │
│  │  - index.html (Home page with statistics)                │  │
│  │  - search.html (Suburb/Postcode search)                  │  │
│  │  - address_lookup.html (Address search)                  │  │
│  │  - school_search.html (School catchment search)          │  │
│  │  - school_rankings.html (NSW school rankings article)    │  │
│  │  - style.css (Corporate design with Google Sans)         │  │
│  │  - main.js, search.js, address.js, school.js            │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  REST API Endpoints                                      │  │
│  │  - GET /api/stats (Statistics)                           │  │
│  │  - GET /api/search/suburbs (Suburb search)               │  │
│  │  - GET /api/search/postcodes (Postcode search)           │  │
│  │  - GET /api/address/search (Address lookup)              │  │
│  │  - GET /api/autocomplete/suburbs (Autocomplete)          │  │
│  │  - GET /api/autocomplete/streets (Autocomplete)          │  │
│  │  - GET /api/autocomplete/schools (School autocomplete)   │  │
│  │  - GET /api/suburbs/by-state (State suburbs)             │  │
│  │  - GET /api/school/<id>/info (School details)            │  │
│  │  - GET /api/school/<id>/addresses (Catchment addresses)  │  │
│  │  - GET /api/school/<id>/boundary (GeoJSON boundary)      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────┬───────────────────────────────────────────┘
                      │ psycopg2
                      │ SQL Queries
┌─────────────────────▼───────────────────────────────────────────┐
│                PostgreSQL Database (gnaf_db)                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  GNAF Schema (gnaf.*)                                    │  │
│  │  - address_detail (15M+ records)                         │  │
│  │    Includes: number_first, number_first_suffix,          │  │
│  │              number_last, number_last_suffix (19A, 19B)  │  │
│  │  - address_default_geocode (15M+ records)                │  │
│  │  - locality (14,125 records)                             │  │
│  │  - street_locality (~500K records)                       │  │
│  │  - state (9 records)                                     │  │
│  │  - street_type_aut, flat_type_aut                        │  │
│  │  - suburb_postcode (custom mapping)                      │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Performance Optimization                                │  │
│  │  - 17 Indexes (~2.5 GB)                                  │  │
│  │  - 2 Materialized Views (stats_summary, stats_by_state)  │  │
│  │  - DISTINCT ON queries (duplicate elimination)           │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Optional: School Catchments (public.* + gnaf.*)         │  │
│  │  - school_catchments_primary (1,661 records)             │  │
│  │  - school_catchments_secondary (447 records)             │  │
│  │  - school_catchments_future (14 records)                 │  │
│  │  - gnaf.school_catchments (materialized view)            │  │
│  │    (school_type data source for /api/school/<id>/info)   │  │
│  │  - PostGIS Extension (spatial queries)                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
┌──────────────┐
│   User       │
│  Browser     │
└──────┬───────┘
       │
       │ 1. Search Request
       │    (suburb, street, postcode, state)
       ▼
┌──────────────────┐
│  Flask Routes    │
│  app.py          │
└──────┬───────────┘
       │
       │ 2. SQL Query Construction
       │    (with filters & DISTINCT ON)
       ▼
┌──────────────────┐
│  PostgreSQL      │
│  Query Executor  │
└──────┬───────────┘
       │
       │ 3. Index Scan
       │    (17 optimized indexes)
       ▼
┌──────────────────┐
│  GNAF Tables     │
│  Join Operations │
└──────┬───────────┘
       │
       │ 4. Results (<2s)
       │    (address, coords, geocode)
       ▼
┌──────────────────┐
│  JSON Response   │
└──────┬───────────┘
       │
       │ 5. Client-side Processing
       │    (distance calc, URL construction)
       ▼
┌──────────────────┐
│  UI Rendering    │
│  - Table display │
│  - Tooltips      │
│  - Property links│
│  - Google Maps   │
└──────────────────┘
```

### External Integrations

```
GNAF Web App ─────┐
                  │
                  ├─► Google Fonts API
                  │   (Google Sans, Momo fonts)
                  │
                  ├─► Unsplash API
                  │   (Hero images for all pages)
                  │
                  ├─► Google Maps API
                  │   (Coordinate visualization + pin drop)
                  │
                  ├─► RealEstate.com.au
                  │   (Property listings)
                  │
                  └─► Domain.com.au
                      (Property listings)
```

---

## GNAF Data Setup

### Step 1: Download GNAF Data

#### Official Data Source

**Source:** Data.gov.au - Geocoded National Address File (GNAF)  
**URL:** https://data.gov.au/dataset/ds-dga-19432f89-dc3a-4ef3-b943-5326ef1dbecc/details

**Download Steps:**

1. Visit the Data.gov.au GNAF page
2. Click "Go to data source" or download the latest release
3. Select **"G-NAF PSVC Format"** (Pipe-Separated Values with Coordinates)
4. Choose **"All States and Territories"**
5. Download the ZIP file (~4-5 GB compressed, ~15-20 GB uncompressed)

**Example File Structure:**
```
G-NAF NOVEMBER 2025/
├── Authority Code/
│   ├── Authority_Code_ADDRESS_ALIAS_TYPE_AUT_psv.psv
│   ├── Authority_Code_FLAT_TYPE_AUT_psv.psv
│   ├── Authority_Code_GEOCODE_TYPE_AUT_psv.psv
│   ├── Authority_Code_STREET_TYPE_AUT_psv.psv
│   └── ...
├── Standard/
│   ├── ACT_ADDRESS_DEFAULT_GEOCODE_psv.psv
│   ├── ACT_ADDRESS_DETAIL_psv.psv
│   ├── NSW_ADDRESS_DEFAULT_GEOCODE_psv.psv
│   ├── NSW_ADDRESS_DETAIL_psv.psv
│   └── ...
└── README.txt
```

#### Alternative: Download Script (Windows)

```powershell
# Create download directory
New-Item -Path "C:\data\downloads" -ItemType Directory -Force

# Download GNAF (replace URL with current release)
$url = "https://data.gov.au/data/dataset/19432f89-dc3a-4ef3-b943-5326ef1dbecc/resource/[resource_id]/download/g-naf_nov25_allstates_gda2020_psv_1021.zip"
$output = "C:\data\downloads\gnaf_latest.zip"

Invoke-WebRequest -Uri $url -OutFile $output

# Extract
Expand-Archive -Path $output -DestinationPath "C:\data\downloads\" -Force
```

### Step 2: Verify Downloaded Data

**Check file integrity:**

```powershell
# Count PSV files
Get-ChildItem -Path "C:\data\downloads\G-NAF\" -Recurse -Filter "*.psv" | Measure-Object

# Expected: ~100+ PSV files
# Total size: ~15-20 GB uncompressed
```

**Important Files to Verify:**
- `*_ADDRESS_DETAIL_psv.psv` (all states)
- `*_ADDRESS_DEFAULT_GEOCODE_psv.psv` (all states)
- `*_LOCALITY_psv.psv` (all states)
- `*_STREET_LOCALITY_psv.psv` (all states)
- `STATE_psv.psv`
- Authority code files (FLAT_TYPE_AUT, STREET_TYPE_AUT, etc.)

---

## Database Configuration

### Step 1: Create PostgreSQL Database

**Connect to PostgreSQL:**

```powershell
# Windows (PowerShell)
$env:PGPASSWORD='your_admin_password'
psql -U postgres -h localhost
```

**Create Database:**

```sql
-- Create database
CREATE DATABASE gnaf_db
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

-- Connect to database
\c gnaf_db

-- Create schema
CREATE SCHEMA IF NOT EXISTS gnaf;

-- Grant permissions
GRANT ALL ON SCHEMA gnaf TO postgres;
```

### Step 2: Configure Database Parameters (Optional)

**For better performance, edit `postgresql.conf`:**

```ini
# Memory Settings
shared_buffers = 4GB                    # 25% of RAM
effective_cache_size = 12GB             # 75% of RAM
maintenance_work_mem = 2GB              # For index creation
work_mem = 256MB                        # For queries

# Checkpoint Settings
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100

# Query Planner
random_page_cost = 1.1                  # SSD optimization
effective_io_concurrency = 200          # SSD

# Connection Settings
max_connections = 100
```

**Restart PostgreSQL after changes:**

```powershell
# Windows
Restart-Service postgresql-x64-16

# Linux
sudo systemctl restart postgresql
```

---

## Application Setup

### Step 1: Clone/Download Application Code

**Option A: From Git Repository (if using version control)**

```powershell
cd C:\Users\kumar\Documents
git clone <repository_url> workspace
cd workspace
```

**Option B: Manual Setup**

Create the following directory structure:

```
workspace/
├── webapp/
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       ├── main.js
│   │       ├── search.js
│   │       ├── address.js
│   │       └── school.js
│   ├── templates/
│   │   ├── index.html
│   │   ├── search.html
│   │   ├── address_lookup.html
│   │   └── school_search.html
│   ├── app.py
│   ├── requirements.txt
│   ├── .env
│   ├── create_indexes.sql
│   └── create_stats_view.sql
├── load_psv_to_postgres.py
├── populate_suburbs.py
├── load_school_catchments.py
├── query_school_catchments.py
└── README.md
```

### Step 2: Create Python Virtual Environment

```powershell
cd C:\Users\kumar\Documents\workspace

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\Activate.ps1

# Linux/Mac:
source venv/bin/activate
```

### Step 3: Install Python Dependencies

**Create `requirements.txt`:**

```txt
Flask==3.1.2
flask-cors==5.0.0
psycopg2-binary==2.9.11
python-dotenv==1.2.1
pandas==3.0.0
numpy==2.4.1

# Optional: For school catchments
geopandas==1.1.2
sqlalchemy==2.0.46
geoalchemy2==0.18.1
```

**Install dependencies:**

```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

**Create `.env` file in `webapp/` directory:**

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gnaf_db
DB_USER=postgres
DB_PASSWORD=your_password_here

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True

# Optional: Production settings
# FLASK_ENV=production
# FLASK_DEBUG=False
```

**⚠️ Security Note:** Never commit `.env` file to version control!

### Step 5: Load GNAF Data into PostgreSQL

**Run the data loader:**

```powershell
# Navigate to workspace directory
cd C:\Users\kumar\Documents\workspace

# Run loader (this will take 30-60 minutes)
python load_psv_to_postgres.py "C:\data\downloads\g-naf_nov25_allstates_gda2020_psv_1021\G-NAF\G-NAF NOVEMBER 2025\Authority Code"
```

**Expected Output:**
```
Loading Authority Code tables...
✓ Loaded FLAT_TYPE_AUT: 32 records
✓ Loaded STREET_TYPE_AUT: 52 records
✓ Loaded GEOCODE_TYPE_AUT: 15 records
...
Loading Standard tables...
✓ Loaded NSW_ADDRESS_DETAIL: 5,234,567 records
✓ Loaded VIC_ADDRESS_DETAIL: 3,456,789 records
...
Total time: 45 minutes
```

### Step 6: Create Suburb-Postcode Mapping

```powershell
python populate_suburbs.py
```

**Expected Output:**
```
Creating suburb_postcode table...
✓ Inserted 25,000+ suburb-postcode mappings
```

### Step 7: Create Performance Indexes

```powershell
cd webapp
psql -U postgres -d gnaf_db -f create_indexes.sql
```

**Expected Duration:** 15-30 minutes  
**Index Size:** ~2.5 GB total

**Verify indexes:**

```sql
-- Check index creation
SELECT schemaname, tablename, indexname, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_indexes
JOIN pg_class ON pg_class.relname = indexname
WHERE schemaname = 'gnaf'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Step 8: Create Materialized Views

```powershell
psql -U postgres -d gnaf_db -f create_stats_view.sql
```

**Expected Output:**
```
Materialized views created successfully!
total_localities: 14,125
total_addresses: 15,234,567
total_streets: 523,456
```

### Step 9: Test Database Connection

**Create test script `test_connection.py`:**

```python
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv('webapp/.env')

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)

cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM gnaf.address_detail WHERE date_retired IS NULL")
count = cursor.fetchone()[0]
print(f"✓ Database connected successfully!")
print(f"  Total active addresses: {count:,}")
cursor.close()
conn.close()
```

```powershell
python test_connection.py
```

### Step 10: Start Flask Application

**Development Mode:**

```powershell
cd webapp
python app.py
```

**Expected Output:**
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
 * Running on http://192.168.1.104:5000
Press CTRL+C to quit
```

**Test the application:**

1. Open browser to `http://127.0.0.1:5000`
2. Verify home page loads with statistics and hero image
3. Test suburb search (should have hero image)
4. Test address lookup (should have hero image)
5. Test school catchment search (should have hero image, if enabled)
6. Verify Google Sans font is applied throughout
7. Test mobile responsiveness (resize browser to 768px, 480px)
8. Check property link buttons are vertically stacked with equal width

**Available Pages:**
- `http://127.0.0.1:5000/` - Home page with statistics
- `http://127.0.0.1:5000/search` - Suburb/postcode search
- `http://127.0.0.1:5000/address-lookup` - Address search
- `http://127.0.0.1:5000/school-search` - School catchment search (if enabled)
- `http://127.0.0.1:5000/school-rankings` - NSW school rankings article

---

## UI/UX Design Features

### Typography

**Google Sans Font:**
- Loaded via @import from Google Fonts CDN
- Applied globally to body and all major elements
- Professional corporate appearance
- Fallbacks: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif

**Momo Signature Font:**
- Used for Marcus Aurelius philosophical quote in school rankings article
- Adds elegant touch to article header
- Loaded via Google Fonts link tag

**Implementation:**
```css
/* In style.css */
@import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap');

body {
    font-family: 'Google Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
```

### Hero Images

**All pages feature hero images for visual appeal:**

- **Home Page:** Modern Australian cityscape (1200x300px)
- **Suburb Search:** Aerial suburban neighborhood view (1200x400px)
- **Address Lookup:** Street addresses perspective (1200x400px)
- **School Search:** School building exterior (1200x400px)

**Technical Implementation:**
- Source: Unsplash API for high-quality photos
- Dimensions: 1200x400px (1200x300px for home)
- Loading: `loading="lazy"` for performance
- Styling: `object-fit: cover` for proper scaling
- Responsive heights via media queries

**Example:**
```html
<div class="hero-image-container">
    <img src="https://images.unsplash.com/photo-[ID]?w=1200&h=400&fit=crop" 
         alt="Descriptive text" 
         class="hero-image" 
         loading="lazy">
</div>
```

### Mobile Responsiveness

**Breakpoints:**
- **Tablet:** ≤768px
- **Phone:** ≤480px

**Tablet Optimizations (≤768px):**
- Hero images: 250px height
- School header: flex-direction column
- Navigation: flex-wrap for better spacing
- Stat tiles: responsive grid

**Phone Optimizations (≤480px):**
- Hero images: 200px height
- Container padding: 15px (reduced from 20px)
- Buttons: 90% width, centered
- Tables: horizontal scroll with overflow-x
- School details: single-column grid
- Touch scrolling: -webkit-overflow-scrolling: touch

**CSS Media Queries:**
```css
/* Tablet */
@media (max-width: 768px) {
    .hero-image { height: 250px; }
    .school-header { flex-direction: column; }
}

/* Phone */
@media (max-width: 480px) {
    .hero-image { height: 200px; }
    .container { padding: 15px; }
    .result-table-container { overflow-x: auto; }
}
```

### Property Links Styling

**Vertical Equal-Width Buttons:**
- Layout: `display: flex; flex-direction: column`
- Spacing: `gap: 6px` between buttons
- Width: Equal width for both RealEstate and Domain buttons
- Colors: #c41230 (RealEstate), #16a34a (Domain)
- Hover effects: Slight darkening on hover

**Implementation (school.js and address.js):**
```javascript
propertyLinksDiv.style.cssText = `
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-top: 8px;
`;
```

### Professional Design Elements

**Corporate Theme:**
- Dark blue primary color: #1e3a8a
- Clean, minimalist design
- No emojis (removed for professional appearance)
- CSS vertical accent bars for h2 headings in articles

**School Rankings Article:**
- Professional layout with proper typography
- Marcus Aurelius quote in Momo signature font
- Verified school URLs (all NSW government school websites)
- Clean table formatting with proper spacing

---

## School Catchment Data Architecture

### School Information Data Flow

The application uses a **two-query approach** to retrieve complete school information:

**Query 1: School Metadata (from gnaf.school_catchments)**
- Purpose: Get school_type, school_name, school_id
- Source: `gnaf.school_catchments` materialized view
- Contains: Clean school_type data (e.g., "PRIMARY", "HIGH_BOYS")
- Note: Does NOT have priority or year level information

**Query 2: Year Level Information (from public.school_catchments_*)**
- Purpose: Get intake_year_level, latest_year_level
- Source: `public.school_catchments_primary`, `school_catchments_secondary`, `school_catchments_future`
- Contains: Detailed year level data
- Note: CATCH_TYPE values are inconsistent, NOT used for school_type

**Combined Result:**
- School Type: From gnaf.school_catchments
- School Name: From gnaf.school_catchments
- Year Levels: From public.school_catchments_*
- Priority: Set to None (not available in gnaf.school_catchments)

**Why This Approach?**
- `gnaf.school_catchments` has clean, reliable school_type data
- `public.school_catchments_*` tables have detailed year level information
- Combining both sources provides complete school details
- Priority field is deprecated (no longer used in UI)

### School Search UI

**Removed Features:**
- ❌ School Type dropdown filter (removed - not useful for users)
- ❌ JavaScript references to schoolType DOM element
- ❌ schoolType parameter in API calls

**Current Features:**
- ✅ School name autocomplete search
- ✅ Interactive catchment boundary maps
- ✅ Address listings with property links
- ✅ Distance calculations from school
- ✅ Detailed school information display
- ✅ Support for PRIMARY, SECONDARY, FUTURE, HIGH_GIRLS, HIGH_BOYS, HIGH_CO_ED types

---

## Optional: School Catchment Integration

**Only for NSW addresses - adds school catchment analysis**

### Step 1: Download School Catchment Data

**Source:** NSW Department of Education  
**Format:** ESRI Shapefile (.shp, .dbf, .prj, .shx)

Place shapefiles in: `workspace/nsw_school_catchments/`

Expected files:
- `catchments_primary.shp` (+ .dbf, .prj, .shx)
- `catchments_secondary.shp` (+ .dbf, .prj, .shx)
- `catchments_future.shp` (+ .dbf, .prj, .shx)

### Step 2: Install Spatial Libraries

```powershell
pip install geopandas sqlalchemy geoalchemy2
```

### Step 3: Load School Catchments

```powershell
python load_school_catchments.py
```

**Expected Output:**
```
✓ PostGIS extension enabled
✓ Loaded 1,661 records to school_catchments_primary
✓ Loaded 447 records to school_catchments_secondary
✓ Loaded 14 records to school_catchments_future
```

### Step 4: Test School Catchment Queries

```powershell
python query_school_catchments.py
```

**Expected Output:**
```
School Catchment Statistics:
- Primary schools: 1,661
- Secondary schools: 447
- Future schools: 14

School catchment for Sydney CBD:
- School: Fort St PS (PRIMARY)
```

### Step 5: Test School Search Web Interface

1. Restart Flask app (if not running with debug mode)
2. Open browser to `http://127.0.0.1:5000/school-search`
3. Test school autocomplete (type "Fort" - should show Fort St PS)
4. Select a school and verify:
   - School information displays (name, type, year levels, address count)
   - Catchment boundary appears on map
   - Address list loads (up to 500 addresses)
   - Distance from school calculated for each address
   - Filter works to search within results
   - Property links and Google Maps buttons functional

### Features Available After Integration:

✅ **School Autocomplete:** Search schools by name with type filter  
✅ **Catchment Visualization:** Interactive map showing catchment boundaries  
✅ **Address Listings:** All addresses within catchment (limit 500)  
✅ **Distance Calculation:** Distance from each address to school  
✅ **Client-side Filtering:** Real-time search within address results  
✅ **Full Address Features:** Property links, Google Maps, geocode info  
✅ **School Details:** Year levels (K-12), school type, total addresses

---

## Production Deployment

### Option 1: Windows Server Deployment

#### Step 1: Install Production WSGI Server

```powershell
pip install gunicorn waitress
```

#### Step 2: Create Startup Script

**`start_production.ps1`:**

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Set environment
$env:FLASK_ENV = "production"
$env:FLASK_DEBUG = "False"

# Start with Waitress (Windows-compatible)
cd webapp
waitress-serve --host=0.0.0.0 --port=5000 --threads=4 app:app
```

#### Step 3: Configure Windows Firewall

```powershell
# Allow inbound connections on port 5000
New-NetFirewallRule -DisplayName "Flask GNAF App" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 5000 `
    -Action Allow `
    -Profile Private,Domain
```

#### Step 4: Create Windows Service (Optional)

Use NSSM (Non-Sucking Service Manager):

```powershell
# Download NSSM
choco install nssm

# Install service
nssm install GNAFWebApp "C:\Users\kumar\Documents\workspace\venv\Scripts\waitress-serve.exe"
nssm set GNAFWebApp AppParameters "--host=0.0.0.0 --port=5000 --threads=4 app:app"
nssm set GNAFWebApp AppDirectory "C:\Users\kumar\Documents\workspace\webapp"

# Start service
nssm start GNAFWebApp
```

### Option 2: Linux Server Deployment

#### Step 1: Install Gunicorn

```bash
pip install gunicorn
```

#### Step 2: Create Systemd Service

**`/etc/systemd/system/gnaf-webapp.service`:**

```ini
[Unit]
Description=GNAF Web Application
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/gnaf/webapp
Environment="PATH=/var/www/gnaf/venv/bin"
EnvironmentFile=/var/www/gnaf/webapp/.env
ExecStart=/var/www/gnaf/venv/bin/gunicorn --workers 4 --bind 0.0.0.0:5000 app:app

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable gnaf-webapp
sudo systemctl start gnaf-webapp
sudo systemctl status gnaf-webapp
```

#### Step 3: Configure NGINX Reverse Proxy

**`/etc/nginx/sites-available/gnaf`:**

```nginx
server {
    listen 80;
    server_name gnaf.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/gnaf/webapp/static;
        expires 30d;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/gnaf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### Step 4: SSL Certificate (Optional)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d gnaf.yourdomain.com
```

### Option 3: Docker Deployment (Advanced)

**`Dockerfile`:**

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install PostgreSQL client
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY webapp/ ./webapp/

WORKDIR /app/webapp

# Run with Gunicorn
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "app:app"]
```

**`docker-compose.yml`:**

```yaml
version: '3.8'

services:
  db:
    image: postgis/postgis:16-3.4
    environment:
      POSTGRES_DB: gnaf_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      DB_HOST: db
      DB_PORT: 5432
      DB_NAME: gnaf_db
      DB_USER: postgres
      DB_PASSWORD: ${DB_PASSWORD}
    depends_on:
      - db

volumes:
  postgres_data:
```

---

## AWS Cloud Deployment

For production deployment on AWS with high availability, auto-scaling, and comprehensive monitoring, see the dedicated **[AWS_ARCHITECTURE.md](AWS_ARCHITECTURE.md)** guide.

The AWS architecture includes:
- Multi-AZ deployment with Application Load Balancer
- RDS PostgreSQL with PostGIS (Multi-AZ, 500GB GP3)
- EC2/ECS Auto Scaling (2-10 instances)
- CloudFront CDN for global distribution
- ElastiCache Redis for API caching
- Complete security, monitoring, and disaster recovery setup
- Cost estimation (~$1,570/month, optimized to ~$1,220/month)

---

## Maintenance & Operations

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Internet Users                              │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Route 53 (DNS)                                    │
│  gnaf.yourdomain.com → CloudFront Distribution                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CloudFront CDN                                    │
│  - Global edge locations                                            │
│  - HTTPS/SSL termination (ACM certificate)                          │
│  - Cache static assets (CSS, JS, images)                            │
│  - DDoS protection (AWS Shield Standard)                            │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                Application Load Balancer (ALB)                       │
│  - HTTPS listener (port 443)                                        │
│  - Health checks (/api/stats)                                       │
│  - SSL/TLS certificate (ACM)                                        │
│  - Cross-zone load balancing                                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  EC2/ECS      │    │  EC2/ECS      │    │  EC2/ECS      │
│  Flask App    │    │  Flask App    │    │  Flask App    │
│  AZ-1a        │    │  AZ-1b        │    │  AZ-1c        │
│  (Gunicorn)   │    │  (Gunicorn)   │    │  (Gunicorn)   │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │                    │                    │
        └────────────────────┼────────────────────┘
                             │
                             ▼
        ┌────────────────────────────────────────────┐
        │          VPC (10.0.0.0/16)                 │
        │                                            │
        │  ┌──────────────────────────────────────┐ │
        │  │   Public Subnets                     │ │
        │  │   - 10.0.1.0/24 (AZ-1a)              │ │
        │  │   - 10.0.2.0/24 (AZ-1b)              │ │
        │  │   - 10.0.3.0/24 (AZ-1c)              │ │
        │  │   (ALB, NAT Gateways)                │ │
        │  └──────────────────────────────────────┘ │
        │                                            │
        │  ┌──────────────────────────────────────┐ │
        │  │   Private Subnets (App)              │ │
        │  │   - 10.0.11.0/24 (AZ-1a)             │ │
        │  │   - 10.0.12.0/24 (AZ-1b)             │ │
        │  │   - 10.0.13.0/24 (AZ-1c)             │ │
        │  │   (EC2/ECS instances)                │ │
        │  └──────────────────────────────────────┘ │
        │                                            │
        │  ┌──────────────────────────────────────┐ │
        │  │   Private Subnets (Database)         │ │
        │  │   - 10.0.21.0/24 (AZ-1a)             │ │
        │  │   - 10.0.22.0/24 (AZ-1b)             │ │
        │  │   - 10.0.23.0/24 (AZ-1c)             │ │
        │  │   (RDS PostgreSQL)                   │ │
        │  └──────────┬───────────────────────────┘ │
        └─────────────┼──────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────────────────┐
        │   RDS PostgreSQL with PostGIS           │
        │   - Primary: AZ-1a (db.r6g.2xlarge)     │
        │   - Standby: AZ-1b (Multi-AZ)           │
        │   - Storage: 500GB GP3 SSD (10,000 IOPS)│
        │   - Automated backups (7-day retention) │
        │   - Read replicas (optional)            │
        └─────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      Supporting Services                             │
├─────────────────────────────────────────────────────────────────────┤
│  S3 Buckets:                                                         │
│  - gnaf-backups (database backups, lifecycle to Glacier)            │
│  - gnaf-static-assets (optional: hero images, fonts)                │
│  - gnaf-logs (ALB/CloudFront access logs)                           │
│                                                                      │
│  ElastiCache Redis (optional):                                      │
│  - cache.r6g.large (for API response caching)                       │
│  - Multi-AZ with automatic failover                                 │
│                                                                      │
│  Secrets Manager:                                                    │
│  - Database credentials                                             │
│  - API keys                                                          │
│                                                                      │
│  CloudWatch:                                                         │
│  - Application logs (from EC2/ECS)                                  │
│  - Database metrics (RDS)                                           │
│  - ALB metrics                                                       │
│  - Custom metrics (API latency)                                     │
│  - Alarms (CPU, memory, errors)                                     │
│                                                                      │
│  Auto Scaling:                                                       │
│  - Target tracking: CPU 70%                                         │
│  - Min instances: 2                                                  │
│  - Max instances: 10                                                 │
│  - Scale-out: +2 instances when CPU >70% for 5 min                 │
│  - Scale-in: -1 instance when CPU <30% for 10 min                  │
└─────────────────────────────────────────────────────────────────────┘
```

### AWS Service Selection

#### Compute Layer

**Option 1: EC2 Auto Scaling Group (Recommended for flexibility)**

**Instance Type:** t3.large or t3.xlarge (2-4 vCPU, 8-16 GB RAM)

**Pros:**
- Full control over instance configuration
- Easy to debug and troubleshoot
- Direct SSH access
- Simple deployment process

**Cons:**
- Manual OS patching required
- More operational overhead

**Setup:**
```bash
# User Data script for EC2 launch
#!/bin/bash
yum update -y
yum install -y python3.13 git postgresql15

# Clone application
cd /opt
git clone <repo_url> gnaf-app
cd gnaf-app

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start application with systemd
cp gnaf-webapp.service /etc/systemd/system/
systemctl enable gnaf-webapp
systemctl start gnaf-webapp
```

**Option 2: ECS Fargate (Recommended for containerization)**

**Task Definition:**
- CPU: 2048 (2 vCPU)
- Memory: 4096 MB (4 GB)
- Container: Flask app with Gunicorn

**Pros:**
- Serverless container management
- Automatic scaling
- No EC2 instance management
- Rolling deployments

**Cons:**
- Slightly higher cost per vCPU
- Less flexibility for debugging

**Option 3: Elastic Beanstalk (Easiest deployment)**

**Environment:** Python 3.13 platform

**Pros:**
- Simplest deployment (just upload zip)
- Automatic load balancing
- Built-in monitoring
- Managed updates

**Cons:**
- Less control over infrastructure
- May incur additional costs

#### Database Layer

**RDS PostgreSQL with PostGIS**

**Configuration:**
- **Engine:** PostgreSQL 16.x
- **Instance Class:** db.r6g.2xlarge (8 vCPU, 64 GB RAM)
  - Dev/Test: db.t3.large (2 vCPU, 8 GB RAM)
- **Storage:** 500 GB GP3 SSD
  - IOPS: 10,000 (provisioned)
  - Throughput: 500 MB/s
- **Multi-AZ:** Enabled (for high availability)
- **Read Replicas:** 1-2 (for read-heavy workloads)
- **Backup:**
  - Automated daily backups (7-day retention)
  - Manual snapshots before major updates
  - Backup window: 02:00-03:00 UTC
- **Maintenance Window:** Sunday 03:00-04:00 UTC

**PostGIS Extension:**
```sql
-- Run after RDS creation
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
```

**Parameter Group Settings:**
```ini
shared_buffers = 16GB                   # 25% of 64GB RAM
effective_cache_size = 48GB             # 75% of 64GB RAM
maintenance_work_mem = 2GB
work_mem = 256MB
max_connections = 200
```

#### Content Delivery

**CloudFront Distribution**

**Cache Behaviors:**
- `/static/*` → Cache everything (TTL: 7 days)
- `/api/*` → No caching (pass through to ALB)
- `/` → Cache HTML (TTL: 1 hour)

**Origin Settings:**
- Primary: ALB (custom origin)
- Backup: S3 bucket (for maintenance page)

**SSL Certificate:**
- ACM certificate for `gnaf.yourdomain.com`
- Minimum TLS version: 1.2

**WAF (Optional):**
- AWS WAF rules for DDoS protection
- Rate limiting: 2000 requests/5 min per IP
- Geo-blocking (if needed)

#### Storage

**S3 Buckets**

1. **gnaf-backups:**
   - Purpose: Database backups, GNAF data archive
   - Lifecycle: Move to Glacier after 30 days
   - Versioning: Enabled
   - Encryption: AES-256 (SSE-S3)

2. **gnaf-static-assets (optional):**
   - Purpose: Host hero images locally instead of Unsplash
   - CloudFront origin for static assets
   - Public read access

3. **gnaf-logs:**
   - Purpose: ALB, CloudFront access logs
   - Lifecycle: Delete after 90 days
   - Compression: Enabled

#### Caching (Optional)

**ElastiCache Redis**

**Configuration:**
- **Node Type:** cache.r6g.large (2 vCPU, 13 GB RAM)
- **Cluster Mode:** Disabled (for simplicity)
- **Multi-AZ:** Enabled
- **Replicas:** 1 read replica

**Use Cases:**
- Cache API responses (suburb lists, stats)
- Session storage (if adding user accounts)
- Rate limiting counters

**Flask Integration:**
```python
import redis
from functools import wraps

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST'),
    port=6379,
    decode_responses=True
)

def cache_response(ttl=300):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            cache_key = f"{f.__name__}:{str(args)}:{str(kwargs)}"
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            result = f(*args, **kwargs)
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

@app.route('/api/stats')
@cache_response(ttl=3600)  # Cache for 1 hour
def get_stats():
    # ... database query ...
```

### Network Architecture

**VPC Configuration:**

**CIDR Block:** 10.0.0.0/16

**Subnets:**

| Tier | AZ | CIDR | Purpose |
|------|-----|------|---------|
| Public | us-east-1a | 10.0.1.0/24 | ALB, NAT Gateway |
| Public | us-east-1b | 10.0.2.0/24 | ALB, NAT Gateway |
| Public | us-east-1c | 10.0.3.0/24 | ALB, NAT Gateway |
| Private (App) | us-east-1a | 10.0.11.0/24 | EC2/ECS |
| Private (App) | us-east-1b | 10.0.12.0/24 | EC2/ECS |
| Private (App) | us-east-1c | 10.0.13.0/24 | EC2/ECS |
| Private (DB) | us-east-1a | 10.0.21.0/24 | RDS Primary |
| Private (DB) | us-east-1b | 10.0.22.0/24 | RDS Standby |
| Private (DB) | us-east-1c | 10.0.23.0/24 | RDS Read Replica |

**Route Tables:**

- **Public:** Routes to Internet Gateway
- **Private:** Routes to NAT Gateway (for outbound internet)
- **Database:** No internet access (isolated)

**NAT Gateways:**
- One per AZ for high availability
- Elastic IP for each NAT Gateway

### Security Configuration

**Security Groups:**

**1. ALB Security Group (sg-alb)**
- Inbound: 443 (HTTPS) from 0.0.0.0/0
- Inbound: 80 (HTTP) from 0.0.0.0/0 (redirect to 443)
- Outbound: All traffic to App SG

**2. Application Security Group (sg-app)**
- Inbound: 5000 from ALB SG
- Outbound: 5432 to DB SG
- Outbound: 443 to 0.0.0.0/0 (for API calls)
- Outbound: 6379 to Redis SG (if using ElastiCache)

**3. Database Security Group (sg-db)**
- Inbound: 5432 from App SG only
- Outbound: None

**4. Redis Security Group (sg-redis)**
- Inbound: 6379 from App SG only
- Outbound: None

**IAM Roles:**

**EC2/ECS Task Role:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::gnaf-backups/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:gnaf/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/gnaf/*"
    }
  ]
}
```

**Secrets Manager:**

Store sensitive credentials:
```json
{
  "DB_HOST": "gnaf-db.xxxxx.us-east-1.rds.amazonaws.com",
  "DB_PORT": "5432",
  "DB_NAME": "gnaf_db",
  "DB_USER": "gnaf_admin",
  "DB_PASSWORD": "SecureRandomPassword123!",
  "REDIS_HOST": "gnaf-redis.xxxxx.cache.amazonaws.com"
}
```

### Auto Scaling Configuration

**EC2 Auto Scaling Group:**

**Launch Template:**
- AMI: Amazon Linux 2023
- Instance Type: t3.large
- IAM Role: EC2-GNAF-Role
- Security Groups: sg-app
- User Data: Install and start Flask app

**Scaling Policies:**

**Target Tracking:**
- Metric: Average CPU Utilization
- Target: 70%
- Cooldown: 300 seconds

**Step Scaling (optional):**
```
CPU > 80% for 5 min → Add 2 instances
CPU > 90% for 5 min → Add 4 instances
CPU < 30% for 10 min → Remove 1 instance
```

**Scheduled Scaling (optional):**
```
# Business hours (9 AM - 6 PM AEST)
Min: 4 instances
Max: 10 instances

# Off-hours
Min: 2 instances
Max: 6 instances
```

**ECS Auto Scaling:**

**Service Auto Scaling:**
- Target: 70% CPU
- Min tasks: 2
- Max tasks: 10
- Scale-out cooldown: 60 seconds
- Scale-in cooldown: 300 seconds

### Monitoring & Alerting

**CloudWatch Alarms:**

| Alarm | Metric | Threshold | Action |
|-------|--------|-----------|--------|
| High CPU | EC2/ECS CPU | >80% for 5 min | SNS notification |
| High Memory | Memory Utilization | >85% for 5 min | SNS notification |
| DB Connections | RDS Connections | >180 | SNS notification |
| DB CPU | RDS CPU | >75% for 10 min | SNS notification |
| 5xx Errors | ALB 5xx count | >50/5 min | SNS notification + scale out |
| Slow Queries | API Latency | >3s (p95) | SNS notification |

**CloudWatch Dashboards:**

Create dashboard with:
- ALB request count, latency, error rates
- EC2/ECS CPU, memory, network
- RDS CPU, connections, read/write IOPS
- Application logs (errors, warnings)

**X-Ray (Optional):**
- Distributed tracing for API calls
- Identify slow database queries
- Performance bottleneck analysis

### Deployment Process

**Step 1: Infrastructure Setup (Terraform/CloudFormation)**

**Using Terraform:**

```hcl
# main.tf
provider "aws" {
  region = "us-east-1"
}

# VPC
module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  
  name = "gnaf-vpc"
  cidr = "10.0.0.0/16"
  
  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  public_subnets  = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnets = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
  database_subnets = ["10.0.21.0/24", "10.0.22.0/24", "10.0.23.0/24"]
  
  enable_nat_gateway = true
  enable_dns_hostnames = true
}

# RDS PostgreSQL
module "rds" {
  source = "terraform-aws-modules/rds/aws"
  
  identifier = "gnaf-db"
  engine = "postgres"
  engine_version = "16.1"
  instance_class = "db.r6g.2xlarge"
  allocated_storage = 500
  storage_type = "gp3"
  iops = 10000
  
  db_name  = "gnaf_db"
  username = "postgres"
  password = random_password.db_password.result
  
  multi_az = true
  vpc_security_group_ids = [aws_security_group.db.id]
  db_subnet_group_name = module.vpc.database_subnet_group_name
  
  backup_retention_period = 7
  backup_window = "02:00-03:00"
  maintenance_window = "sun:03:00-sun:04:00"
  
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  
  tags = {
    Environment = "production"
    Application = "GNAF"
  }
}
```

**Step 2: Database Initialization**

```bash
# Connect to RDS instance
psql -h gnaf-db.xxxxx.us-east-1.rds.amazonaws.com \
     -U postgres \
     -d gnaf_db

# Create schema and extensions
CREATE SCHEMA IF NOT EXISTS gnaf;
CREATE EXTENSION IF NOT EXISTS postgis;

# Load GNAF data (from EC2 bastion host)
python3 load_psv_to_postgres.py /data/gnaf/
```

**Step 3: Application Deployment**

**Option A: EC2 with CodeDeploy**

```yaml
# appspec.yml
version: 0.0
os: linux
files:
  - source: /
    destination: /opt/gnaf-app
hooks:
  ApplicationStop:
    - location: scripts/stop_app.sh
      timeout: 300
  ApplicationStart:
    - location: scripts/start_app.sh
      timeout: 300
  ValidateService:
    - location: scripts/validate.sh
      timeout: 300
```

**Option B: ECS with Blue/Green Deployment**

```json
{
  "family": "gnaf-app",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "containerDefinitions": [
    {
      "name": "gnaf-flask",
      "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/gnaf:latest",
      "portMappings": [
        {
          "containerPort": 5000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "FLASK_ENV", "value": "production"}
      ],
      "secrets": [
        {
          "name": "DB_HOST",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789:secret:gnaf/db:DB_HOST::"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/aws/ecs/gnaf",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "flask"
        }
      }
    }
  ]
}
```

**Step 4: DNS Configuration**

```bash
# Route 53 hosted zone
aws route53 create-hosted-zone --name yourdomain.com

# Create A record pointing to CloudFront
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "gnaf.yourdomain.com",
      "Type": "A",
      "AliasTarget": {
        "HostedZoneId": "Z2FDTNDATAQYW2",
        "DNSName": "d123456.cloudfront.net",
        "EvaluateTargetHealth": false
      }
    }
  }]
}
```

### Cost Estimation

**Monthly Cost Breakdown (Production):**

| Service | Configuration | Monthly Cost (USD) |
|---------|---------------|-------------------|
| **RDS PostgreSQL** | db.r6g.2xlarge Multi-AZ, 500GB GP3 | $850 |
| **EC2 Auto Scaling** | 3x t3.large (avg), Reserved | $160 |
| **ALB** | Standard, 1M requests | $25 |
| **CloudFront** | 1TB data transfer, 10M requests | $85 |
| **S3** | 100GB storage, 1TB transfer | $25 |
| **ElastiCache Redis** | cache.r6g.large Multi-AZ | $200 |
| **NAT Gateway** | 3x NAT, 1TB data | $135 |
| **CloudWatch** | Logs, metrics, alarms | $30 |
| **Route 53** | Hosted zone, queries | $10 |
| **Data Transfer** | Inter-AZ, out to internet | $50 |
| **Total** | | **~$1,570/month** |

**Cost Optimization Tips:**

1. **Use Reserved Instances:**
   - RDS: 1-year Reserved → Save 40%
   - EC2: 1-year Reserved → Save 35%
   - Total savings: ~$350/month

2. **Right-sizing:**
   - Start with smaller instances (t3.medium)
   - Scale up based on actual usage
   - Use RDS Performance Insights to optimize

3. **S3 Lifecycle:**
   - Move backups to Glacier after 30 days
   - Save ~70% on backup storage

4. **CloudFront Optimization:**
   - Cache more aggressively
   - Reduce origin requests
   - Consider CloudFront Savings Bundle

5. **Dev/Test Environment:**
   - Use smaller instance types
   - Single-AZ RDS
   - Stop instances during off-hours
   - Cost: ~$300/month

### High Availability & Disaster Recovery

**RTO (Recovery Time Objective):** 15 minutes  
**RPO (Recovery Point Objective):** 5 minutes

**HA Strategy:**

1. **Multi-AZ Deployment:**
   - Application: 3 AZs (us-east-1a, 1b, 1c)
   - Database: Multi-AZ automatic failover
   - ALB: Cross-zone load balancing

2. **Auto-healing:**
   - ALB health checks every 30 seconds
   - Auto Scaling replaces unhealthy instances
   - RDS automatic failover (60-120 seconds)

3. **Data Backup:**
   - RDS automated daily backups
   - Point-in-time recovery (5-minute granularity)
   - Manual snapshots before deployments
   - S3 backup replication to another region

**Disaster Recovery:**

**Scenario 1: AZ Failure**
- Auto: Traffic routes to healthy AZs
- Impact: None (handled automatically)

**Scenario 2: Region Failure**
- Manual: Restore RDS snapshot in another region
- Manual: Deploy application stack via Terraform
- Impact: 2-4 hours downtime
- Cost: Active-passive DR adds ~30% to costs

**Scenario 3: Data Corruption**
- Manual: Point-in-time restore from RDS backup
- Impact: Up to 5 minutes of data loss
- Time: 30-60 minutes

### Performance Optimization

**Database Optimization:**

1. **Connection Pooling:**
```python
from psycopg2 import pool

db_pool = pool.ThreadedConnectionPool(
    minconn=5,
    maxconn=20,
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD')
)
```

2. **Read Replicas:**
- Route read queries to RDS read replica
- Use Route 53 weighted routing
- Reduce load on primary database

3. **Query Optimization:**
- Enable pg_stat_statements extension
- Monitor slow queries in CloudWatch
- Add missing indexes identified by query plans

**Application Optimization:**

1. **Static Asset Delivery:**
- Serve CSS/JS/images from CloudFront
- Enable Gzip compression
- Set far-future cache headers

2. **API Response Caching:**
- Cache frequently accessed data in Redis
- Cache stats API response (1-hour TTL)
- Cache suburb/postcode lists (1-day TTL)

3. **Async Operations:**
- Use Celery + SQS for background tasks
- Offload heavy computations
- Generate reports asynchronously

### Security Best Practices

**1. Network Security:**
- Private subnets for app and database
- No public IP addresses on app/DB instances
- NAT Gateway for outbound internet only
- VPC Flow Logs enabled

**2. Data Encryption:**
- RDS encryption at rest (KMS)
- EBS volumes encrypted
- S3 bucket encryption
- ALB HTTPS/TLS 1.2+

**3. Access Control:**
- SSM Session Manager (no SSH keys)
- IAM roles for EC2/ECS (no hardcoded credentials)
- Secrets Manager for database passwords
- MFA for AWS Console access

**4. Compliance:**
- Enable AWS Config for compliance checks
- CloudTrail for API audit logs
- GuardDuty for threat detection
- Security Hub for consolidated view

**5. Application Security:**
- WAF rate limiting
- Input validation
- SQL injection prevention (parameterized queries)
- CORS restrictions
- Security headers (CSP, HSTS, X-Frame-Options)

```python
# Flask security headers
from flask import Flask, make_response

@app.after_request
def add_security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' https://images.unsplash.com; font-src 'self' https://fonts.googleapis.com https://fonts.gstatic.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; script-src 'self' 'unsafe-inline';"
    return response
```

### Maintenance Runbook

**Monthly Tasks:**
- Review CloudWatch alarms and metrics
- Check RDS storage utilization
- Review CloudWatch Logs Insights for errors
- Update security patches (OS, Python packages)
- Review AWS Cost Explorer for anomalies

**Quarterly Tasks:**
- RDS performance tuning (query optimization)
- Review Auto Scaling policies
- Update SSL certificates (if not using ACM)
- Disaster recovery drill (restore from backup)
- Review IAM permissions (least privilege)

**Annual Tasks:**
- Renew Reserved Instances
- Update GNAF dataset (new release)
- Review and update architecture
- Security audit and penetration testing

---

## Maintenance & Operations

### Refreshing Materialized Views

**Frequency:** Weekly or monthly

```sql
-- Refresh statistics (run during low-traffic periods)
REFRESH MATERIALIZED VIEW gnaf.stats_summary;
REFRESH MATERIALIZED VIEW gnaf.stats_by_state;

-- Or concurrent refresh (doesn't lock table)
REFRESH MATERIALIZED VIEW CONCURRENTLY gnaf.stats_summary;
REFRESH MATERIALIZED VIEW CONCURRENTLY gnaf.stats_by_state;
```

**Automated Script:**

```powershell
# refresh_stats.ps1
$env:PGPASSWORD='your_password'
psql -U postgres -d gnaf_db -c "REFRESH MATERIALIZED VIEW gnaf.stats_summary;"
psql -U postgres -d gnaf_db -c "REFRESH MATERIALIZED VIEW gnaf.stats_by_state;"
```

**Schedule with Task Scheduler (Windows):**

```powershell
$action = New-ScheduledTaskAction -Execute 'PowerShell.exe' -Argument '-File C:\path\to\refresh_stats.ps1'
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 2am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "GNAF Stats Refresh"
```

### Database Backup

**Daily backup script:**

```powershell
# backup_gnaf.ps1
$date = Get-Date -Format "yyyyMMdd"
$backupFile = "C:\backups\gnaf_db_$date.backup"

pg_dump -U postgres -d gnaf_db -F c -b -v -f $backupFile
```

### Monitoring

**Check application health:**

```powershell
# Test API endpoint
Invoke-RestMethod -Uri "http://localhost:5000/api/stats"
```

**Monitor database performance:**

```sql
-- Check slow queries
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active' AND now() - pg_stat_activity.query_start > interval '5 seconds'
ORDER BY duration DESC;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE schemaname = 'gnaf'
ORDER BY idx_scan ASC;
```

### Updating GNAF Data

**When new GNAF release is available:**

1. Download new GNAF data
2. Backup current database
3. Truncate tables
4. Run `load_psv_to_postgres.py` with new data
5. Rebuild indexes: `psql -f create_indexes.sql`
6. Refresh materialized views
7. Test application

---

## Troubleshooting

### Issue: Database Connection Failed

**Symptoms:** Application can't connect to PostgreSQL

**Solutions:**

1. **Check PostgreSQL is running:**
   ```powershell
   Get-Service postgresql*
   ```

2. **Verify credentials in `.env` file**

3. **Check pg_hba.conf** (PostgreSQL authentication):
   ```
   # Add this line to allow local connections
   host    all             all             127.0.0.1/32            md5
   ```

4. **Restart PostgreSQL:**
   ```powershell
   Restart-Service postgresql-x64-16
   ```

### Issue: Slow Query Performance

**Symptoms:** Searches take >5 seconds

**Solutions:**

1. **Verify indexes are created:**
   ```sql
   SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'gnaf';
   -- Should return 17+
   ```

2. **Run ANALYZE:**
   ```sql
   ANALYZE gnaf.address_detail;
   ANALYZE gnaf.street_locality;
   ```

3. **Check query plan:**
   ```sql
   EXPLAIN ANALYZE
   SELECT * FROM gnaf.address_detail WHERE ...
   ```

### Issue: Port 5000 Already in Use

**Symptoms:** Flask won't start due to port conflict

**Solutions:**

1. **Find process using port 5000:**
   ```powershell
   Get-NetTCPConnection -LocalPort 5000
   ```

2. **Kill the process:**
   ```powershell
   Stop-Process -Id [PID]
   ```

3. **Or use a different port:**
   ```python
   # In app.py
   app.run(host='0.0.0.0', port=8080)
   ```

### Issue: Hero Images Not Loading

**Symptoms:** Blank spaces where hero images should appear

**Solutions:**

1. **Check internet connection** (images load from Unsplash CDN)

2. **Verify image URLs in HTML files:**
   - index.html: photo-1514565131-fce0801e5785 (cityscape)
   - search.html: photo-1560518883-ce09059eeffa (suburban aerial)
   - address_lookup.html: photo-1582407947304-fd86f028f716 (street view)
   - school_search.html: photo-1509062522246-3755977927d7 (school building)

3. **Check browser console for 404 errors:**
   - Press F12 → Console tab
   - Look for Unsplash API errors

4. **Test image URL directly:**
   ```
   https://images.unsplash.com/photo-1514565131-fce0801e5785?w=1200&h=300&fit=crop
   ```

### Issue: Google Sans Font Not Applied

**Symptoms:** Application shows system fonts instead of Google Sans

**Solutions:**

1. **Check internet connection** (font loads from Google Fonts CDN)

2. **Verify @import in style.css:**
   ```css
   @import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;700&display=swap');
   ```

3. **Check browser DevTools:**
   - F12 → Network tab
   - Filter by "font"
   - Verify Google Sans loads successfully

4. **Clear browser cache:**
   ```
   Ctrl+Shift+Delete → Clear cached files
   ```

### Issue: Mobile Layout Not Responsive

**Symptoms:** Desktop layout shows on mobile devices

**Solutions:**

1. **Check viewport meta tag in HTML:**
   ```html
   <meta name="viewport" content="width=device-width, initial-scale=1.0">
   ```

2. **Test with browser DevTools:**
   - F12 → Toggle device toolbar (Ctrl+Shift+M)
   - Test at 768px (tablet) and 480px (phone)

3. **Verify media queries in style.css:**
   ```css
   @media (max-width: 768px) { /* tablet */ }
   @media (max-width: 480px) { /* phone */ }
   ```

4. **Check hero image heights:**
   - Desktop: 300-400px
   - Tablet (≤768px): 250px
   - Phone (≤480px): 200px

**Symptoms:** Flask won't start - "Address already in use"

**Solutions:**

1. **Find process using port:**
   ```powershell
   Get-NetTCPConnection -LocalPort 5000
   ```

2. **Kill process or change port:**
   ```python
   # In app.py
   app.run(host='0.0.0.0', port=5001, debug=True)
   ```

### Issue: Missing Dependencies

**Symptoms:** ImportError when running Python scripts

**Solutions:**

```powershell
# Reinstall all dependencies
pip install --force-reinstall -r requirements.txt
```

### Issue: Firewall Blocking Connections

**Symptoms:** Can't access from other computers

**Solutions:**

```powershell
# Check firewall rules
Get-NetFirewallRule -DisplayName "*Flask*"

# Create new rule
New-NetFirewallRule -DisplayName "Flask GNAF" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
```

### Issue: School Search Not Working

**Symptoms:** School search page returns errors or no results

**Solutions:**

1. **Verify PostGIS extension is enabled:**
   ```sql
   SELECT PostGIS_Version();
   -- Should return version number
   ```

2. **Check school catchment tables exist:**
   ```sql
   SELECT COUNT(*) FROM public.school_catchments_primary;
   SELECT COUNT(*) FROM public.school_catchments_secondary;
   SELECT COUNT(*) FROM public.school_catchments_future;
   -- Should return: 1,661, 447, 14
   ```

3. **Verify spatial indexes:**
   ```sql
   SELECT tablename, indexname 
   FROM pg_indexes 
   WHERE schemaname = 'public' 
   AND tablename LIKE 'school_catchments%';
   -- Should show GIST indexes on geometry columns
   ```

4. **Test API endpoint directly:**
   ```powershell
   Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/autocomplete/schools?q=Fort&type="
   # Should return Fort St PS and other matching schools
   ```

5. **Check browser console for JavaScript errors:**
   - Press F12 in browser
   - Look for errors in Console tab
   - Verify Leaflet.js loads from CDN

---

## Appendix

### A. Quick Reference - Ports

| Service | Port | Purpose |
|---------|------|---------|
| PostgreSQL | 5432 | Database server |
| Flask (Dev) | 5000 | Web application |
| NGINX | 80 | HTTP reverse proxy |
| NGINX SSL | 443 | HTTPS reverse proxy |

### B. Quick Reference - File Locations

| Component | Location |
|-----------|----------|
| Application | `C:\Users\kumar\Documents\workspace\webapp\` |
| School Catchments | `C:\Users\kumar\Documents\workspace\nsw_school_catchments\` |
| Database | PostgreSQL data directory (varies by installation) |
| Logs | `C:\Users\kumar\Documents\workspace\logs\` |
| Backups | `C:\backups\` |
| GNAF Data | `C:\data\downloads\` |

### C. Quick Reference - Commands

| Task | Command |
|------|---------|
| Start Flask (Dev) | `python app.py` |
| Start Flask (Prod) | `waitress-serve --host=0.0.0.0 --port=5000 app:app` |
| Connect to DB | `psql -U postgres -d gnaf_db` |
| Backup DB | `pg_dump -U postgres -d gnaf_db -F c -f backup.backup` |
| Restore DB | `pg_restore -U postgres -d gnaf_db backup.backup` |
| Refresh Stats | `psql -c "REFRESH MATERIALIZED VIEW gnaf.stats_summary;"` |
| Load School Catchments | `python load_school_catchments.py` |
| Test School Queries | `python query_school_catchments.py` |

### D. Quick Reference - API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stats` | GET | Database statistics |
| `/api/search/suburbs` | GET | Suburb search |
| `/api/search/postcodes` | GET | Postcode search |
| `/api/address/search` | GET | Address lookup |
| `/api/autocomplete/suburbs` | GET | Suburb autocomplete |
| `/api/autocomplete/streets` | GET | Street autocomplete |
| `/api/autocomplete/schools` | GET | School autocomplete |
| `/api/suburbs/by-state` | GET | Suburbs by state |
| `/api/school/<id>/info` | GET | School details |
| `/api/school/<id>/addresses` | GET | Catchment addresses |
| `/api/school/<id>/boundary` | GET | Catchment GeoJSON |

---

## Support & Documentation

### Additional Resources

- **GNAF Documentation:** https://data.gov.au/dataset/ds-dga-19432f89-dc3a-4ef3-b943-5326ef1dbecc
- **Flask Documentation:** https://flask.palletsprojects.com/
- **PostgreSQL Documentation:** https://www.postgresql.org/docs/
- **PostGIS Documentation:** https://postgis.net/documentation/
- **Leaflet.js Documentation:** https://leafletjs.com/reference.html

### Application Documentation

- `README.md` - Application overview
- `TEST_REPORT.md` - Comprehensive test results
- `SCHOOL_CATCHMENT_GUIDE.md` - School catchment integration guide
- `DEPLOYMENT_GUIDE.md` - This deployment guide

### Key Features Summary

**Core Features:**
- ✅ Suburb and postcode search
- ✅ Address lookup with geocoded coordinates
- ✅ Autocomplete for suburbs and streets
- ✅ Property links to RealEstate.com.au and Domain.com.au (vertical equal-width buttons)
- ✅ Google Maps integration with pin drop
- ✅ Distance calculations from state CBDs
- ✅ State filter for targeted searches
- ✅ Performance-optimized queries (<2s)
- ✅ Hero images on all pages (Unsplash 1200x400px)
- ✅ Google Sans professional typography
- ✅ Fully responsive mobile design (768px tablet, 480px phone breakpoints)

**School Catchment Features (Optional):**
- ✅ School search with autocomplete
- ✅ Interactive catchment boundary maps
- ✅ Address listings within catchments
- ✅ Distance from school calculations
- ✅ Real-time address filtering
- ✅ Support for primary, secondary, and future schools
- ✅ Support for selective schools (HIGH_GIRLS, HIGH_BOYS, HIGH_CO_ED)
- ✅ Full address features (property links, maps, geocodes)
- ✅ Two-query architecture (gnaf.school_catchments + public.school_catchments_*)

**Design & UX Features:**
- ✅ Professional corporate theme with dark blue (#1e3a8a)
- ✅ Google Sans primary font, Momo signature font
- ✅ Hero images with lazy loading
- ✅ Responsive breakpoints for tablets and phones
- ✅ Touch-optimized scrolling for mobile
- ✅ Equal-width vertical property link buttons
- ✅ CSS vertical accent bars for article headings
- ✅ No emojis (professional appearance)

**Database Tables:**
- GNAF: 15M+ addresses, 14,125 localities, ~500K streets
- School Catchments: 2,122 total (1,661 primary, 447 secondary, 14 future)
- Performance: 17 indexes (~2.5GB), 2 materialized views
- School Data: gnaf.school_catchments (materialized view) + public.school_catchments_* tables

---

**Deployment Guide Version:** 2.0  
**Last Updated:** January 26, 2026  
**Author:** GitHub Copilot (Claude Sonnet 4.5)

**Version 2.0 Updates:**
- Added UI/UX Design Features section (Google Sans font, Momo font, hero images)
- Added Mobile Responsiveness section (768px tablet, 480px phone breakpoints)
- Added School Catchment Data Architecture section (two-query approach)
- Updated Technology Stack (typography, images, responsive design)
- Added troubleshooting for hero images, fonts, and mobile layouts
- Documented property links vertical button styling
- Documented address suffix fields (number_first_suffix, number_last_suffix)
- Updated feature lists with recent enhancements
- Added school_rankings.html page documentation
