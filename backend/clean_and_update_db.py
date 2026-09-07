"""
CaseIntel — Database Cleanup & Trajectory Re-sync Script
1. Purge legacy demo seed records (inv-001, inv-002, inv-003).
2. Reset any hardcoded Parking Area locations to 'Location not specified'.
3. Re-process real YOLO trajectory for Person-01 with full [x, y, w, h] boxes.
"""

import os
import sys
import json
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "caseintel.db")

def cleanup_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Delete legacy demo investigations and related children
    demo_ids = ['inv-001', 'inv-002', 'inv-003']
    for did in demo_ids:
        cursor.execute("DELETE FROM events WHERE investigation_id = ?", (did,))
        cursor.execute("DELETE FROM entities WHERE investigation_id = ?", (did,))
        cursor.execute("DELETE FROM evidence WHERE investigation_id = ?", (did,))
        cursor.execute("DELETE FROM videos WHERE investigation_id = ?", (did,))
        cursor.execute("DELETE FROM investigations WHERE id = ?", (did,))
    print(f"[Cleanup] Deleted seed demo investigations {demo_ids}")

    # 2. Purge demo locations
    cursor.execute("DELETE FROM locations WHERE id IN ('LOC-PARK-A', 'LOC-SRV-3', 'LOC-LOBBY')")

    # 3. Clean up any occurrences of "Parking Area — Block B, Sector 14" in investigations and videos
    cursor.execute("""
        UPDATE investigations
        SET location = 'Location not specified'
        WHERE location LIKE '%Parking Area%' OR location LIKE '%Block B%'
    """)
    cursor.execute("""
        UPDATE videos
        SET location = 'Location not specified'
        WHERE location LIKE '%Parking Area%' OR location LIKE '%Block B%'
    """)
    cursor.execute("""
        UPDATE events
        SET location = 'Location not specified'
        WHERE location LIKE '%Parking Area%' OR location LIKE '%Block B%'
    """)

    # 4. Correct video_counts across all remaining investigations
    cursor.execute("SELECT id FROM investigations")
    all_invs = [r[0] for r in cursor.fetchall()]
    for iid in all_invs:
        cursor.execute("SELECT COUNT(*) FROM videos WHERE investigation_id = ?", (iid,))
        cnt = cursor.fetchone()[0]
        cursor.execute("UPDATE investigations SET video_count = ? WHERE id = ?", (cnt, iid))

    conn.commit()

    # 5. Re-run YOLO detection with full (x, y, w, h) for the active user video
    from services.yolo_service import YOLOv11DetectorService
    yolo = YOLOv11DetectorService()

    # Find the indoor video
    cursor.execute("SELECT id, filepath, investigation_id FROM videos WHERE filename LIKE '%3878245337%'")
    indoor_videos = cursor.fetchall()

    for vid_id, fpath, inv_id in indoor_videos:
        if os.path.exists(fpath):
            print(f"[YOLO] Processing video {fpath} for investigation {inv_id}...")
            res = yolo.process_video(fpath, sample_fps=4.0, conf_thresh=0.25)

            if res.get("valid") and res.get("tracks"):
                for track in res["tracks"]:
                    ent_id = track["entity_id"]
                    cls_name = track["class"]
                    traj = track["trajectory"]
                    print(f"  Track {ent_id} ({cls_name}): {len(traj)} observations with full bbox [x,y,w,h]")

                    # Update Entity in database
                    meta = {"trajectory": traj, "class": cls_name, "trajectory_points": len(traj)}
                    cursor.execute("""
                        UPDATE entities
                        SET metadata_json = ?, confidence = ?
                        WHERE id = ? AND investigation_id = ?
                    """, (json.dumps(meta), round(track.get("avg_confidence", 0.85) * 100, 1), ent_id, inv_id))

    conn.commit()
    conn.close()
    print("[Success] Database cleanup and trajectory re-sync complete.")

if __name__ == "__main__":
    cleanup_db()
