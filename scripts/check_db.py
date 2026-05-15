import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

tables = ["roles", "skills", "role_skills", "industries", "postings", "career_transitions"]
for table in tables:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    count = cur.fetchone()[0]
    print(f"{table}: {count} rows")

cur.close()
conn.close()