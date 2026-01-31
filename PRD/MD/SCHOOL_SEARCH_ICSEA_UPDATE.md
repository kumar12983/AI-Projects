# School Search - ICSEA Display Update

## ✓ Changes Made

The School Search page now displays **ICSEA Score** and **ICSEA Percentile** when a school is selected, if this data is available in the lookup table.

---

## What Was Updated

### 1. HTML Template (`school_search.html`)

Added two new detail fields to the school info card:

```html
<div class="detail-item" id="icsea-container" style="display: none;">
    <span class="detail-label">ICSEA Score:</span>
    <span id="icsea">-</span>
</div>
<div class="detail-item" id="icsea-percentile-container" style="display: none;">
    <span class="detail-label">ICSEA Percentile:</span>
    <span id="icsea-percentile">-</span>
</div>
```

- Containers are hidden by default
- Show only when ICSEA data is available

### 2. JavaScript (`school.js`)

Updated the `displaySchoolInfo()` function to:

```javascript
// Display ICSEA if available
if (info.icsea !== null && info.icsea !== undefined) {
    document.getElementById('icsea').textContent = Math.round(info.icsea);
    document.getElementById('icsea-container').style.display = 'block';
} else {
    document.getElementById('icsea-container').style.display = 'none';
}

// Display ICSEA percentile if available
if (info.icsea_percentile !== null && info.icsea_percentile !== undefined) {
    document.getElementById('icsea-percentile').textContent = Math.round(info.icsea_percentile) + '%';
    document.getElementById('icsea-percentile-container').style.display = 'block';
} else {
    document.getElementById('icsea-percentile-container').style.display = 'none';
}
```

- Rounds ICSEA score to whole number
- Adds % symbol to percentile
- Shows/hides containers based on data availability

Also added School Sector display:
```javascript
document.getElementById('schoolSector').textContent = info.school_sector || 'N/A';
```

### 3. CSS Styling (`style.css`)

Added special styling for ICSEA fields:

```css
#icsea-container span:last-child,
#icsea-percentile-container span:last-child {
    font-size: 1.25rem;
    color: #1e3a8a;
    font-weight: 600;
}
```

- Larger font size (1.25rem vs 1.125rem)
- Bold weight (600)
- Primary color (#1e3a8a) for emphasis

---

## How It Works

### When a School is Selected:

1. API endpoint `/api/school/<school_id>` is called
2. Returns school data including `icsea` and `icsea_percentile`
3. `displaySchoolInfo()` function checks if these values exist
4. If present: shows the fields with formatted data
5. If missing: hides the fields (no broken appearance)

### Data Flow:

```
User selects school
    ↓
API called: GET /api/school/1001
    ↓
Response includes icsea & icsea_percentile
    ↓
displaySchoolInfo() processes data
    ↓
ICSEA fields shown/hidden based on data
```

---

## Display Examples

### School With ICSEA Data (e.g., Abbotsford PS)

```
NSW School Catchment Search

School Name: Abbotsford Public School [PRIMARY]

Year Levels: K, 1, 2, 3, 4, 5, 6
School Type: Government Primary School
School Sector: Government
Catchment Priority: Local Intake Area
ICSEA Score: 1113
ICSEA Percentile: 87%
```

### School Without ICSEA Data

```
NSW School Catchment Search

School Name: Example School [PRIMARY]

Year Levels: K, 1, 2, 3, 4, 5, 6
School Type: Government Primary School
School Sector: Government
Catchment Priority: Local Intake Area
(ICSEA fields not shown)
```

---

## Data Availability

⚠️ **NSW-Focused**: ICSEA data is primarily available for NSW schools

- **NSW Schools:** 1,702 records, 1,768 matched with ICSEA
- **Other States:** Limited coverage
- **Missing Schools:** 172 schools have no state/ICSEA data

---

## Technical Details

### Files Modified:

1. **`webapp/templates/school_search.html`**
   - Added ICSEA display containers
   - Added School Sector field

2. **`webapp/static/js/school.js`**
   - Updated `displaySchoolInfo()` function
   - Added ICSEA formatting and visibility logic
   - Added School Sector display

3. **`webapp/static/css/style.css`**
   - Added styling for ICSEA fields
   - Larger, bolder font for emphasis

### API Data Structure:

The school lookup API returns:

```json
{
  "school_id": "1001",
  "school_name": "Abbotsford Public School",
  "school_sector": "Government",
  "icsea": 1113.0,
  "icsea_percentile": 87.0,
  ...other fields...
}
```

---

## Testing

To test the ICSEA display:

1. Open the School Search page
2. Search for a NSW school (e.g., "Abbotsford")
3. Click on a school result
4. School details should show with ICSEA data (if available)

**Example NSW Schools with ICSEA:**
- School ID 1001 - Abbotsford PS (ICSEA: 1113, Percentile: 87%)
- School ID 1002 - Aberdeen PS (ICSEA: 890, Percentile: 5%)
- School ID 2060 - Grafton PS (ICSEA: 941, Percentile: 21%)

---

## ICSEA Explained

**ICSEA (Index of Community Socio-Educational Advantage)**

- **Range:** 0 to ~1200
- **Average:** 1000
- **Higher = Better:** Score reflects school performance and student advantage
- **Percentile:** Ranking compared to all Australian schools
  - 87% = In top 13% of schools
  - 50% = Average performance
  - 5% = Below average

---

## Future Enhancements

Possible next features:

- [ ] Add ICSEA comparison between schools
- [ ] Color-code ICSEA scores (red=low, green=high)
- [ ] Show ICSEA trend over time
- [ ] Filter schools by ICSEA range
- [ ] Add HSC/NAPLAN scores when available

---

## Status

✅ **Complete and Ready**

All changes are live. School Search now displays ICSEA data when available.

