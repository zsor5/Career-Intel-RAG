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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

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
    growth_outlook TEXT,
    projected_growth_pct FLOAT,
    projected_annual_openings INTEGER,
    projected_growth_category TEXT,
    education_typical TEXT
)
skills (
    skill_id TEXT,
    name TEXT,
    category TEXT
)
role_skills (
    role_id TEXT,
    skill_id TEXT,
    importance TEXT
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

def is_transition_query(question):
    keywords = ["pivot", "transition", "switch", "move into", "change career",
                "change to", "move to", "get into", "break into", "tradeoff",
                "trade off", "difficulty", "salary tradeoff", "looking to pivot"]
    return any(k in question.lower() for k in keywords)

def generate_transition_sql(question, similar_roles):
    titles = [r[0] for r in similar_roles[:6]]
    titles_str = ", ".join([f"'{t}'" for t in titles])

    return f"""
SELECT
    r1.title as current_role,
    r2.title as potential_role,
    r1.avg_salary_usd as current_salary,
    r2.avg_salary_usd as new_salary,
    ct.avg_salary_delta,
    ct.transition_difficulty,
    ct.how_common
FROM career_transitions ct
JOIN roles r1 ON ct.from_role_id = r1.role_id
JOIN roles r2 ON ct.to_role_id = r2.role_id
WHERE r1.title IN ({titles_str})
ORDER BY ct.avg_salary_delta DESC
LIMIT 15
"""

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
- For growth or job security questions always include projected_growth_pct, projected_annual_openings, projected_growth_category
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
    col_set = set(columns)

    prompt = f"""Given this user question: "{question}"
Result columns available: {list(col_set)}
Number of results: {len(results)}

Choose the single best visualization from this list:

- bar_chart: comparing salaries across multiple roles (needs avg_salary_usd, 3+ results)
- salary_range_chart: showing salary spread when p25/p75 data available (needs salary_p25 AND salary_p75)
- ranked_list: top N job recommendations (best for 'what jobs suit me' questions)
- transition_table: career pivot questions with salary delta and difficulty (needs avg_salary_delta)
- growth_chart: job security, projections, fastest growing roles (needs projected_growth_pct OR projected_annual_openings)
- scatter_chart: comparing two dimensions like difficulty vs salary delta (needs avg_salary_delta AND transition_difficulty)
- comparison_table: side by side role comparison (best for 2-4 roles being directly compared)
- stat_cards: single role lookup or only 1-3 results

Rules:
- If question mentions 'growth', 'future', 'projections', 'job security', 'outlook', 'growing' → growth_chart
- If question mentions 'pivot', 'transition', 'switch', 'move into', 'tradeoff', 'difficulty' → scatter_chart if transition_difficulty exists, else transition_table
- If salary_p25 and salary_p75 both exist → prefer salary_range_chart over bar_chart
- Never pick ranked_list if better columns exist for a more specific chart
- Only pick stat_cards if fewer than 3 results

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
def query(req: QueryRequest):
    conn = get_db()
    cur = conn.cursor()

    try:
        # Step 1: semantic search
        embedding = get_embedding(req.question)
        similar_roles = semantic_search(embedding, cur)

        # Step 2: generate and run SQL
        if is_transition_query(req.question):
            sql = generate_transition_sql(req.question, similar_roles)
        else:
            sql = generate_sql(req.question, similar_roles, cur)

        cur.execute(sql)
        results = cur.fetchall()
        columns = [desc[0] for desc in cur.description]

        # Step 3: serialize results
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
        viz_hint = get_viz_hint(req.question, results, columns)
        answer = interpret_results(req.question, sql, results, columns)

        return QueryResponse(
            answer=answer,
            sql=sql,
            results=serialized,
            viz_hint=viz_hint,
            columns=columns
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()