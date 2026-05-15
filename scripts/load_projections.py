import pandas as pd
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("Reading projections data...")
df = pd.read_excel("data/occupation.xlsx", sheet_name="Table 1.2", dtype=str)

# Row 0 is the header row, actual data starts at row 1
df.columns = [
    "title", "soc_code", "occupation_type", "employment_2024", "employment_2034",
    "dist_pct_2024", "dist_pct_2034", "change_numeric", "change_pct",
    "self_employed_pct", "annual_openings", "median_wage", "education_typical",
    "work_experience", "ojt_training", "ooh_content"
]

# Skip the header row and summary rows, only keep line items
df = df[df["occupation_type"] == "Line item"].copy()
df = df[df["soc_code"].notna()].copy()

print(f"Found {len(df)} line item occupations")

def clean_number(val):
    if val is None or str(val).strip() in ["—", "nan", "", "N/A"]:
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except:
        return None

def growth_category(pct):
    if pct is None:
        return None
    if pct >= 10:
        return "Much faster than average"
    if pct >= 5:
        return "Faster than average"
    if pct >= 2:
        return "Average"
    if pct >= 0:
        return "Slower than average"
    return "Declining"

updated = 0
for _, row in df.iterrows():
    soc_code = str(row["soc_code"]).strip()
    change_pct = clean_number(row["change_pct"])
    annual_openings = clean_number(row["annual_openings"])
    education = str(row["education_typical"]).strip() if pd.notna(row["education_typical"]) else None
    if education in ["—", "nan", ""]:
        education = None

    cur.execute("""
        UPDATE roles
        SET projected_growth_pct = %s,
            projected_annual_openings = %s,
            projected_growth_category = %s,
            education_typical = %s
        WHERE LEFT(role_id, 7) = %s
    """, (
        change_pct,
        int(annual_openings * 1000) if annual_openings else None,
        growth_category(change_pct),
        education,
        soc_code
    ))
    updated += cur.rowcount

conn.commit()
cur.close()
conn.close()
print(f"Updated {updated} roles with projection data.")