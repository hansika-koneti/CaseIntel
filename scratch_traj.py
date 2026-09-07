import sqlite3, json

conn = sqlite3.connect('backend/caseintel.db')
c = conn.cursor()
inv = c.execute("SELECT id FROM investigations WHERE case_number LIKE '%22725B%'").fetchone()
e = c.execute("SELECT metadata_json FROM entities WHERE investigation_id = ?", (inv[0],)).fetchone()
traj = json.loads(e[0])['trajectory']
for p in traj:
    print(p)
