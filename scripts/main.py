from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import anthropic
import openai
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# CORS — allows your React frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Clients
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# Request/response models
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    sql: str
    results: list
    viz_hint: str
    columns: list

SCHEMA = """
roles (
    role_id TEXT,
    title TEXT,
    seniority_level TEXT,       -- 'entry', 'mid', 'senior', 'leadership'
    family TEXT,                -- 'engineering', 'data', 'product', 'design', 'business', 'healthcare', 'other'
    description TEXT,
    avg_salary_usd INTEGER,
    salary_p25 INTEGER,
    salary_p75 INTEGER,
    remote_friendly BOOLEAN,
    growth_outlook TEXT
)
skills (
    skill_id TEXT,
    name TEXT,
    category TEXT
)
role_skills (
    role_id TEXT,
    skill_id TEXT,
    importance TEXT             -- 'required', 'preferred', 'nice-to-have'
)
career_transitions (
    from_role_id TEXT,
    to_role_id TEXT,
    avg_salary_delta INTEGER,
    transition_difficulty INTEGER,
    common_upskilling_path TEXT,
    how_common INTEGER
)
"""

def get_embedding(text):
    response = openai_client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def semantic_search(embedding, cur, limit=8):
    cur.execute("""
        SELECT title, role_id, avg_salary_usd,
               1 - (description_vec <=> %s::vector) AS similarity
        FROM roles
        WHERE description_vec IS NOT NULL
        ORDER BY description_vec <=> %s::vector
        LIMIT %s
    """, (embedding, embedding, limit))
    return cur.fetchall()

def generate_sql(question, similar_roles, cur):
    similar_titles = ", ".join([f"'{r[0]}'" for r in similar_roles[:5]])
    cur.execute("SELECT DISTINCT name FROM skills ORDER BY name")
    actual_skills = [row[0] for row in cur.fetchall()]
    skills_list = ", ".join(actual_skills)

    prompt = f"""You are a SQL expert. Given this database schema:
{SCHEMA}

The actual skill names in the skills table are: {skills_list}

The user asked: "{question}"

Semantic search found these relevant roles: {similar_titles}

Write a single PostgreSQL SELECT query to answer the question.
Rules:
- Only SELECT statements, never INSERT/UPDATE/DELETE
- Only filter on skill names from the list above
- If user mentions technical skills not in the list, rely on the semantic roles instead
- Never JOIN to role_skills or skills tables unless absolutely necessary
- Always include title and avg_salary_usd in results
- For transition questions, join career_transitions to get salary delta and difficulty
- Limit to 15 rows max
- Return ONLY the SQL query, no explanation, no markdown, no backticks

SQL:"""

    message = anthropic_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()

def get_viz_hint(question, results, columns):
    prompt = f"""Given this user question: "{question}"
And these result columns: {columns}
And {len(results)} rows of data returned.

Choose the single best visualization type from this list:
- bar_chart: for comparing salaries or counts across multiple roles
- ranked_list: for showing top N recommended jobs
- transition_table: for career pivot/transition questions showing from/to roles with salary delta
- comparison_table: for side by side comparison of a few roles
- stat_cards: for when there are only 1-3 results to highlight

Reply with ONLY the visualization type, nothing else."""

    message = anthropic_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=20,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()

def interpret_results(question, sql, results, columns):
    results_text = "\n".join([
        str(dict(zip(columns, row))) for row in results[:10]
    ])

    prompt = f"""A user asked: "{question}"

We ran this SQL: {sql}

Results: {results_text}

Give a clear 2-3 sentence answer using specific job titles and salary figures from the results.
Then suggest one relevant follow-up question they might want to ask.
Be concise and specific."""

    message = anthropic_client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text.strip()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    conn = get_db()
    cur = conn.cursor()

    try:
        # Step 1: semantic search
        embedding = get_embedding(request.question)
        similar_roles = semantic_search(embedding, cur)

        # Step 2: generate and run SQL
        sql = generate_sql(request.question, similar_roles, cur)
        cur.execute(sql)
        results = cur.fetchall()
        columns = [desc[0] for desc in cur.description]

        # Step 3: serialize results (convert to JSON-safe types)
        serialized = []
        for row in results:
            serialized_row = {}
            for col, val in zip(columns, row):
                if hasattr(val, 'isoformat'):
                    serialized_row[col] = val.isoformat()
                elif val is None:
                    serialized_row[col] = None
                else:
                    serialized_row[col] = val
            serialized.append(serialized_row)

        # Step 4: viz hint + interpretation
        viz_hint = get_viz_hint(request.question, results, columns)
        answer = interpret_results(request.question, sql, results, columns)

        return QueryResponse(
            answer=answer,
            sql=sql,
            results=serialized,
            viz_hint=viz_hint,
            columns=columns
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()