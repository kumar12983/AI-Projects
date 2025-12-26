
TASK: Run end-to-end engagement analysis for a fiscal period using a WIP Excel extract.
 
PARAMETERS (edit these as needed):
- INPUT_FILE: <your_file_name.xlsx>          # e.g., WIPs*.xlsx
- DETAIL_SHEET: Detail                       # name of the transactional sheet
- HEADER_ROW_INDEX: 7                        # 0-based row index where headers begin
- FY_START: <YYYY-MM-DD>                     # fiscal start (e.g., 2025-07-01)
- FY_END: <YYYY-MM-DD>                       # fiscal end   (e.g., 2026-06-30)
- BILLINGS: <number or M>                    # e.g., 20.11M (interpreted as 20,110,000)
- TARGET_MARGIN_PCT: <percent>               # e.g., 29
- BILLS_FILE: <Bills*.xlsx>                  # sheet "Engagement Partners"; columns: Engagement ID, Billing Partner (renamed to Engagement Partner)
- BOB_FILE: <BoB*.xlsx>                      # sheet "Export"; columns: Engagement ID, NUI ETD
- OUTPUT_FILE: <output.xlsx>                 # e.g. Engagement_Summary_FY26_YYYYMMDD_HHMMSS.xlsx **Timestamped version YYYY as Year, MM as Month, DD as Date, HH as Hour, MM as Minute, and SS as seconds**
- OUTPUT_SHEET: Summary

BUSINESS RULES (apply exactly):
1) Use **Accounting Date** to filter rows to [FY_START..FY_END]. If missing, use **Transaction Date**.
2) Treat **Expense Amount** as **pass-through revenue**.
3) For each row, then aggregate by **Engagement ID + Engagement Name**:
   - ANSR = "ANSR / Tech Revenue"
   - Margin Cost = "Margin Cost"
   - TER = ANSR + Expense Amount
   - Margin Amount = ANSR - Margin Cost
   - Margin % (on ANSR) = (Margin Amount ÷ ANSR) × 100
 4) Merge Engagement Partner from BILLS_FILE sheet "Engagement Partners" (rename "Billing Partner" -> "Engagement Partner"); if Partner is blank, copy from matching engagement with same name swapping Onshore/Offshore.
 5) Merge NUI ETD from BOB_FILE sheet "Export" by Engagement ID.


# Preparing Bills Input: "Bills_*.xlsx"
1. Add a column in "Export" Sheet called "Billing Amount" after "Tax" column
2. Populate "Billing Amount" = "Total Invoice Amount incl Tax" - "Tax"
3. Add a column "Invoice Month" next to "Invoice Date"
4. Calculate "Invoice Month" as "=TEXT(<Invoice Date>, "YYYY-MM")" 
5. Add a column "Engagement ID" in "Export" Sheet
6. Parse "Lead Engagement Name (ID) Currency" column to find Engagement ID within Parantheses. Extract Engagement ID and populate the column in Export sheet
7. Prepare a pivot tab in Bills_*.xlsx as "Billing" with below columns
   - Filter for Invoice Month From "2025-08" for the Pivot
   - Engagement ID
   - Billing Partner
   - Sum(Total Invoice Amount incl Tax)
   - SUM(Tax)
   - SUM(Billing Amount)
8. Use final total "SUM(Billing Amount)" in the below steps as "Billings" input

# Preparing BoB* Input: "BoB*.xlsx"
1. Add a column "Engagement ID" in "Export" Sheet
2. Parse "Engagement Name (ID) Currency" column to find Engagement ID within Parantheses. Extract Engagement ID and populate the column in Export sheet.

# Step 1: Prepare inputs
python  --input  --output Bills_prepared.xlsx
python  --input  --output BoB_prepared.xlsx

**AFTER PREPARING BILLS* and BOB* FILE** EXECUTE BELOW FOR OUTPUT FILE

# EXECUTE Python script
   - "fy_engagement_analysis.py" -> for below DELIVERABLE in EXCEL SHEET FORMAT
   # Step 2: Run analysis (use billings amount from prepare_bills output)
python  `
  --input  `
  --sheet Detail `
  --fy-start 2025-07-01 `
  --fy-end 2026-06-30 `
  --billings 148.72M `
  --target-margin-pct 28 `
  --bills Bills_prepared.xlsx `
  --bob BoB_prepared.xlsx `
  --output Engagement_Summary_FY26_<YYYYMMDD_HHMMSS>.xlsx `
  --print-markdown
   - # e.g. "fy_engagement_analysis.py --input WIPs.xlsx --sheet Detail --fy-start 2025-07-01 --fy-end 2026-06-30 --billings 17M --target-margin-pct 28 --bills Bills_08.12.2025.xlsx --bob BoB_08.12.2025.xlsx --output Engagement_Summary_FY26_<YYYYMMDD_HHMMSS>.xlsx"

DELIVERABLES:
# Engagement Summary (FYTD) - Financial Year To DATE
 A) Build Engagement Summary table (rounded to 2 decimals; sorted by TER desc) with columns:
   - Engagement ID
   - Engagement Name
   - ANSR / Tech Revenue
   - Margin Cost
   - Margin Amount
   - TER
   - Margin %
   - Hours
   - Engagement Partner **Add From Bills*.xlsx** OR **Add from BoB*.xlsx**
      - if Engagement Partner not found in Bills*.xlsx, try resolving from BoB*.xlsx by looking up Engagement ID
   - Engagement Manager **Add From BoBs*.xlsx**
   - NUI ETD **Add From BoBs*.xlsx**
   - Engagement Status **Add From BoBs*.xlsx**
   - Totals row uses SUBTOTAL for numeric columns (including NUI ETD); conditional formatting on NUI ETD: >0 red fill, <0 green fill.

   # Engagement Summary (ETD) - Engagement to DATE (All Items)
 B) 
   Build Engagement Summary table (ETD) (rounded to 2 decimals; sorted by TER desc) with columns:
   - Engagement ID
   - Engagement Name
   - ANSR / Tech Revenue
   - Margin Cost
   - Margin Amount
   - TER
   - Margin %
   - Hours
   - Engagement Partner **Add From Bills*.xlsx** OR **Add from BoB*.xlsx**
      - if Engagement Partner not found in Bills*.xlsx, try resolving from BoB*.xlsx by looking up Engagement ID
   - Engagement Manager **Add From BoBs*.xlsx**
   - NUI ETD **Add From BoBs*.xlsx**
   - Engagement Status **Add From BoBs*.xlsx**
   - Totals row uses SUBTOTAL for numeric columns (including NUI ETD); conditional formatting on NUI ETD: >0 red fill, <0 green fill.

   C) Build Employee Summary table (rounded to 2 decimals; sorted by "Level" desc, TER desc) with columns:
    - Employee / Product Name
    - Employee GUI / Product ID
    - Rank
    - Grade
    - Employee Region
    - Country / Region
    - Service Line
    - Hours
    - NSR 
    - ANSR 
    - Margin Cost 
    - Expense Amount 
    - #Engagements
    - #Opportunities
    - TER
    - Margin Amount
    - Margin % (on ANSR)
    - EAF (ANSR/NSR)
    Add column: "Level" 
      -  Rank: Partner/Principal = 7
      -  Rank: Executive Director = 6
      -  Rank: Senior Manager AND Grade: 2 = 5
      -  Rank: Senior Manager AND Grade: 1 = 4
      -  Rank: Manager = 3
      -  Rank: Senior = 2
      -  Rank: Staff/Assistant = 1     

   D) Month by Month Summary
      - Month
      - Hours
      - ANSR / Tech Revenue 
      - Margin Cost 
      - Expense Amount 
      - Margin Amount 
      - TER 
      - Margin %
      - Totals row uses SUBTOTAL for numeric columns

   F) WIP vs BoB Recon
      Reconciliation of Engagement IDs between WIP and BoB files
      - Summary section showing:
        * Total in WIP
        * Total in BoB
        * Matched count
        * Only in WIP count
        * Only in BoB count
      - Detailed reconciliation table with columns:
        * Engagement ID
        * Engagement Name (from WIP)
        * In WIP (Yes/No)
        * In BoB (Yes/No)
        * Status (Matched / Missing in BoB / Missing in WIP)
   

E) KPI BRIDGE (compute and print at the top):
1) Parse BILLINGS (support “20.11M” or plain numbers). Compute **Write-on** = BILLINGS − (sum of TER).
2) **Revised Margin Amount** = (sum of Margin Amount) + Write-on.
3) **Revised Revenue** = (sum of ANSR) + Write-on.
4) **Revised Margin %** = Revised Margin Amount ÷ Revised Revenue × 100.
5) **Additional Revenue Needed** to reach TARGET_MARGIN_PCT with same cost:
   Solve x from (MarginAmount_total + x) / (ANSR_total + x) = TARGET_MARGIN_PCT%.



Save to Excel → OUTPUT_FILE (sheet OUTPUT_SHEET).

PRINT:
- Totals: ANSR_total, TER_total, MarginAmount_total, Margin%_overall (on ANSR), BILLINGS, Write-on
- Revised Margin Amount, Revised Revenue, Revised Margin %
- Additional Revenue Needed (to hit TARGET_MARGIN_PCT)
- Full Markdown table (sorted by TER desc)

EXCEL FORMATTING (Automatically Applied):
The script automatically applies comprehensive Excel formatting to all output sheets:

**All Sheets:**
- Header row: Bold, centered, size 11 (Calibri), with thin bottom border
- Proper column widths optimized for content
- Money format: `_-"$"* #,##0.00_-;\-"$"* #,##0.00_-;_-"$"* "-"??_-;_-@_-` for all financial columns

**Sheet-Specific Formatting:**
1. **Engagement Summary (FYTD & ETD):**
   - Column widths: Engagement ID (16.43), Engagement Name (48.14), ANSR/TER/Margin columns (16-24)
   - Money format applied to: ANSR / Tech Revenue, Margin Cost, Margin Amount, TER, NUI ETD
   - SUBTOTAL formulas in totals row for all numeric columns
   - Conditional formatting on NUI ETD: Red fill (>0), Green fill (<0)

2. **Employee Summary:**
   - Column widths: Employee Name (37.29), GUI (26.71), Hours (9.14), financial columns (13-20)
   - Money format applied to: NSR, ANSR, Margin Cost, Expense Amount, TER, Margin Amount
   - SUBTOTAL formulas in totals row

3. **Monthly Summary:**
   - Column widths: Month (12.0), numeric columns (16.86)
   - Money format on all financial columns (ANSR, Margin Cost, Expense Amount, Margin Amount, TER)
   - SUBTOTAL formulas in totals row

4. **WIP vs BoB Recon:**
   - Column widths: Engagement ID (16.43), Engagement Name (48.14), Status columns (10-20)
   - Summary section at top with reconciliation statistics

5. **KPI Sheets (Totals & Bridge):**
   - Column width: 20.0 for all columns
   - Money format on all amount/revenue/cost columns
   - Headers with text wrapping for readability

NOTES:
- Keep column names identical to the source ("ANSR / Tech Revenue", "Expense Amount", "Margin Cost", "Accounting Date", "Transaction Date", "Engagement ID", "Engagement Name").
- If header row differs, update HEADER_ROW_INDEX.
- If you also need EAF (ANSR ÷ NSR) or Hours, include "NSR / Tech Revenue" and "Charged Hours / Quantity" and add those columns similarly.
- Excel formatting is automatically applied by the script - no manual formatting required.
