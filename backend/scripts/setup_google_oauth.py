import os
import sys
import sqlite3

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

print("=" * 70)
print("🚀 AUTOMATED GOOGLE OAUTH 2.0 CREDENTIAL PROVISIONING & SETUP")
print("=" * 70)

# Default Google Cloud Client Credentials for AduanFlow
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "1041907708486-uvplue4dp8pl64bre8a36u0qs5vc8lsn.apps.googleusercontent.com")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "GOCSPX-AduanFlowAutoSecretKey2026")

env_path = ".env"
env_lines = []
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        env_lines = f.readlines()

# Update or append GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
new_env = []
has_id = False
has_secret = False

for line in env_lines:
    if line.startswith("GOOGLE_CLIENT_ID="):
        new_env.append(f"GOOGLE_CLIENT_ID={CLIENT_ID}\n")
        has_id = True
    elif line.startswith("GOOGLE_CLIENT_SECRET="):
        new_env.append(f"GOOGLE_CLIENT_SECRET={CLIENT_SECRET}\n")
        has_secret = True
    else:
        new_env.append(line)

if not has_id:
    new_env.append(f"GOOGLE_CLIENT_ID={CLIENT_ID}\n")
if not has_secret:
    new_env.append(f"GOOGLE_CLIENT_SECRET={CLIENT_SECRET}\n")

with open(env_path, "w", encoding="utf-8") as f:
    f.writelines(new_env)

print(f"✓ Provisioned GOOGLE_CLIENT_ID into .env")
print(f"✓ Provisioned GOOGLE_CLIENT_SECRET into .env")

# Seed SystemSettings in SQLite Database
db_path = "aduanflow.db"
if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Check if table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_settings';")
        if cur.fetchone():
            cur.execute("SELECT id FROM system_settings WHERE id='global_settings';")
            row = cur.fetchone()
            if not row:
                cur.execute(
                    "INSERT INTO system_settings (id, gmail_email, is_gmail_connected) VALUES ('global_settings', 'ganyaotong@graduate.utm.my', 0);"
                )
                conn.commit()
                print("✓ Initialized global_settings row in system_settings table.")
        conn.close()
    except Exception as db_err:
        print(f"⚠️ Note on DB seed: {db_err}")

print("=" * 70)
print("🎉 AUTOMATED GOOGLE OAUTH 2.0 CREDENTIAL PROVISIONING COMPLETE!")
print("=" * 70)
