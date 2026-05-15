import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

# O*NET education level category codes
EDUCATION_LEVELS = {
    1: "Less than high school diploma",
    2: "High school diploma or equivalent",
    3: "Post-secondary certificate",
    4: "Some college, no degree",
    5: "Associate's degree",
    6: "Bachelor's degree",
    7: "Post-baccalaureate certificate",
    8: "Master's degree",
    9: "Post-master's certificate",
    10: "First professional degree",
    11: "Doctoral degree",
    12: "Post-doctoral training"
}

print("Reading education data...")
df = pd.read_csv("data/O_net_txt/Education, Training, and Experience.txt", sep="\t")

# Only keep Required Level of Education rows
ed_df = df[df["Element Name"] == "Required Level of Education"].copy()
ed_df = ed_df[ed_df["Category"].notna()].copy()
ed_df = ed_df[ed_df["Data Value"].notna()].copy()

print(f"Found {len(ed_df)} education records")

records = []
for _, row in ed_df.iterrows():
    role_id = str(row["O*NET-SOC Code"]).strip()
    category = int(float(row["Category"]))
    pct = float(row["Data Value"])
    
    if category not in EDUCATION_LEVELS:
        continue
    if pct <= 0:
        continue

    education_level = EDUCATION_LEVELS[category]
    records.append((role_id, education_level, pct))

print(f"Inserting {len(records)} education records...")
execute_values(cur, """
    INSERT INTO role_education (role_id, education_level, education_pct)
    VALUES %s
    ON CONFLICT (role_id, education_level) DO UPDATE
    SET education_pct = EXCLUDED.education_pct
""", records, page_size=1000)

conn.commit()
cur.close()
conn.close()
print("Done.")