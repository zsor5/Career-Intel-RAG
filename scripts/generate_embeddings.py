import psycopg2
import openai
from dotenv import load_dotenv
import os
import time

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

cur.execute("SELECT role_id, title, description FROM roles WHERE description_vec IS NULL")
roles = cur.fetchall()
print(f"Generating embeddings for {len(roles)} roles...")

for i, (role_id, title, description) in enumerate(roles):
    text = f"{title}: {description or ''}"
    try:
        response = client.embeddings.create(
            input=text,
            model="text-embedding-3-small"
        )
        vec = response.data[0].embedding
        cur.execute(
            "UPDATE roles SET description_vec = %s WHERE role_id = %s",
            (vec, role_id)
        )
        if i % 50 == 0:
            conn.commit()
            print(f"  {i+1}/{len(roles)} done...")
        time.sleep(0.05)
    except Exception as e:
        print(f"  Error on {role_id}: {e}")

conn.commit()
cur.close()
conn.close()
print("All embeddings complete.")