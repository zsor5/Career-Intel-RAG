# Career Intel

An AI-powered career intelligence system that answers natural language questions about careers, salaries, job growth, and pivot paths — grounded in real government labor market data from O*NET and the Bureau of Labor Statistics.

---

## What it does

Ask any career question in plain English and get a data-backed answer with an automatically selected visualization:

- *"What industries pay software engineers the most?"*
- *"I'm a nurse — what adjacent healthcare roles have better pay and job security?"*
- *"What are the fastest growing jobs over the next 10 years?"*
- *"I want to pivot from teaching — show me salary tradeoffs and difficulty"*

Every response shows the generated SQL query so you can see exactly what data backed the answer. A clickable follow-up question appears after each response to continue the conversation.

---

## Architecture

```
User question → OpenAI embeddings → pgvector semantic search
                                          ↓
                          Claude generates SQL from schema + context
                          (transition queries use hardcoded SQL patterns)
                                          ↓
                          PostgreSQL query executes against BLS/O*NET data
                                          ↓
                          Claude interprets results → JSON with answer + follow-up
                          Claude selects visualization type
                                          ↓
                          React renders appropriate chart component
```

Hybrid retrieval combines vector search (semantic similarity) with structured SQL queries to handle questions neither approach can answer alone.

---

## Tech Stack

**Backend** — Python, FastAPI, PostgreSQL + pgvector (Neon), Anthropic Claude, OpenAI Embeddings

**Frontend** — React.js, Recharts, Axios

**Data** — O*NET bulk database, BLS OES salary data, BLS OES industry-specific data, BLS Employment Projections (2024–2034)

---

## Database

| Table | Contents |
|---|---|
| `roles` | 1,016 occupations with salaries, seniority, family, growth projections |
| `skills` | 35 skill categories |
| `role_skills` | 31,290 role-skill mappings with importance levels |
| `career_transitions` | 12,322 transition paths with salary delta and difficulty score |
| `role_education` | 4,223 education level breakdowns per role with percentages |
| `industries` | 62 industries from BLS OES |
| `role_industry` | 7,351 role-industry salary records showing pay differentials by sector |

---

## Visualizations

The system automatically selects the best chart type based on query intent:

| Query type | Visualization |
|---|---|
| Salary comparison across roles | Bar chart |
| Salary distribution | Range chart (p25 / median / p75) |
| Job recommendations | Ranked list with salary bars |
| Career pivot analysis | Scatter plot (transition difficulty vs salary delta) |
| Job growth / outlook | Color-coded bar chart by growth category |
| Industry salary differentials | Bar chart ranked by sector pay |
| Role comparison | Comparison table |

---

## Key Features

**Hybrid RAG pipeline** — vector embeddings find semantically relevant roles, SQL retrieves verified facts. Grounded in government data rather than LLM training knowledge.

**Text-to-SQL generation** — Claude generates PostgreSQL queries from natural language, with hardcoded fallback patterns for transition queries to ensure consistent results.

**Industry salary intelligence** — surfaces salary differentials across 62 industries so you can see what a role pays in finance vs healthcare vs energy.

**10-year job projections** — BLS 2024–2034 growth data with annual opening counts and growth category labels on every applicable role.

**Education breakdowns** — percentage of workers in each role by education level, enabling questions like "what well paying jobs don't require a degree."

**Career transition paths** — 12,322 derived transition paths with salary delta and difficulty scores, visualized as a scatter plot showing easy wins vs hard but lucrative pivots.

**Clickable follow-up questions** — each response generates a contextual follow-up question you can fire with one click.

---

## Setup

### Prerequisites
- Python 3.10+, Node.js 18+
- [Neon](https://neon.tech) account (free)
- [Anthropic](https://console.anthropic.com) API key
- [OpenAI](https://platform.openai.com) API key

### 1. Clone and install

```bash
git clone https://github.com/yourusername/career-intel.git
cd career-intel
python -m venv venv
source venv/bin/activate
pip install psycopg2-binary python-dotenv requests pandas anthropic openai fastapi uvicorn openpyxl
```

### 2. Configure environment

Create a `.env` file in the project root:

```
DATABASE_URL=postgresql://your-neon-connection-string
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

### 3. Load data

Download the following into your `data/` folder:
- **O*NET bulk data** → [onetcenter.org/database.html](https://www.onetcenter.org/database.html), unzip into `data/O_net_txt/`
- **BLS OES national salaries** → national Excel file from [bls.gov/oes/tables.htm](https://www.bls.gov/oes/tables.htm)
- **BLS OES industry salaries** → "National industry-specific" Excel file from the same page
- **BLS projections** → Excel file from [bls.gov/emp/tables](https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm)

Run the ingestion scripts in order:

```bash
python scripts/create_tables.py
python scripts/load_onet.py
python scripts/load_role_skills.py
python scripts/load_salaries.py
python scripts/load_projections.py
python scripts/load_education.py
python scripts/generate_embeddings.py
python scripts/load_transitions.py
python scripts/load_industries.py
```

Verify everything loaded:

```bash
python scripts/check_db.py
```

### 4. Run the app

In one terminal:
```bash
uvicorn main:app --reload
```

In another terminal:
```bash
cd frontend
npm install
npm start
```

Open **http://localhost:3000**

---

## License

MIT
