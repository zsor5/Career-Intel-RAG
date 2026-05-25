import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("Reading industry data...")
df = pd.read_excel("data/nat5d_6d_M2025_dl.xlsx", dtype=str)

# Only keep detailed line items at the national level
df = df[df["AREA"] == "99"]           # national only
df = df[df["O_GROUP"] == "detailed"]  # detailed occupations only
df = df[df["I_GROUP"].isin(["6-digit", "5-digit"])]   # specific industries only
df = df[df["OCC_CODE"].notna()]
df = df[df["NAICS"].notna()]

print(f"Found {len(df)} industry-occupation records")

def clean_int(val):
    try:
        v = str(val).replace(",", "").strip()
        if v in ["*", "#", "**", "nan", ""]:
            return None
        return int(float(v))
    except:
        return None

# Load unique industries first
print("Loading industries...")
industries = df[["NAICS", "NAICS_TITLE"]].drop_duplicates()
for _, row in industries.iterrows():
    cur.execute("""
        INSERT INTO industries (naics_code, name)
        VALUES (%s, %s)
        ON CONFLICT (naics_code) DO NOTHING
    """, (row["NAICS"], row["NAICS_TITLE"]))
conn.commit()
print(f"  {len(industries)} industries loaded")

# Build industry id lookup
cur.execute("SELECT naics_code, industry_id FROM industries")
industry_lookup = {row[0]: row[1] for row in cur.fetchall()}

# Load role-industry salary data
print("Loading role-industry salary data...")
records = []
for _, row in df.iterrows():
    soc_code = str(row["OCC_CODE"]).strip()
    naics = str(row["NAICS"]).strip()
    industry_id = industry_lookup.get(naics)
    if not industry_id:
        continue

    avg_salary = clean_int(row.get("A_MEDIAN"))
    p25 = clean_int(row.get("A_PCT25"))
    p75 = clean_int(row.get("A_PCT75"))
    employed = clean_int(row.get("TOT_EMP"))

    if not avg_salary:
        continue

    # match O*NET role_id using first 7 chars of SOC code
    cur.execute("""
        SELECT role_id FROM roles WHERE LEFT(role_id, 7) = %s LIMIT 1
    """, (soc_code[:7],))
    role = cur.fetchone()
    if not role:
        continue

    records.append((role[0], industry_id, avg_salary, p25, p75, employed))

print(f"Inserting {len(records)} role-industry records...")
execute_values(cur, """
    INSERT INTO role_industry (role_id, industry_id, avg_salary, salary_p25, salary_p75, total_employed)
    VALUES %s
    ON CONFLICT DO NOTHING
""", records, page_size=1000)

conn.commit()
cur.close()
conn.close()
print("Done.")