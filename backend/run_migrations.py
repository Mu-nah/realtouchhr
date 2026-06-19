"""
Run this script once to apply / update the Supabase schema.

Usage:
    cd backend
    python run_migrations.py

Requires DATABASE_URL in backend/.env (direct PostgreSQL connection string).
Get it from Supabase → Settings → Database → Connection string (URI mode).
Add it to backend/.env as:
    DATABASE_URL=postgresql://postgres.[ref]:[password]@aws-0-eu-west-2.pooler.supabase.com:5432/postgres
"""
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent
from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL", "")
SCHEMA_FILE = ROOT_DIR / "supabase_schema.sql"

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in backend/.env")
    print("Get it from Supabase → Settings → Database → Connection string (URI mode)")
    sys.exit(1)

if not SCHEMA_FILE.exists():
    print(f"ERROR: Schema file not found: {SCHEMA_FILE}")
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print("Installing psycopg2-binary...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2

sql = SCHEMA_FILE.read_text(encoding="utf-8")

print(f"Connecting to database...")
conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()

# Split on statement-ending semicolons (simple split; comments handled by PostgreSQL)
statements = [s.strip() for s in sql.split(";") if s.strip()]
ok = 0
failed = 0
for stmt in statements:
    try:
        cur.execute(stmt)
        ok += 1
    except Exception as e:
        msg = str(e).strip()
        if "already exists" in msg or "does not exist" in msg:
            ok += 1  # idempotent
        else:
            print(f"  WARNING: {msg[:120]}")
            failed += 1

cur.close()
conn.close()

print(f"\nMigration complete: {ok} statements OK, {failed} warnings")
if failed == 0:
    print("All tables are up to date.")
