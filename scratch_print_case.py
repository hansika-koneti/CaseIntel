import sqlite3
conn = sqlite3.connect('backend/caseintel.db')
c = conn.cursor()
row = c.execute("SELECT id, case_number, location, video_count FROM investigations WHERE case_number LIKE '%22725B%'").fetchone()
print("CASE:", row)
