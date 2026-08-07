import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Load .env at module import time so every entrypoint (uvicorn, MCP, scripts)
# picks up DATABASE_URL and credentials regardless of import order.
_env_candidates = [
    Path(__file__).resolve().parents[2] / ".env",   # backend/.env
    Path(__file__).resolve().parents[3] / ".env",   # project root /.env
]
for _env_path in _env_candidates:
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path)
        break

class Settings(BaseModel):
    PROJECT_NAME: str = "AduanFlow AI Backend"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api"
    
    # Database connection URL - defaults to local XAMPP MySQL or SQLite fallback
    # For TencentDB VPC deployment: set DATABASE_URL in .env to mysql+pymysql://<user>:<pass>@10.0.0.7:3306/aduanflow
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "mysql+pymysql://root:@127.0.0.1:3306/aduanflow"
    )
    
    # Secret key for field-level Fernet encryption
    ENCRYPTION_KEY: str = os.getenv(
        "ENCRYPTION_KEY", 
        "4_pZk1y0XzL_7p2N4aW-q9x6B3v8C1m5K0j7R2u4V8w=" # Default dev key
    )

settings = Settings()
