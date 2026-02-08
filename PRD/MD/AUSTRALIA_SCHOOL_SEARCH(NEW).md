-- Australia School Search (New Feature requirements)
# Create an Australian school search page similar to NSW school catchment search page
# Consider requirements of user login similar to the school catchment search
# Use school_geometry table to auto populate school name (TSVector column exists) for search and join to school_profile_2025 using acara_sml_id to provide "school info" similar to the school catchment search
# Provide a open map for geom_5km_buffer as a boundary 
# In school, info if has_catchment is 'Y' then provide a button as hyperlink that will take them to the school catchment search for that school_id
# Provide a tile (similar to school catchment search) in home page as 'Australia School Search' for the logged in user to go the school search
# Have title of page to be 'Australia School Search' and provide link to pages 'Home, Suburb Search, Address lookup, and School Catchment Search' 
# Keep the design similar to 'School Catchment Search' page and style and fonts the same for consistency
# Address Search
    -- Add address search to Australia School Search like School Catchment Search, and load first 1000 addresses in 5km radius similar to school address search
    -- Fields design and expand/collapse design similar to school address search
    -- Allow user to search any address in Australia after the first load and show the distance from school (Haversian formula is ok)
    -- Search functionality should query the database for all matching addresses within 5km (not limited to initially loaded addresses)
    -- Both initial load and search results limited to 1000 addresses within 5km radius
    -- Ensure full address format is supported (street number, street name, suburb, state, postcode)
    
    ## Address Results Display Fields:
    
    ### Main Row (Collapsed State):
        - ADDRESS: Display full address (street number, street name, suburb, state, postcode)
        - DISTANCE: Show distance in km from the selected school
        - CONFIDENCE: Display geocoding confidence level (High/Medium/Low)
        - ACTIONS: Include "Map" button
    
    ### Expanded Section (When row is clicked):
        - COORDINATES: Display latitude and longitude
        - GEOCODE TYPE: Show geocode type (e.g., PC, Street, Locality)
        - SCHOOL CATCHMENTS: If address has school catchments, display all schools with:
            * School name as hyperlink
            * School type in parentheses (e.g., HIGH_COED, HIGH_GIRLS, PRIMARY)
        - PROPERTY LINKS: Include buttons for:
            * RealEstate.com.au (red button with house icon)
            * Domain.com.au (green button with house icon)
            * URL formatting: Properly handle multi-word street names and suburbs (e.g., "Church St" → "church-st", "North Parramatta" → "north-parramatta")
            * Street type expansions for both platforms (RealEstate uses abbreviations, Domain uses full names)
        - MAP BUTTON: Opens map showing the address in relation to the selected school