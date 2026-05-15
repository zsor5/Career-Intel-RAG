import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

commands = [
    """
    CREATE EXTENSION IF NOT EXISTS vector
    """,
    """
    CREATE TABLE IF NOT EXISTS roles (
        role_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        seniority_level TEXT,
        family TEXT,
        description TEXT,
        avg_salary_usd INTEGER,
        salary_p25 INTEGER,
        salary_p75 INTEGER,
        remote_friendly BOOLEAN,
        growth_outlook TEXT,
        description_vec vector(1536)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS skills (
        skill_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT,
        embedding vector(1536)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS role_skills (
        role_id TEXT REFERENCES roles(role_id),
        skill_id TEXT REFERENCES skills(skill_id),
        importance TEXT,
        PRIMARY KEY (role_id, skill_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS industries (
        industry_id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        sector TEXT,
        salary_modifier FLOAT DEFAULT 1.0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS role_industry (
        role_id TEXT REFERENCES roles(role_id),
        industry_id INTEGER REFERENCES industries(industry_id),
        typical_salary_modifier FLOAT DEFAULT 1.0,
        PRIMARY KEY (role_id, industry_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS postings (
        posting_id SERIAL PRIMARY KEY,
        role_id TEXT REFERENCES roles(role_id),
        company_size TEXT,
        industry_id INTEGER REFERENCES industries(industry_id),
        location TEXT,
        remote_ok BOOLEAN,
        date_scraped DATE DEFAULT CURRENT_DATE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS career_transitions (
        from_role_id TEXT REFERENCES roles(role_id),
        to_role_id TEXT REFERENCES roles(role_id),
        avg_salary_delta INTEGER,
        transition_difficulty INTEGER CHECK (transition_difficulty BETWEEN 1 AND 5),
        common_upskilling_path TEXT,
        how_common INTEGER DEFAULT 0,
        PRIMARY KEY (from_role_id, to_role_id)
    )
    """
]

for cmd in commands:
    cur.execute(cmd)

conn.commit()
cur.close()
conn.close()
print("All tables created successfully.")