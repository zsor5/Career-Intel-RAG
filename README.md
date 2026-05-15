Setup
1. Clone the repo
bashgit clone https://github.com/yourusername/career-intel.git
cd career-intel
2. Set up Python environment
bashpython -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

pip install psycopg2-binary python-dotenv requests pandas anthropic openai fastapi uvicorn openpyxl
3. Configure environment variables
Create a .env file in the project root:
DATABASE_URL=postgresql://your-neon-connection-string
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
4. Set up the database
Create a free PostgreSQL database at neon.tech, then run:
bashpython scripts/create_tables.py
5. Load the data
O*NET bulk data — download from onetcenter.org/database.html, unzip into data/O_net_txt/
BLS salary data — download the national OES Excel file from bls.gov/oes/tables.htm into data/
BLS projections — download the occupational projections Excel file from bls.gov/emp/tables into data/
Then run the ingestion scripts in order:
bashpython scripts/load_onet.py
python scripts/load_role_skills.py
python scripts/load_salaries.py
python scripts/load_projections.py
python scripts/load_education.py
python scripts/generate_embeddings.py
python scripts/load_transitions.py
Verify everything loaded:
bashpython scripts/check_db.py
Expected output:
roles: 1016 rows
skills: 35 rows
role_skills: 31290 rows
career_transitions: 12322 rows
role_education: 4223 rows
6. Run the backend
bashuvicorn main:app --reload
Backend runs at http://localhost:8000. Visit http://localhost:8000/docs for the interactive API explorer.
7. Run the frontend
bashcd frontend
npm install
npm start
Frontend runs at http://localhost:3000.

Usage
Open http://localhost:3000 and ask any career question. Examples:

What are the fastest growing jobs over the next 10 years?
I'm a software engineer, what higher paying roles can I transition to?
Compare the salary ranges for data, engineering, and product roles
What healthcare jobs have the most openings and best job security?
What well paying jobs can I get without a college degree?
I know Python and statistics, what roles suit me?

Every response shows the generated SQL query so you can inspect exactly what data backed the answer.
