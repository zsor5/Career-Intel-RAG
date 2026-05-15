import psycopg2
import numpy as np
from dotenv import load_dotenv
from psycopg2.extras import execute_values
import os

load_dotenv()
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

print("Fetching roles with embeddings and salary data...")
cur.execute("""
    SELECT role_id, title, family, avg_salary_usd, description_vec
    FROM roles
    WHERE description_vec IS NOT NULL
    AND avg_salary_usd IS NOT NULL
    AND avg_salary_usd > 0
""")
roles = cur.fetchall()
print(f"Found {len(roles)} roles to process")

# Parse vectors
role_data = []
for role_id, title, family, salary, vec_str in roles:
    import json
    vec = np.array(json.loads(vec_str), dtype=np.float32)    
    role_data.append((role_id, title, family, salary, vec))

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def transition_difficulty(from_family, to_family, similarity):
    if from_family == to_family:
        base = 1
    else:
        base = 3
    if similarity > 0.85:
        adjustment = -1
    elif similarity < 0.70:
        adjustment = 1
    else:
        adjustment = 0
    return max(1, min(5, base + adjustment))

print("Computing transitions (this takes a few minutes)...")
transitions = []
for i, (from_id, from_title, from_family, from_salary, from_vec) in enumerate(role_data):
    similarities = []
    for j, (to_id, to_title, to_family, to_salary, to_vec) in enumerate(role_data):
        if from_id == to_id:
            continue
        sim = cosine_similarity(from_vec, to_vec)
        if sim > 0.45:  # broader similarity threshold 
            similarities.append((sim, to_id, to_title, to_family, to_salary))
    
    # take top 5 most similar roles as valid transitions
    similarities.sort(reverse=True)
    for sim, to_id, to_title, to_family, to_salary in similarities[:15]:
        salary_delta = to_salary - from_salary
        difficulty = transition_difficulty(from_family, to_family, sim)
        transitions.append((
            from_id,
            to_id,
            salary_delta,
            difficulty,
            f"Transition from {from_title} to {to_title}",
            int(sim * 100)  # use similarity as a proxy for how common
        ))

    if i % 100 == 0:
        print(f"  Processed {i+1}/{len(role_data)} roles, {len(transitions)} transitions so far...")

print(f"\nInserting {len(transitions)} transitions...")
execute_values(cur, """
    INSERT INTO career_transitions 
        (from_role_id, to_role_id, avg_salary_delta, transition_difficulty, common_upskilling_path, how_common)
    VALUES %s
    ON CONFLICT DO NOTHING
""", transitions, page_size=1000)

conn.commit()
cur.close()
conn.close()
print("Done. Career transitions loaded.")