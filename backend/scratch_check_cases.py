import sqlite3

conn = sqlite3.connect('caseintel.db')
c = conn.cursor()

c.execute("SELECT id, case_number, incident_type, location FROM investigations")
invs = c.fetchall()

print(f"Total investigations: {len(invs)}")
for inv_id, cnum, itype, loc in invs:
    vids = c.execute("SELECT id, filename, status FROM videos WHERE investigation_id=?", (inv_id,)).fetchall()
    ents = c.execute("SELECT id, type, label FROM entities WHERE investigation_id=?", (inv_id,)).fetchall()
    evts = c.execute("SELECT id, action, entity_id, is_suspicious FROM events WHERE investigation_id=?", (inv_id,)).fetchall()
    evds = c.execute("SELECT id, type, primary_entity_id FROM evidence WHERE investigation_id=?", (inv_id,)).fetchall()
    print(f"\n--- {cnum} ({inv_id}) | Type: {itype} | Loc: {loc} ---")
    print(f"  Videos ({len(vids)}): {vids}")
    print(f"  Entities ({len(ents)}): {ents}")
    print(f"  Events ({len(evts)}): {evts}")
    print(f"  Evidence ({len(evds)}): {evds}")

conn.close()
