# Engagement Summary Toolkit

This toolkit produces fiscal-year engagement, employee, and monthly summaries with KPI bridge, Engagement Partner, and NUI ETD enrichment.

## Contents
- **prepare_bills.py** — prepares Bills*.xlsx input file (extracts Engagement ID, calculates Billing Amount, creates pivot)
- **prepare_bob.py** — prepares BoB*.xlsx input file (extracts Engagement ID from Export sheet)
- **fy_engagement_analysis.py** — end-to-end generator (Excel + console output)
- **Engagement Summary/Engagement Summary (FY).md** — task/rules reference and parameters
- **Bills_*.xlsx** — provides Engagement Partner data (sheet: "Engagement Partners", column: Billing Partner)
- **BoB_*.xlsx** — provides NUI ETD, Engagement Manager, Engagement Status (sheet: "Export")
- **WIPs*.xlsx** — main transactional WIP input (sheet: Detail by default)

## Prerequisites
- Python 3.12+ with pandas, numpy, openpyxl (already installed in .venv)
- Raw input files: WIPs*.xlsx, Bills_*.xlsx, BoB_*.xlsx

## Quick start

### Step 1: Prepare input files

Activate the venv (PowerShell):
```powershell
& "C:\Users\sankaku\OneDrive - EY\workspace\.venv\Scripts\Activate.ps1"
```

**Prepare Bills file** (extracts Engagement ID, calculates Billing Amount, creates pivot):
```powershell
python prepare_bills.py --input Bills_08.12.2025.xlsx --output Bills_08.12.2025_prepared.xlsx --invoice-month-from 2025-08
```
This will:
- Add "Billing Amount" = Total Invoice Amount incl Tax - Tax
- Add "Invoice Month" from Invoice Date (YYYY-MM format)
- Extract "Engagement ID" from "Lead Engagement Name (ID) Currency" column
- **Filter invoices from 2025-08 onwards** (configurable via --invoice-month-from)
- Create "Billing" pivot sheet with totals by Engagement ID and Billing Partner
- Display total Billing Amount (use this for --billings parameter)

**Prepare BoB file** (extracts Engagement ID):
```powershell
python prepare_bob.py --input BoB_08.12.2025.xlsx --output BoB_08.12.2025_prepared.xlsx
```
This will:
- Extract "Engagement ID" from "Engagement Name (ID) Currency" column in Export sheet
- Verify presence of NUI ETD, Engagement Manager, Engagement Status columns

### Step 2: Run the engagement analysis

Run the analysis with prepared files:
```powershell
python fy_engagement_analysis.py `
  --input WIPs.xlsx `
  --sheet Detail `
  --fy-start 2025-07-01 `
  --fy-end 2026-06-30 `
  --billings 17.99M `
  --target-margin-pct 28 `
  --bills Bills_08.12.2025_prepared.xlsx `
  --bob BoB_08.12.2025_prepared.xlsx `
  --output Engagement_Summary_FY26_20251226.xlsx `
  --print-markdown
```
**Note:** Use the billings amount reported by `prepare_bills.py` in the --billings parameter.

## Parameters (key ones)
- --input: WIP file (e.g., WIPs.xlsx)
- --sheet: transactional sheet (default Detail)
- --fy-start / --fy-end: fiscal window (YYYY-MM-DD)
- --billings: billings total (supports "20.11M")
- --target-margin-pct: target margin percent
- --bills: Bills file with sheet "Engagement Partners" (column Billing Partner → Engagement Partner)
- --bob: BoB file with sheet "Export" (column NUI ETD)
- --output: Excel output path
- --print-markdown: also print top engagement markdown to console

## What the script generates
- **Engagement Summary (FYTD) sheet:** Filtered to FY dates, TER-sorted, includes Engagement Partner, Engagement Manager, Engagement Status, and NUI ETD; totals row with SUBTOTAL; conditional formatting on NUI ETD (>0 red, <0 green).
- **Engagement Summary (ETD) sheet:** All dates (Engagement To Date), same columns and formatting as FYTD.
- **Employee Summary sheet:** Level calculation, totals row with SUBTOTAL.
- **Monthly Summary sheet:** month-level rollup for the FY period.
- **KPI Totals sheet** and **KPI Bridge sheet:** billings vs TER, margin gap, additional revenue needed to hit target margin.

## Rules implemented (mirrors Engagement Summary (FY).md)
- Use Accounting Date (fallback Transaction Date) within FY range.
- Expense Amount treated as pass-through revenue (included in TER).
- Metrics: ANSR, Margin Cost, TER=ANSR+Expense, Margin Amount=ANSR−Margin Cost, Margin % on ANSR.
- Engagement Partner merged from Bills; blanks backfilled via Onshore/Offshore name match.
- Engagement Manager, Engagement Status, and NUI ETD merged from BoB by Engagement ID.
- FYTD vs ETD: FYTD filters to FY window; ETD includes all transaction dates.

## Input File Preparation Details

### Bills*.xlsx preparation (prepare_bills.py)
The script performs these transformations on the "Export" sheet:
1. **Billing Amount** = "Total Invoice Amount incl Tax" - "Tax"
2. **Invoice Month** = TEXT(Invoice Date, "YYYY-MM")
3. **Engagement ID** extracted from "Lead Engagement Name (ID) Currency" using regex pattern `\(([A-Z]-\d+)\)`
4. **Filter by Invoice Month** (default: from 2025-08 onwards, configurable via --invoice-month-from)
5. **Billing pivot sheet** created with columns:
   - Engagement ID
   - Billing Partner
   - Sum of Total Invoice Amount incl Tax
   - Sum of Tax
   - Sum of Billing Amount

The total Billing Amount from the pivot is what you should use for the `--billings` parameter in the analysis.

### BoB*.xlsx preparation (prepare_bob.py)
The script performs these transformations on the "Export" sheet:
1. **Engagement ID** extracted from "Engagement Name (ID) Currency" using regex pattern `\(([A-Z]-\d+)\)`
2. Verifies presence of required columns:
   - NUI ETD
   - Engagement Manager
   - Engagement Status

The prepared file will be used by the analysis script to enrich engagement summaries.

## Tips
- If a file is locked (OneDrive), copy to a temp name and point --bob/--bills to it.
- Ensure header row index matches your WIP layout (default 7 is 0-based).
- You can omit --bills or --bob; those columns simply won’t appear.

## References
See Engagement Summary/Engagement Summary (FY).md for the full specification and business rules.
