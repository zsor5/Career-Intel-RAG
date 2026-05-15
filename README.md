# Career Intel

An AI-powered career intelligence system that answers natural language questions about careers, salaries, job growth, and pivot paths — grounded in real government labor market data from O*NET and the Bureau of Labor Statistics.

---

## What it does

Ask any career question in plain English and get a data-backed answer with an auto-selected visualization:

- *"What are the fastest growing jobs over the next 10 years?"*
- *"I'm a software engineer — what higher paying roles can I transition to?"*
- *"What healthcare jobs have the most openings and best job security?"*
- *"What well paying jobs don't require a college degree?"*

Every response shows the generated SQL query so you can see exactly what data backed the answer.

---

## Architecture

```
User question → OpenAI embeddings → pgvector semantic search
                                          ↓
                          Claude generates SQL from schema + context
                                          ↓
                          PostgreSQL query executes against BLS/O*NET data
                                          ↓
                          Claude interprets results → answer + visualization
```

Hybrid retrieval combines vector search (semantic similarity) with SQL (structured facts) to handle questions neither approach can answer alone.

---

## Tech Stack

**Backend** — Python, FastAPI, PostgreSQL + pgvector (Neon), Anthropic Claude, OpenAI Embeddings

**Frontend** — React.js, Recharts, Axios

**Data** — O*NET bulk database, BLS OES salary data, BLS Employment Projections (2024–2034)

---

## Database

| Table | Contents |
|---|---|
| `roles` | 1,016 occupations with salaries, growth projections, seniority |
| `skills` | 35 skill categories |
| `role_skills` | 31,290 role-skill mappings with importance levels |
| `career_transitions` | 12,322 transition paths with salary delta and difficulty |
| `role_education` | Education level breakdowns per role |

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
- **BLS OES salaries** → national Excel file from [bls.gov/oes/tables.htm](https://www.bls.gov/oes/tables.htm)
- **BLS projections** → Excel file from [bls.gov/emp/tables](https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm)

Then run the ingestion scripts in order:

```bash
python scripts/create_tables.py
python scripts/load_onet.py
python scripts/load_role_skills.py
python scripts/load_salaries.py
python scripts/load_projections.py
python scripts/load_education.py
python scripts/generate_embeddings.py
python scripts/load_transitions.py
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
