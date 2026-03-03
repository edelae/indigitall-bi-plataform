"""Query analytics tables - temporary script for verification."""
import psycopg2
import sys

conn = psycopg2.connect(
    host='localhost', port=5432, dbname='postgres',
    user='postgres', password='5hOnuj-FDb4V9D5Lk3LUrSuSUGgDS8k8'
)
cur = conn.cursor()

query = sys.argv[1] if len(sys.argv) > 1 else "SELECT 1"

cur.execute(query)
if cur.description:
    cols = [d[0] for d in cur.description]
    print(" | ".join(cols))
    print("-" * (len(" | ".join(cols))))
    for row in cur.fetchall():
        print(" | ".join(str(v) for v in row))

cur.close()
conn.close()
