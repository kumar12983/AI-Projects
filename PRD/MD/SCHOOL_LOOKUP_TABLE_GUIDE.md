# School ID Lookup Table - Documentation

## Overview

A comprehensive lookup table (`gnaf.school_type_lookup`) has been created that combines:
- **School catchment data** from `gnaf.school_catchments`
- **School profile data** from `gnaf.school_profile_2025`

This enables quick lookups of school information by school_id and provides detailed profile information.

## Table Structure

### `gnaf.school_type_lookup`

**Purpose:** Central lookup table mapping school catchment IDs with detailed profile information

**Key Columns:**
| Column | Type | Description |
|--------|------|-------------|
| `school_id` | TEXT | Unique school identifier (primary key for lookups) |
| `catchment_school_name` | VARCHAR | School name from catchment data (e.g., "Grafton PS") |
| `school_first` | VARCHAR | School name without abbreviation (e.g., "Grafton") |
| `school_abbrev` | VARCHAR | School abbreviation (PS, HS, EPS, WPS, etc.) |
| `school_type_name` | VARCHAR | Expanded school type name (e.g., "Public School", "High School") |
| `acara_sml_id` | BIGINT | School profile ID from ACARA |
| `profile_school_name` | VARCHAR | School name from profile data (e.g., "Grafton High School") |
| `school_sector` | VARCHAR | Government, Non-Government, or Catholic |
| `school_type` | VARCHAR | Primary, Secondary, or similar |
| `icsea` | NUMERIC | ICSEA index score |
| `icsea_percentile` | NUMERIC | ICSEA percentile (0-100) |
| `suburb` | VARCHAR | Suburb/locality |
| `state` | VARCHAR | State code (NSW, VIC, QLD, etc.) |
| `postcode` | VARCHAR | Postal code |
| `school_url` | VARCHAR | School website URL |
| `governing_body` | VARCHAR | Governing body name |
| `governing_body_url` | VARCHAR | Governing body website URL |
| `calendar_year` | VARCHAR | School calendar year |

**Indexes:**
- `idx_school_type_lookup_school_id` on `school_id`
- `idx_school_type_lookup_acara_sml_id` on `acara_sml_id`
- `idx_school_type_lookup_school_name` on `catchment_school_name`
- `idx_school_type_lookup_state` on `state`

## Usage Examples

### 1. Command Line Lookup by School ID

```bash
python school_id_lookup.py 2060
```

**Output:**
```
School ID: 2060
Catchment Information:
  School Name: Grafton PS
  School First: Grafton
  Abbreviation: PS
  School Type Name: Public School

Profile Information:
  Profile School Name: Grafton High School
  School Sector: Government
  School Type: Secondary
  ICSEA: 941.0
  ICSEA Percentile: 21.0

Location:
  Suburb: Grafton
  State: NSW
  Postcode: 2460

Contact:
  URL: https://grafton-h.schools.nsw.gov.au
```

### 2. Lookup All Schools by State

```bash
python school_id_lookup.py state NSW
```

Shows all schools in NSW with basic profile information.

### 3. Lookup All Schools by Sector

```bash
python school_id_lookup.py sector Government
```

Shows all government schools across all states.

## API Endpoints

### 1. Get School by ID

**Endpoint:** `GET /api/school/<school_id>`

**Authentication:** Required (Login)

**Example Request:**
```
GET /api/school/2060
```

**Example Response:**
```json
{
  "school_id": "2060",
  "school_name": "Grafton High School",
  "school_name_short": "Grafton",
  "school_sector": "Government",
  "school_type": "Secondary",
  "school_type_name": "Public School",
  "icsea": 941.0,
  "icsea_percentile": 21.0,
  "location": {
    "suburb": "Grafton",
    "state": "NSW",
    "postcode": "2460"
  },
  "contact": {
    "school_url": "https://grafton-h.schools.nsw.gov.au",
    "governing_body": "NSW Department of Education",
    "governing_body_url": "https://education.nsw.gov.au/"
  },
  "acara_sml_id": null
}
```

**Error Response (404):**
```json
{
  "error": "School not found",
  "school_id": 9999
}
```

### 2. Search Schools by Name

**Endpoint:** `GET /api/school/search-by-name`

**Authentication:** Required (Login)

**Query Parameters:**
- `q` (required): Search query (minimum 2 characters)
- `state` (optional): Filter by state code (NSW, VIC, etc.)
- `limit` (optional): Max results (default 10, max 50)

**Example Request:**
```
GET /api/school/search-by-name?q=Sydney&state=NSW&limit=10
```

**Example Response:**
```json
{
  "total_results": 5,
  "results": [
    {
      "school_id": "2060",
      "school_name": "Grafton High School",
      "school_sector": "Government",
      "school_type": "Public School",
      "icsea": 941.0,
      "icsea_percentile": 21.0,
      "location": {
        "suburb": "Grafton",
        "state": "NSW",
        "postcode": "2460"
      },
      "school_url": "https://grafton-h.schools.nsw.gov.au"
    }
  ]
}
```

### 3. Get School Profile Details

**Endpoint:** `GET /api/school/<school_id>/profile`

**Authentication:** Required (Login)

Returns comprehensive school profile data with:
- School Sector (Government, Non-Government)
- School Type and Type Name
- ICSEA value and percentile
- Location (Suburb, State, Postcode)
- Contact Information (URL, Governing Body)

## Data Statistics

### Summary
- **Total Records:** 2,048
- **Unique Schools:** 1,970
- **Matched with Profile:** 1,871 (91.3% of matched)
- **States Covered:** 9
- **NSW Coverage:** 1,702 schools (86.4%) ✓ PRIMARY FOCUS
- **Other States:** 96 schools (4.9%) - Limited coverage

### Breakdown by State
| State | Schools | Profile Matched |
|-------|---------|-----------------|
| NSW | 1,702 | 1,768 |
| QLD | 42 | 43 |
| VIC | 39 | 44 |
| SA | 4 | 4 |
| TAS | 4 | 4 |
| ACT | 3 | 3 |
| WA | 3 | 4 |
| NT | 1 | 1 |

## Python Function Reference

### `lookup_school_by_id(school_id)`

Quick lookup of school information by school_id.

**Parameters:**
- `school_id` (int): School ID to search for

**Returns:**
- `dict`: School information or `None` if not found

**Example:**
```python
from school_id_lookup import lookup_school_by_id

school = lookup_school_by_id(2060)
print(school['profile_school_name'])  # Output: "Grafton High School"
print(school['icsea'])  # Output: 941.0
```

### `lookup_schools_by_state(state_code)`

Lookup all schools in a specific state.

**Parameters:**
- `state_code` (str): State code (NSW, VIC, etc.)

**Returns:**
- `list`: List of school dictionaries

**Example:**
```python
from school_id_lookup import lookup_schools_by_state

nsw_schools = lookup_schools_by_state('NSW')
print(len(nsw_schools))  # Output: 1702
```

### `lookup_schools_by_sector(sector)`

Lookup all schools by sector.

**Parameters:**
- `sector` (str): School sector (Government, Non-Government, etc.)

**Returns:**
- `list`: List of school dictionaries

**Example:**
```python
from school_id_lookup import lookup_schools_by_sector

govt_schools = lookup_schools_by_sector('Government')
for school in govt_schools[:5]:
    print(f"{school['school_id']}: {school['catchment_school_name']}")
```

## Integration in Flask App

To enable the school profile API endpoints in your Flask app:

```python
from school_profile_search import setup_school_profile_routes

# Setup school profile routes
setup_school_profile_routes(app, DB_CONFIG)
```

This will activate:
- `GET /api/school/<school_id>` - Quick lookup by ID
- `GET /api/school/<school_id>/profile` - Get full profile
- `GET /api/school/search-by-name` - Search by name

## Matching Logic

The lookup table uses a priority-based matching strategy:

1. **Exact match** on constructed school name (e.g., "Abbotsford Public School")
2. **Prefix match** on school_first name (e.g., "Abbotsford" matches "Abbotsford Public School")
3. **Case-insensitive** ILIKE matching to handle variations

**Example Matches:**
- Catchment: "Abbotsford PS" → Profile: "Abbotsford Public School"
- Catchment: "Grafton PS" → Profile: "Grafton High School"
- Catchment: "Lindfield EPS" → Profile: "Lindfield Public School"

## School Type Abbreviations

The following abbreviations are recognized and expanded:

| Abbrev | Expanded |
|--------|----------|
| PS | Public School |
| HS | High School |
| GHS | Girls High School |
| BHS | Boys High School |
| NPS | North Public School |
| SPS | South Public School |
| WPS | West Public School |
| EPS | East Public School |
| CS | Central School |
| SC | Secondary College |
| WIS | West Infants School |
| SIS | South Infants School |
| EIS | East Infants School |
| NIS | North Infants School |
| IS | Infants School |

## Performance Considerations

- All lookups use indexed columns (`school_id`, `acara_sml_id`, `state`)
- ILIKE searches are optimized with trigram indexes
- Typical query response time: < 50ms for indexed columns

## Maintenance

To refresh the lookup table with new data:

```bash
python create_school_lookup.py
```

This will:
1. Drop the existing table
2. Recreate it with updated data from both source tables
3. Regenerate all indexes
4. Display summary statistics

## Related Files

- `create_school_lookup_table.sql` - SQL script to create the table
- `create_school_lookup.py` - Python script to execute creation
- `school_id_lookup.py` - CLI tool for quick lookups
- `school_profile_search.py` - Flask API endpoint handlers
