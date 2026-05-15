import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

DATA_DIR = "data/O_net_txt"

print("Reading skills file...")
skills_df = pd.read_csv(f"{DATA_DIR}/Skills.txt", sep="\t")

print("Building records...")
records = []
for _, row in skills_df.iterrows():
    role_id = row["O*NET-SOC Code"]
    skill_id = row["Element Name"].lower().replace(" ", "_").replace("/", "_")[:50]
    score = float(row["Data Value"]) if pd.notna(row["Data Value"]) else 0
    importance = "required" if score > 4.0 else "preferred" if score > 3.0 else "nice-to-have"
    records.append((role_id, skill_id, importance))

print(f"Inserting {len(records)} records in one shot...")
execute_values(cur, """
    INSERT INTO role_skills (role_id, skill_id, importance)
    VALUES %s
    ON CONFLICT DO NOTHING
""", records, page_size=1000)

conn.commit()
cur.close()
conn.close()
print("Done.")