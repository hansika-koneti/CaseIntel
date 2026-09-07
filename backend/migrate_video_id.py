import sqlite3

def run_migration():
    conn = sqlite3.connect('backend/caseintel.db')
    c = conn.cursor()

    # 1. Add active_video_id to investigations
    cols = [col[1] for col in c.execute('PRAGMA table_info(investigations)').fetchall()]
    if 'active_video_id' not in cols:
        c.execute('ALTER TABLE investigations ADD COLUMN active_video_id VARCHAR(64)')
        print('Added active_video_id to investigations')

    # 2. Add video_id to entities
    cols = [col[1] for col in c.execute('PRAGMA table_info(entities)').fetchall()]
    if 'video_id' not in cols:
        c.execute('ALTER TABLE entities ADD COLUMN video_id VARCHAR(64)')
        print('Added video_id to entities')

    # 3. Add video_id to events
    cols = [col[1] for col in c.execute('PRAGMA table_info(events)').fetchall()]
    if 'video_id' not in cols:
        c.execute('ALTER TABLE events ADD COLUMN video_id VARCHAR(64)')
        print('Added video_id to events')

    # 4. Add video_id to evidence
    cols = [col[1] for col in c.execute('PRAGMA table_info(evidence)').fetchall()]
    if 'video_id' not in cols:
        c.execute('ALTER TABLE evidence ADD COLUMN video_id VARCHAR(64)')
        print('Added video_id to evidence')

    # 5. Backfill inv-41771fb9 with its analyzed video vid-a5ad7565
    c.execute("UPDATE investigations SET active_video_id = 'vid-a5ad7565' WHERE id = 'inv-41771fb9'")
    c.execute("UPDATE entities SET video_id = 'vid-a5ad7565' WHERE investigation_id = 'inv-41771fb9'")
    c.execute("UPDATE events SET video_id = 'vid-a5ad7565' WHERE investigation_id = 'inv-41771fb9'")
    c.execute("UPDATE evidence SET video_id = 'vid-a5ad7565' WHERE investigation_id = 'inv-41771fb9'")

    conn.commit()
    conn.close()
    print('Database migration complete!')

if __name__ == '__main__':
    run_migration()
