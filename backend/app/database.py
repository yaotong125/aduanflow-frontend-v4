import logging
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text
from backend.app.config import settings

logger = logging.getLogger("aduanflow")

def create_db_if_not_exists(url: str):
    """Attempt to create the database if it doesn't exist (MySQL dialect)."""
    if "mysql" in url:
        try:
            # Parse server base URL without database name
            base_url, db_name = url.rsplit("/", 1)
            db_name = db_name.split("?")[0]
            engine = create_engine(base_url, isolation_level="AUTOCOMMIT")
            with engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            logger.info(f"Verified/Created MySQL database `{db_name}`")
        except Exception as e:
            logger.warning(f"Could not auto-create MySQL database: {e}")

from sqlalchemy import event, text

# Build engine with automatic fallback to SQLite if remote DB is offline
from urllib.parse import quote_plus

db_url = settings.DATABASE_URL
if db_url:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+psycopg2://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

db_connect_error_msg = None

def create_db_engine(url_str: str):
    connect_args = {}
    is_sqlite = "sqlite" in url_str
    is_postgres = "postgresql" in url_str

    if is_postgres:
        if "sslmode" not in url_str:
            connect_args["sslmode"] = "require"

    kwargs = {
        "echo": False,
        "pool_pre_ping": True,
    }
    # SQLite uses StaticPool and does not support pool_size / max_overflow
    if not is_sqlite:
        kwargs["pool_size"] = 10
        kwargs["max_overflow"] = 20

    if connect_args:
        kwargs["connect_args"] = connect_args

    test_eng = create_engine(url_str, **kwargs)
    with test_eng.connect() as conn:
        conn.execute(text("SELECT 1"))
    return test_eng

try:
    if db_url and "mysql" in db_url:
        create_db_if_not_exists(db_url)

    engine = create_db_engine(db_url)
    logger.info("Connected to primary database server (Supabase/PostgreSQL/MySQL) successfully.")
except Exception as primary_e:
    db_connect_error_msg = f"{type(primary_e).__name__}: {str(primary_e)}"
    logger.warning(f"Direct DB connection failed ({primary_e}). Trying IPv4 Supabase Pooler fallback...")

    # Attempt automatic pooler rewrite for Supabase IPv4 compatibility
    fallback_success = False
    if db_url and "supabase.co" in db_url:
        try:
            import re
            ref_match = re.search(r'db\.([a-zA-Z0-9]+)\.supabase\.co', db_url)
            if ref_match:
                proj_ref = ref_match.group(1)
                pooler_url = db_url.replace(f"db.{proj_ref}.supabase.co:5432", "aws-0-ap-northeast-2.pooler.supabase.com:6543")
                pooler_url = pooler_url.replace(f"db.{proj_ref}.supabase.co", "aws-0-ap-northeast-2.pooler.supabase.com:6543")
                if "postgres:" in pooler_url and f"postgres.{proj_ref}:" not in pooler_url:
                    pooler_url = pooler_url.replace("postgres:", f"postgres.{proj_ref}:", 1)

                logger.info(f"Attempting Supabase IPv4 Pooler rewrite: {pooler_url}")
                engine = create_db_engine(pooler_url)
                fallback_success = True
                db_connect_error_msg = None
                logger.info("Connected to Supabase via IPv4 Pooler successfully!")
        except Exception as pooler_e:
            db_connect_error_msg = f"Direct: {primary_e} | Pooler: {pooler_e}"
            logger.error(f"Supabase IPv4 Pooler connection also failed: {pooler_e}")

    if not fallback_success:
        logger.warning("Using SQLite fallback with WAL concurrency (aduanflow.db).")
        sqlite_fallback = "sqlite:///./aduanflow.db"
        engine = create_engine(
            sqlite_fallback,
            connect_args={"check_same_thread": False, "timeout": 30}
        )

def get_db_error():
    return db_connect_error_msg

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in str(engine.url):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA busy_timeout=30000;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.close()
        except Exception:
            pass

def init_db():
    """Create all SQLModel tables."""
    from backend.app.models.case import Case
    from backend.app.models.audit import AuditLog
    from backend.app.models.settings import SystemSettings
    from backend.app.models.user import User
    SQLModel.metadata.create_all(engine)

def get_session():
    """Dependency for obtaining DB session."""
    with Session(engine) as session:
        yield session
