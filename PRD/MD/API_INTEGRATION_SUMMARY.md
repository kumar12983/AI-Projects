# School Profile Search API - Integration Summary

## ✓ API Successfully Integrated into Flask App

The school profile search API has been added to `webapp/app.py` and is now active.

---

## API Endpoints Available

### 1. **Quick School Lookup by ID**
```
GET /api/school/<school_id>
```

**Authentication:** Required (Login)

**Example Request:**
```
GET /api/school/1001
```

**Example Response:**
```json
{
  "school_id": "1001",
  "school_name": "Abbotsford Public School",
  "school_name_short": "Abbotsford",
  "school_sector": "Government",
  "school_type": "Primary",
  "school_type_name": "Public School",
  "icsea": 1113.0,
  "icsea_percentile": 87.0,
  "location": {
    "suburb": "Abbotsford",
    "state": "NSW",
    "postcode": "2046"
  },
  "contact": {
    "school_url": "https://abbotsford-p.schools.nsw.gov.au",
    "governing_body": "NSW Department of Education",
    "governing_body_url": "https://education.nsw.gov.au/"
  },
  "acara_sml_id": null
}
```

**Error (404):**
```json
{
  "error": "School not found",
  "school_id": "1001"
}
```

---

### 2. **Search Schools by Name**
```
GET /api/school/search-by-name
```

**Authentication:** Required (Login)

**Query Parameters:**
- `q` (required): Search query (minimum 2 characters)
- `state` (optional): Filter by state code (NSW, VIC, etc.)
- `limit` (optional): Max results (default 10, max 50)

**Example Request:**
```
GET /api/school/search-by-name?q=Sydney&state=NSW&limit=5
```

**Example Response:**
```json
{
  "total_results": 5,
  "results": [
    {
      "school_id": "1001",
      "school_name": "Sydney Grammar School",
      "school_sector": "Non-Government",
      "school_type": "Public School",
      "icsea": 1200.0,
      "icsea_percentile": 99.0,
      "location": {
        "suburb": "Sydney",
        "state": "NSW",
        "postcode": "2000"
      },
      "school_url": "https://www.sydneygrammar.nsw.edu.au"
    }
  ]
}
```

---

### 3. **Get Full School Profile**
```
GET /api/school/<school_id>/profile
```

**Authentication:** Required (Login)

**Returns:** Same as endpoint #1 (comprehensive profile data)

---

## Where It's Used in App

### Integration Location
**File:** `webapp/app.py` (lines ~60-63)

```python
# Setup school profile search routes
from school_profile_search import setup_school_profile_routes
setup_school_profile_routes(app, DB_CONFIG)
```

### How It Works

1. **Function Call:** `setup_school_profile_routes(app, DB_CONFIG)`
   - Registers 3 new Flask routes
   - Uses the database configuration passed to it
   - All routes require login (`@login_required`)

2. **Routes Created:**
   - `GET /api/school/<int:school_id>` - Quick lookup
   - `GET /api/school/<school_id>/profile` - Full profile
   - `GET /api/school/search-by-name` - Search by name

3. **Data Source:**
   - Queries `gnaf.school_type_lookup` table
   - Returns school profile information with ICSEA scores

---

## Frontend Integration Points

### In Templates/JavaScript

**To call the API from your frontend:**

```javascript
// Get school profile by ID
fetch('/api/school/1001', {
    headers: {
        'Accept': 'application/json'
    }
})
.then(response => response.json())
.then(data => {
    console.log('School:', data.school_name);
    console.log('ICSEA:', data.icsea);
    console.log('Sector:', data.school_sector);
});
```

**Search schools by name:**

```javascript
fetch('/api/school/search-by-name?q=Sydney&state=NSW&limit=10')
    .then(response => response.json())
    .then(data => {
        console.log(`Found ${data.total_results} schools`);
        data.results.forEach(school => {
            console.log(school.school_name);
        });
    });
```

---

## Current Implementation Details

### Source Code Files

**API Handlers:** `webapp/school_profile_search.py`
- Contains all route definitions
- Manages database queries
- Formats responses

**Python Functions:** `school_id_lookup.py`
- CLI tool
- Python library functions
- Used by school_profile_search.py

**Lookup Table:** `gnaf.school_type_lookup`
- 2,048 school records
- 1,871 matched with profiles
- Indexed for fast queries

---

## Testing the API

### Using cURL (Command Line)

```bash
# Lookup a school
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://yourapp.com/api/school/1001

# Search schools
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "https://yourapp.com/api/school/search-by-name?q=Sydney&state=NSW"
```

### Using Python

```python
import requests

headers = {'Authorization': 'Bearer YOUR_TOKEN'}

# Lookup
response = requests.get('https://yourapp.com/api/school/1001', headers=headers)
print(response.json())

# Search
response = requests.get(
    'https://yourapp.com/api/school/search-by-name?q=Sydney',
    headers=headers
)
print(response.json())
```

### Using Browser Developer Console

```javascript
fetch('/api/school/1001')
  .then(r => r.json())
  .then(d => console.table(d))
```

---

## Available Data from API

Each school record includes:

**Identification:**
- `school_id` - Unique school identifier
- `school_name` - Full school name
- `acara_sml_id` - ACARA identifier

**Classification:**
- `school_sector` - Government, Non-Government, or Catholic
- `school_type` - Primary, Secondary, Combined
- `school_type_name` - Expanded type name

**Quality Metrics:**
- `icsea` - Quality index (0-1200 scale)
- `icsea_percentile` - Ranking (0-100, higher is better)

**Location:**
- `suburb` - Suburb/locality
- `state` - State code (NSW, VIC, etc.)
- `postcode` - Postal code

**Contact:**
- `school_url` - School website
- `governing_body` - Organisation name
- `governing_body_url` - Organisation website

---

## Limitations

⚠️ **NSW-FOCUSED:** 86.4% of schools in lookup table are NSW

- Best for NSW school queries
- Limited data for other states
- For multi-state queries, query `gnaf.school_profile_2025` directly

---

## Next Steps (Optional)

### Create Frontend Features

1. **School Search Widget**
   - Add search box to your UI
   - Call `/api/school/search-by-name` on input
   - Display results with ICSEA scores

2. **School Profile Page**
   - Display full profile when school selected
   - Show ICSEA ranking
   - Link to school website

3. **School Comparison**
   - Compare ICSEA scores
   - Compare sectors and types
   - Side-by-side location comparison

### Monitor Usage

- Track API calls in logs
- Monitor response times
- Adjust limits as needed

---

## Support & Documentation

- **Quick Reference:** `SCHOOL_ID_QUICK_REFERENCE.md`
- **Technical Details:** `SCHOOL_LOOKUP_TABLE_GUIDE.md`
- **Limitations:** `NSW_FOCUSED_NOTICE.md`
- **CLI Tool:** `python school_id_lookup.py`

---

**Status:** ✅ API Integrated and Active

**Integration Date:** January 31, 2026

**Ready to use immediately!**

