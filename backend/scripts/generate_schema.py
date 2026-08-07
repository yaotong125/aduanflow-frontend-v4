import sys
import os
import pathlib
import io
from contextlib import redirect_stdout

# Add project root to pythonpath
project_root = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from sqlmodel import SQLModel
from sqlalchemy.dialects import postgresql
from sqlalchemy import create_mock_engine

# Import models to register them
from backend.app.models.case import Case
from backend.app.models.audit import AuditLog
from backend.app.models.settings import SystemSettings
from backend.app.models.user import User

def dump(sql, *multiparams, **params):
    compiled_sql = str(sql.compile(dialect=postgresql.dialect()))
    print(compiled_sql.strip())
    print(";\n")

def main():
    engine = create_mock_engine('postgresql://', dump)
    
    output_path = project_root / 'docs' / 'supabase_schema.sql'
    
    with open(output_path, 'w', encoding='utf-8') as f:
        with redirect_stdout(f):
            print("-- ==============================================================================")
            print("-- AduanFlow Supabase PostgreSQL Database Schema")
            print("-- ==============================================================================")
            print("-- ")
            print("-- Instructions:")
            print("-- 1. Open your Supabase Project Dashboard.")
            print("-- 2. Navigate to the \"SQL Editor\" on the left sidebar.")
            print("-- 3. Create a new query, paste the contents of this file, and click \"RUN\".")
            print("-- ")
            print("-- This schema accurately matches the SQLModel schema defined in the codebase.")
            print("-- ==============================================================================\n")
            
            SQLModel.metadata.create_all(engine, checkfirst=True)
            
    print(f"Schema written to {output_path}")

if __name__ == "__main__":
    main()
