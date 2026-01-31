# Automated GNAF Download Options

## Option 1: Using the Python Script (Semi-Automated)

I've created `download_gnaf.py` which will download and extract GNAF automatically.

**Steps:**
1. Get the download URL from data.gov.au:
   - Visit: https://data.gov.au/
   - Search for "GNAF"
   - Find latest release (e.g., "NOV25 - Geoscape G-NAF - GDA2020")
   - Right-click the download button and copy the link

2. Run the script:
   ```powershell
   python download_gnaf.py
   ```
   
3. Paste the URL when prompted

The script will:
- Download the GNAF zip file (~2-3 GB)
- Extract it automatically
- Tell you the exact command to run next

## Option 2: PowerShell Direct Download (Fully Automated)

If you have a direct download link, use this one-liner:

```powershell
# Replace with actual URL from data.gov.au
$url = "https://data.gov.au/data/dataset/.../gnaf-core.zip"
$output = "$env:USERPROFILE\Downloads\GNAF\gnaf_data.zip"

# Create directory
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\Downloads\GNAF"

# Download
Invoke-WebRequest -Uri $url -OutFile $output

# Extract
Expand-Archive -Path $output -DestinationPath "$env:USERPROFILE\Downloads\GNAF\extracted" -Force

# Run the export script
python export_nsw_suburbs_postcodes_gnaf.py "$env:USERPROFILE\Downloads\GNAF\extracted"
```

## Option 3: Using curl/wget (Command Line)

```powershell
# Using PowerShell's curl alias
curl -o "$env:USERPROFILE\Downloads\gnaf.zip" "DOWNLOAD_URL_HERE"
```

## Getting the Download URL

The GNAF download URL changes with each release. To find it:

1. **Via Browser:**
   - Go to https://data.gov.au/
   - Search "GNAF" or "G-NAF"
   - Open the latest dataset
   - Right-click download → Copy link address

2. **Via API (Advanced):**
   ```powershell
   # Query data.gov.au API for latest GNAF
   $response = Invoke-RestMethod "https://data.gov.au/api/3/action/package_show?id=19432f89-dc3a-4ef3-b943-5326ef1dbecc"
   $response.result.resources | Where-Object {$_.name -like "*GDA2020*"} | Select-Object -First 1 -ExpandProperty url
   ```

## Recommended Approach

**For first-time setup:**
Use the Python script `download_gnaf.py` - it shows progress and handles errors well.

**For automation/scripts:**
Save the download URL and use the PowerShell one-liner in your automation workflow.

---

**Note:** The file is large (2-3 GB), so download may take 10-30 minutes depending on your connection.
