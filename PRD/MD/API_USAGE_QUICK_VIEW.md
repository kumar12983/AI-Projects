# Where School Profile API is Used

## Integration Summary

### ✓ Integrated in `webapp/app.py`

**Location:** Lines 63-64

```python
from school_profile_search import setup_school_profile_routes
setup_school_profile_routes(app, DB_CONFIG)
```

---

## 3 New API Endpoints Created

### 1️⃣ Quick Lookup by School ID
```
GET /api/school/<school_id>
```
- Fast lookup using indexed school_id
- Returns full school profile
- Example: `/api/school/1001`

### 2️⃣ Search Schools by Name  
```
GET /api/school/search-by-name?q=...&state=...&limit=...
```
- Search by school name
- Optional state filter
- Example: `/api/school/search-by-name?q=Sydney&state=NSW`

### 3️⃣ Get Full Profile
```
GET /api/school/<school_id>/profile
```
- Comprehensive profile data
- Same as endpoint #1
- Example: `/api/school/1001/profile`

---

## What Data is Returned

For each school:

✓ **School Info**
- Name, ID, Type, Sector

✓ **Quality Metrics**
- ICSEA score (0-1200)
- ICSEA percentile (0-100)

✓ **Location**
- Suburb, State, Postcode

✓ **Contact**
- Website URL
- Governing body info

---

## How to Use From Frontend

### JavaScript/Browser
```javascript
// Lookup school
fetch('/api/school/1001')
  .then(r => r.json())
  .then(school => console.log(school.school_name))

// Search schools
fetch('/api/school/search-by-name?q=Sydney&state=NSW')
  .then(r => r.json())
  .then(results => console.log(results.total_results))
```

### HTML Form
```html
<form action="/api/school/search-by-name">
  <input name="q" placeholder="School name" required>
  <select name="state">
    <option value="NSW">NSW</option>
    <option value="VIC">VIC</option>
  </select>
  <button>Search</button>
</form>
```

---

## Data Flow

```
User Request
    ↓
Flask App (app.py)
    ↓
school_profile_search.py (handles API)
    ↓
school_id_lookup.py (queries database)
    ↓
PostgreSQL Table: gnaf.school_type_lookup
    ↓
JSON Response
```

---

## Active Endpoints Summary

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/api/school/<id>` | GET | ✓ | Quick lookup |
| `/api/school/<id>/profile` | GET | ✓ | Full profile |
| `/api/school/search-by-name` | GET | ✓ | Search by name |

---

## Example Usage

**Find school by ID 1001:**
```
GET /api/school/1001
```

**Response:**
```json
{
  "school_id": "1001",
  "school_name": "Abbotsford Public School",
  "school_sector": "Government",
  "icsea": 1113.0,
  "icsea_percentile": 87.0,
  "location": {
    "suburb": "Abbotsford",
    "state": "NSW",
    "postcode": "2046"
  }
}
```

---

## ⚠️ Important Notes

- All endpoints require user to be **logged in**
- Data is **NSW-focused** (86.4% of records)
- Queries use **indexed columns** for speed
- Response time: **< 50ms** typically

---

## See Also

- `API_INTEGRATION_SUMMARY.md` - Detailed integration guide
- `SCHOOL_LOOKUP_TABLE_GUIDE.md` - Full API documentation
- `school_profile_search.py` - Source code
- `school_id_lookup.py` - Query functions

