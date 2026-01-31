# NSW Postcodes and Suburbs - Data Sources

## Current Status
The file `nsw_postcodes_suburbs.csv` contains postcodes but suburb names need to be populated from a reliable source.

## Recommended Data Sources

### 1. GNAF (Geocoded National Address File) - **Most Accurate**
- Official Australian government address dataset
- Download from: https://data.gov.au/
- Use the script `export_nsw_suburbs_postcodes_gnaf.py` to extract NSW data
- Command: `python export_nsw_suburbs_postcodes_gnaf.py <path-to-unzipped-gnaf> nsw_postcodes_suburbs.csv`

### 2. Australia Post Data
- Commercial postcode data available from Australia Post
- https://auspost.com.au/business/marketing-and-communications/access-data-and-insights/address-data/postcode-data

### 3. Manual Data Entry
- For specific postcodes, you can manually look up suburbs at:
  - https://auspost.com.au/postcode
  - https://postcodes-australia.com/

## Web Scraping Issues
Web scraping from public websites is unreliable because:
- HTML structure changes frequently
- Data may be incomplete or incorrectly formatted
- Rate limiting and blocking may occur

## Next Steps
1. Download GNAF data (free, official source)
2. Run the GNAF export script to get accurate suburb-postcode mappings
3. Or manually populate critical postcodes from Australia Post website
