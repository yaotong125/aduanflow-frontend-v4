import psycopg2

refs = ['wuxffgyqvvhvleil', 'wuxffgyqvvhvleiliecs']
regions = ['ap-southeast-1', 'us-east-1', 'us-west-1', 'eu-central-1', 'sa-east-1', 'ap-northeast-1']
passw = 'Donaldtrumplol123!'

print("--- TESTING SUPABASE POOLER REGIONS & REFS ---")
for r in refs:
    for reg in regions:
        url = f"postgresql://postgres.{r}:{passw}@aws-0-{reg}.pooler.supabase.com:6543/postgres?sslmode=require"
        try:
            conn = psycopg2.connect(url, connect_timeout=3)
            print(f"\n🎉 SUCCESSFUL MATCH FOUND! 🎉")
            print(f"DATABASE_URL: {url}\n")
            conn.close()
            break
        except Exception as e:
            err_str = str(e).splitlines()[0]
            print(f"[{r} | {reg}] Error: {err_str}")
