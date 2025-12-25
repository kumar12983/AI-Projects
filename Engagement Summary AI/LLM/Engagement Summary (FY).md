TASK: Run end-to-end engagement analysis for a fiscal period using a WIP Excel extract.

PARAMETERS (edit these as needed):

INPUT_FILE: <your_file_name.xlsx> # e.g., WIPs*.xlsx
DETAIL_SHEET: Detail # name of the transactional sheet
HEADER_ROW_INDEX: 7 # 0-based row index where headers begin
FY_START: # fiscal start (e.g., 2025-07-01)
FY_END: # fiscal end (e.g., 2026-06-30)
BILLINGS: # e.g., 20.11M (interpreted as 20,110,000)
TARGET_MARGIN_PCT: # e.g., 29
BILLS_FILE: <Bills*.xlsx> # sheet "Engagement Partners"; columns: Engagement ID, Billing Partner (renamed to Engagement Partner)
BOB_FILE: <BoB*.xlsx> # sheet "Export"; columns: Engagement ID, NUI ETD
OUTPUT_FILE: <output.xlsx> # e.g. Engagement_Summary_FY26_YYYYMMDD_HHMMSS.xlsx
OUTPUT_SHEET: Summary
BUSINESS RULES (apply exactly):

Use Accounting Date to filter rows to [FY_START..FY_END]. If missing, use Transaction Date.
Treat Expense Amount as pass-through revenue.
For each row, then aggregate by Engagement ID + Engagement Name:
ANSR = "ANSR / Tech Revenue"
Margin Cost = "Margin Cost"
TER = ANSR + Expense Amount
Margin Amount = ANSR - Margin Cost
Margin % (on ANSR) = (Margin Amount ÷ ANSR) × 100
Merge Engagement Partner from BILLS_FILE sheet "Engagement Partners" (rename "Billing Partner" -> "Engagement Partner"); if Partner is blank, copy from matching engagement with same name swapping Onshore/Offshore.
Merge NUI ETD from BOB_FILE sheet "Export" by Engagement ID.
EXECUTE Python script
"fy_engagement_analysis.py" -> for below DELIVERABLE in EXCEL SHEET FORMAT
e.g. "fy_engagement_analysis.py --input WIPs.xlsx --sheet Detail --fy-start 2025-07-01 --fy-end 2026-06-30 --billings 17M --target-margin-pct 28 --bills Bills_08.12.2025.xlsx --bob BoB_08.12.2025.xlsx --output Engagement_Summary_FY26_Final.xlsx"

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
  - Engagement Partner
  - NUI ETD
  - Totals row uses SUBTOTAL for numeric columns (including NUI ETD); conditional formatting on NUI ETD: >0 red fill, <0 green fill.

# Employee Summary table
B) Build Employee Summary table (rounded to 2 decimals; sorted by "Level" desc, TER desc) with columns:
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

# Month-by-Month Summary table
 C) Month by Month Summary
      - Month
      - Hours
      - ANSR / Tech Revenue 
      - Margin Cost 
      - Expense Amount 
      - Margin Amount 
      - TER 
      - Margin %

# KPI BRIDGE (Target calculations)
D) KPI BRIDGE (compute and print at the top):

Parse BILLINGS (support “20.11M” or plain numbers). Compute Write-on = BILLINGS − (sum of TER).
Revised Margin Amount = (sum of Margin Amount) + Write-on.
Revised Revenue = (sum of ANSR) + Write-on.
Revised Margin % = Revised Margin Amount ÷ Revised Revenue × 100.
Additional Revenue Needed to reach TARGET_MARGIN_PCT with same cost: Solve x from (MarginAmount_total + x) / (ANSR_total + x) = TARGET_MARGIN_PCT%.

# Engagement Summary (ETD) - Engagement to DATE (All Items)
 E) 
   Build Engagement Summary table (ETD) (rounded to 2 decimals; sorted by TER desc) with columns:
   - Engagement ID
   - Engagement Name
   - ANSR / Tech Revenue
   - Margin Cost
   - Margin Amount
   - TER
   - Margin %
   - Hours
   - Engagement Partner
   - NUI ETD
   - Totals row uses SUBTOTAL for numeric columns (including NUI ETD); conditional formatting on NUI ETD: >0 red fill, <0 green fill.

Save to Excel → OUTPUT_FILE (sheet OUTPUT_SHEET).

PRINT:

Totals: ANSR_total, TER_total, MarginAmount_total, Margin%_overall (on ANSR), BILLINGS, Write-on
Revised Margin Amount, Revised Revenue, Revised Margin %
Additional Revenue Needed (to hit TARGET_MARGIN_PCT)
Full Markdown table (sorted by TER desc)

NOTES:

Keep column names identical to the source (“ANSR / Tech Revenue”, “Expense Amount”, “Margin Cost”, “Accounting Date”, “Transaction Date”, “Engagement ID”, “Engagement Name”).
If header row differs, update HEADER_ROW_INDEX.
If you also need EAF (ANSR ÷ NSR) or Hours, include “NSR / Tech Revenue” and “Charged Hours / Quantity” and add those columns similarly.
