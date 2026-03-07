# Bug Fix: Victoria School Catchment Loading Error

## Issue
Error message "Error loading catchments" displayed for Victoria addresses (e.g., 55 YARRA BVD, RICHMOND, VIC 3121).

## Root Cause
In [app.py](app.py), the `/api/address/schools` endpoint function `get_schools_for_address()` was **empty** with no implementation. The school catchment query code was incorrectly placed inside the `/api/stats` endpoint's `get_statistics()` function.

### Before (Lines 557-638):
```python
@app.route('/api/address/schools', methods=['GET'])
@login_required
def get_schools_for_address():
    """
    Get schools that contain a given address (lat/lng) in their catchment
    Example: /api/address/schools?lat=-33.8688&lng=151.2093
    """
    # ← EMPTY FUNCTION - NO CODE HERE!

@app.route('/api/stats', methods=['GET'])
def get_statistics():
    # School catchment query code was HERE (wrong place!)
    try:
        lat = float(request.args.get('lat', ''))
        lng = float(request.args.get('lng', ''))
        # ... school query code ...
```

## Solution
Moved the school catchment query code into the correct function (`get_schools_for_address()`) and properly implemented the `get_statistics()` function.

### After:
```python
@app.route('/api/address/schools', methods=['GET'])
@login_required
def get_schools_for_address():
    """
    Get schools that contain a given address (lat/lng) in their catchment
    Example: /api/address/schools?lat=-33.8688&lng=151.2093&state=VIC
    """
    # ✓ Now has proper implementation
    try:
        lat = float(request.args.get('lat', ''))
        lng = float(request.args.get('lng', ''))
        state = str(request.args.get('state', 'NSW')).strip()
        
        # Query school catchments by state and coordinates
        query = """
            SELECT DISTINCT
                school_id, school_name, campus_name,
                school_type, state, year_level_code
            FROM gnaf.school_catchments
            WHERE state = %s
            AND ST_Contains(geometry, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
            ORDER BY school_type, school_name
        """
        
        cursor.execute(query, (state, lng, lat))
        schools = cursor.fetchall()
        
        return jsonify({'count': len(schools), 'schools': schools})
    # ... error handling ...

@app.route('/api/stats', methods=['GET'])
def get_statistics():
    """Get general database statistics"""
    # ✓ Now has correct stats implementation
    # ... stats query code ...
```

## Testing
### Test Script: [test_catchment_fix.py](test_catchment_fix.py)

Verified with Richmond, VIC address (55 YARRA BVD):
```
✓ TEST PASSED - School catchments found!

Found 8 school catchments:
  ✓ Hawthorn West Primary School (PRIMARY, Year P6)
  ✓ Richmond High School (SECONDARY, Years 7-12) 
  ✓ Melbourne Girls College (SINGLE_SEX, Years 7-12)
```

### Database Status
- NSW catchments: 2,122 
- VIC catchments: 3,083 ✓
- **Total:** 5,205 school catchments

## Impact
- ✅ Victoria addresses now correctly load school catchments
- ✅ NSW addresses continue to work (backward compatible)
- ✅ Frontend correctly passes `state` parameter
- ✅ All states supported via unified API

## Files Modified
1. **[app.py](app.py)** - Lines 557-640
   - Fixed `get_schools_for_address()` endpoint
   - Fixed `get_statistics()` endpoint

## Verification Steps
1. Start Flask app: `python app.py`
2. Search for a Victoria address: "55 YARRA BVD, RICHMOND, VIC 3121"
3. Verify "School Catchments" column shows schools (no error)
4. Click "Map" button to view catchment boundaries

## Related Files
- Frontend: [static/js/address.js](static/js/address.js) - Lines 430-450 (passes state parameter)
- Test: [test_catchment_fix.py](test_catchment_fix.py) - Validation script
- Data: Victoria data loaded via `PRD/scripts/load_victoria_catchments.py`

---
**Fixed:** February 10, 2026  
**Status:** ✅ Resolved
