-- Index for the main join between address_detail and address_site_geocode
CREATE INDEX IF NOT EXISTS idx_address_detail_site_pid 
ON gnaf.address_detail(address_site_pid) 
WHERE address_site_pid IS NOT NULL;

-- Composite index for bounding box queries on latitude/longitude
-- (This already exists based on earlier query: idx_address_site_geo_lat_lng)

-- Index for street locality joins
CREATE INDEX IF NOT EXISTS idx_address_detail_street_locality 
ON gnaf.address_detail(street_locality_pid) 
WHERE street_locality_pid IS NOT NULL;

-- Index for locality joins
CREATE INDEX IF NOT EXISTS idx_address_detail_locality 
ON gnaf.address_detail(locality_pid) 
WHERE locality_pid IS NOT NULL;

-- Index for postcode filtering (very common filter)
CREATE INDEX IF NOT EXISTS idx_address_detail_postcode 
ON gnaf.address_detail(postcode) 
WHERE postcode IS NOT NULL;