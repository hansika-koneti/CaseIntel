import sqlite3

conn = sqlite3.connect('backend/caseintel.db')
c = conn.cursor()

# 1. Update evidence primary_entity_id
c.execute("UPDATE evidence SET primary_entity_id = 'Person-77' WHERE id = 'EVD-6450' AND primary_entity_id = 'Tv-74'")
print(f"Updated EVD-6450 Tv-74 -> Person-77: {c.rowcount} rows")

c.execute("UPDATE evidence SET primary_entity_id = 'Person-01' WHERE id = 'EVD-1307' AND primary_entity_id = 'Person-08'")
print(f"Updated EVD-1307 Person-08 -> Person-01: {c.rowcount} rows")

# 2. Insert Person-01 for inv-a25b62a1 if not exists
c.execute("SELECT id FROM entities WHERE investigation_id = 'inv-a25b62a1'")
existing_entity = c.fetchone()
if not existing_entity:
    c.execute("""
        INSERT INTO entities (id, investigation_id, type, label, confidence, first_seen, last_seen, track_duration, metadata_json)
        VALUES ('inv-a25b62a1:Person-01', 'inv-a25b62a1', 'person', 'Person-01', 71.8, '00:06', '00:16', '10.0s', '{}')
    """)
    print("Inserted missing entity inv-a25b62a1:Person-01")
else:
    print(f"Entity already exists for inv-a25b62a1: {existing_entity}")

# 3. Synchronize event locations to match investigation location
c.execute("UPDATE events SET location = 'house' WHERE investigation_id = 'inv-a25b62a1' AND (location IS NULL OR location = 'Location not specified' OR location = 'undefined')")
print(f"Updated inv-a25b62a1 event locations: {c.rowcount}")

c.execute("UPDATE events SET location = 'newplace' WHERE investigation_id = 'inv-41771fb9' AND (location IS NULL OR location = 'Location not specified' OR location = 'undefined')")
print(f"Updated inv-41771fb9 event locations: {c.rowcount}")

c.execute("UPDATE events SET location = 'Monitored Zone' WHERE investigation_id = 'inv-6022725b' AND (location IS NULL OR location = 'Location not specified' OR location = 'undefined')")
print(f"Updated inv-6022725b event locations: {c.rowcount}")

c.execute("UPDATE events SET location = 'Research Lab 2' WHERE investigation_id = 'inv-1bfcb9bc' AND (location IS NULL OR location = 'Location not specified' OR location = 'undefined')")
print(f"Updated inv-1bfcb9bc event locations: {c.rowcount}")

conn.commit()
conn.close()
print("Database cleanup completed successfully.")
