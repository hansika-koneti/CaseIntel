import sqlite3, json

conn = sqlite3.connect('backend/caseintel.db')
c = conn.cursor()
inv = c.execute("SELECT id, case_number, location, video_count, incident_data FROM investigations WHERE case_number LIKE '%22725B%'").fetchone()
print("INV:", inv)
if inv:
    ents = c.execute("SELECT id, type, label, confidence, first_seen, last_seen, metadata_json FROM entities WHERE investigation_id = ?", (inv[0],)).fetchall()
    print("ENTS:")
    for e in ents:
        meta = json.loads(e[6]) if e[6] else {}
        traj = meta.get('trajectory', [])
        print(e[0], e[1], e[3], e[4], e[5], f"traj_len={len(traj)}")
        if traj:
            print("First 5 traj points:", traj[:5])
            print("Last 5 traj points:", traj[-5:])
    
    events = c.execute("SELECT id, timestamp, action, confidence, description FROM events WHERE investigation_id = ?", (inv[0],)).fetchall()
    print("EVENTS:")
    for ev in events:
        print(ev)

    vids = c.execute("SELECT id, filename, filepath, location FROM videos WHERE investigation_id = ?", (inv[0],)).fetchall()
    print("VIDEOS:")
    for v in vids:
        print(v)
