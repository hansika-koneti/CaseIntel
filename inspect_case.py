import sqlite3

conn = sqlite3.connect('backend/caseintel.db')
c = conn.cursor()
print('VIDEOS for inv-41771fb9:')
for r in c.execute("SELECT id, filename, uploaded_at, status FROM videos WHERE investigation_id = 'inv-41771fb9' ORDER BY uploaded_at ASC").fetchall():
    print(r)

print('\nENTITIES for inv-41771fb9:')
for r in c.execute("SELECT id, type, label, confidence, first_seen, last_seen, track_duration FROM entities WHERE investigation_id = 'inv-41771fb9'").fetchall():
    print(r)

print('\nEVENTS for inv-41771fb9:')
for r in c.execute("SELECT id, timestamp, action, entity_id, description FROM events WHERE investigation_id = 'inv-41771fb9'").fetchall():
    print(r)

print('\nINVESTIGATION:')
for r in c.execute("SELECT id, case_number, location, video_count, duration_analyzed, incident_type, confidence FROM investigations WHERE id = 'inv-41771fb9'").fetchall():
    print(r)

conn.close()
