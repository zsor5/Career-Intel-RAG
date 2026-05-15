import pandas as pd
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("Reading BLS salary data...")
df = pd.read_excel("data/national_M2024_dl.xlsx", dtype=str)

updated = 0
for _, row in df.iterrows():
    soc_code = str(row["OCC_CODE"]).strip()
    try:
        p25 = int(float(str(row.get("A_PCT25", "0")).replace("*", "0").replace("#", "0")))
        median = int(float(str(row.get("A_MEDIAN", "0")).replace("*", "0").replace("#", "0")))
        p75 = int(float(str(row.get("A_PCT75", "0")).replace("*", "0").replace("#", "0")))
    except:
        continue

    cur.execute("""
        UPDATE roles
        SET avg_salary_usd = %s, salary_p25 = %s, salary_p75 = %s
        WHERE LEFT(role_id, 7) = %s
    """, (median, p25, p75, soc_code))
    updated += cur.rowcount

conn.commit()
cur.close()
conn.close()
print(f"Salary data updated for {updated} roles.")