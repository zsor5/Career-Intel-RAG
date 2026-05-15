import pandas as pd
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

DATA_DIR = "data/O_net_txt"  # update this to match your unzipped folder name

def infer_seniority(title):
    t = title.lower()
    if any(w in t for w in ["senior", "lead", "principal", "staff"]): return "senior"
    if any(w in t for w in ["manager", "director", "vp", "chief"]): return "leadership"
    if any(w in t for w in ["junior", "entry", "associate"]): return "entry"
    return "mid"

def infer_family(title):
    t = title.lower()
    if any(w in t for w in ["software", "developer", "engineer"]): return "engineering"
    if any(w in t for w in ["data", "analyst", "scientist"]): return "data"
    if any(w in t for w in ["product", "program", "project"]): return "product"
    if any(w in t for w in ["design", "ux", "ui"]): return "design"
    if any(w in t for w in ["market", "sales", "account"]): return "business"
    if any(w in t for w in ["nurse", "physician", "therapist"]): return "healthcare"
    return "other"

# Load roles
print("Loading roles...")
occ = pd.read_csv(f"{DATA_DIR}/Occupation Data.txt", sep="\t")
for _, row in occ.iterrows():
    cur.execute("""
        INSERT INTO roles (role_id, title, seniority_level, family, description)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (role_id) DO NOTHING
    """, (row["O*NET-SOC Code"], row["Title"], infer_seniority(row["Title"]),
          infer_family(row["Title"]), row["Description"]))
conn.commit()
print(f"  {len(occ)} roles loaded.")

# Load role_skills (bulk insert)
print("Loading role-skill mappings...")
records = []
for _, row in skills_df.iterrows():
    role_id = row["O*NET-SOC Code"]
    skill_id = row["Element Name"].lower().replace(" ", "_").replace("/", "_")[:50]
    score = float(row["Data Value"]) if pd.notna(row["Data Value"]) else 0
    importance = "required" if score > 4.0 else "preferred" if score > 3.0 else "nice-to-have"
    records.append((role_id, skill_id, importance))

from psycopg2.extras import execute_values
execute_values(cur, """
    INSERT INTO role_skills (role_id, skill_id, importance)
    VALUES %s
    ON CONFLICT DO NOTHING
""", records)
conn.commit()
print(f"  {len(records)} mappings loaded.")

# Load role_skills
print("Loading role-skill mappings...")
for _, row in skills_df.iterrows():
    role_id = row["O*NET-SOC Code"]
    skill_id = row["Element Name"].lower().replace(" ", "_").replace("/", "_")[:50]
    score = float(row["Data Value"]) if pd.notna(row["Data Value"]) else 0
    importance = "required" if score > 4.0 else "preferred" if score > 3.0 else "nice-to-have"
    cur.execute("""
        INSERT INTO role_skills (role_id, skill_id, importance)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (role_id, skill_id, importance))
conn.commit()
print("  Done.")

cur.close()
conn.close()
print("\nAll done — no API key needed.")