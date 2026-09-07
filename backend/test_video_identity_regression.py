"""
CaseIntel — Automated Video Identity & Detection Regression Test
Validates end-to-end video association, persistence, stream 1:1 mapping,
isolation between multiple uploads, and strict video_id propagation across entities/events.
"""

import os
import sys
import requests
import hashlib

BASE_URL = "http://127.0.0.1:8000"

VIDEO_A_PATH = "backend/uploads/vid-6e5c1814_3878245337-preview.mp4"
VIDEO_B_PATH = "backend/uploads/vid-a5ad7565_womans-encounter-with-intruder-at-home-SBV-306399481-preview.mp4"

def sha256_file(filepath):
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def test_pipeline():
    print("=== STARTING VIDEO IDENTITY REGRESSION TEST ===")
    assert os.path.exists(VIDEO_A_PATH), f"Missing {VIDEO_A_PATH}"
    assert os.path.exists(VIDEO_B_PATH), f"Missing {VIDEO_B_PATH}"

    sha_a = sha256_file(VIDEO_A_PATH)
    sha_b = sha256_file(VIDEO_B_PATH)
    print(f"Video A SHA-256: {sha_a[:16]}... (size: {os.path.getsize(VIDEO_A_PATH)} bytes)")
    print(f"Video B SHA-256: {sha_b[:16]}... (size: {os.path.getsize(VIDEO_B_PATH)} bytes)")
    assert sha_a != sha_b, "Test videos must be distinct!"

    # 1. Create a fresh investigation
    inv_res = requests.post(f"{BASE_URL}/api/investigations/", json={
        "case_number": f"CASE-REGRESS-{os.getpid()}",
        "incident_type": "Unclassified",
        "location": "Forensic Audit Lab",
        "severity": "MEDIUM",
        "status": "under_investigation",
        "video_count": 0,
        "confidence": 0.0,
        "investigator": "Forensic Auditor",
    })
    assert inv_res.status_code in (200, 201), f"Failed creating investigation: {inv_res.text}"
    inv_data = inv_res.json()
    inv_id = inv_data["id"]
    print(f"[Step 1] Created fresh investigation: {inv_id} ({inv_data['case_number']})")

    # 2. Upload Video A
    with open(VIDEO_A_PATH, "rb") as f:
        up_a_res = requests.post(f"{BASE_URL}/api/videos/upload", files={"file": ("video_a_preview.mp4", f, "video/mp4")}, data={
            "camera_id": "C-01",
            "location": "Forensic Audit Lab",
            "investigation_id": inv_id,
        })
    assert up_a_res.status_code == 200, f"Upload A failed: {up_a_res.text}"
    up_a_data = up_a_res.json()
    video_a_id = up_a_data["video_id"]
    print(f"[Step 2] Uploaded Video A -> returned video_id: {video_a_id}")

    # Analyze Video A
    an_a_res = requests.post(f"{BASE_URL}/api/videos/{video_a_id}/analyze")
    assert an_a_res.status_code == 200, f"Analyze A failed: {an_a_res.text}"
    an_a_data = an_a_res.json()
    assert an_a_data["video_id"] == video_a_id, f"Analysis video_id mismatch: {an_a_data['video_id']} != {video_a_id}"
    print(f"[Step 2] Analyzed Video A -> {len(an_a_data.get('entities', []))} entities, {len(an_a_data.get('events', []))} events")

    # Verify investigation active_video_id is Video A
    chk1 = requests.get(f"{BASE_URL}/api/investigations/{inv_id}").json()
    assert chk1["video_id"] == video_a_id, f"Expected video_id {video_a_id}, got {chk1['video_id']}"
    assert chk1["active_video_id"] == video_a_id, f"Expected active_video_id {video_a_id}, got {chk1['active_video_id']}"
    print(f"[Step 2 Verified] Investigation active_video_id is correctly Video A: {video_a_id}")

    # 3. Upload Video B to the SAME investigation
    with open(VIDEO_B_PATH, "rb") as f:
        up_b_res = requests.post(f"{BASE_URL}/api/videos/upload", files={"file": ("video_b_intruder.mp4", f, "video/mp4")}, data={
            "camera_id": "C-01",
            "location": "Forensic Audit Lab",
            "investigation_id": inv_id,
        })
    assert up_b_res.status_code == 200, f"Upload B failed: {up_b_res.text}"
    up_b_data = up_b_res.json()
    video_b_id = up_b_data["video_id"]
    print(f"[Step 3] Uploaded Video B -> returned video_id: {video_b_id}")
    assert video_b_id != video_a_id, "Video B id must be different from Video A id"

    # Analyze Video B
    an_b_res = requests.post(f"{BASE_URL}/api/videos/{video_b_id}/analyze")
    assert an_b_res.status_code == 200, f"Analyze B failed: {an_b_res.text}"
    an_b_data = an_b_res.json()
    assert an_b_data["video_id"] == video_b_id, f"Analysis video_id mismatch: {an_b_data['video_id']} != {video_b_id}"
    print(f"[Step 3] Analyzed Video B -> {len(an_b_data.get('entities', []))} entities, {len(an_b_data.get('events', []))} events")

    # Check that each entity and event in an_b_data retains video_id == video_b_id
    for ent in an_b_data.get("entities", []):
        assert ent.get("video_id") == video_b_id, f"Entity {ent['id']} has wrong video_id: {ent.get('video_id')} != {video_b_id}"
    for evt in an_b_data.get("events", []):
        assert evt.get("video_id") == video_b_id, f"Event {evt['id']} has wrong video_id: {evt.get('video_id')} != {video_b_id}"
    print(f"[Step 3 Verified] All entities and events strictly retain video_b_id: {video_b_id}")

    # 4. Verify Investigation state after Video B processing
    chk2 = requests.get(f"{BASE_URL}/api/investigations/{inv_id}").json()
    print(f"[Step 4] After Video B: active_video_id is {chk2['active_video_id']}, video_id is {chk2['video_id']}")
    assert chk2["video_id"] == video_b_id, f"CRITICAL: Displayed video must be Video B ({video_b_id}), but was {chk2['video_id']}!"
    assert chk2["active_video_id"] == video_b_id, f"CRITICAL: Active video must be Video B ({video_b_id}), but was {chk2['active_video_id']}!"
    assert chk2["video_count"] == 2, f"Expected 2 videos, got {chk2['video_count']}"

    # 5. Simulate Page Refresh (call GET investigation again)
    chk_refresh = requests.get(f"{BASE_URL}/api/investigations/{inv_id}").json()
    assert chk_refresh["video_id"] == video_b_id, f"After refresh: expected Video B, got {chk_refresh['video_id']}"
    assert chk_refresh["active_video_id"] == video_b_id, f"After refresh: expected Video B, got {chk_refresh['active_video_id']}"
    print(f"[Step 5 Verified] Page refresh still deterministically renders Video B: {video_b_id}")

    # 6. Verify Physical Stream Endpoints
    stream_b = requests.get(f"{BASE_URL}/api/videos/{video_b_id}/stream")
    assert stream_b.status_code == 200
    assert hashlib.sha256(stream_b.content).hexdigest() == sha_b, "Stream B content does not match physical Video B file!"
    assert stream_b.headers.get("X-Video-ID") == video_b_id
    print(f"[Step 6 Verified] Stream endpoint for Video B matches physical Video B SHA-256 and size ({len(stream_b.content)} bytes)")

    stream_a = requests.get(f"{BASE_URL}/api/videos/{video_a_id}/stream")
    assert stream_a.status_code == 200
    assert hashlib.sha256(stream_a.content).hexdigest() == sha_a, "Stream A content does not match physical Video A file!"
    assert stream_a.headers.get("X-Video-ID") == video_a_id
    print(f"[Step 6 Verified] Stream endpoint for Video A matches physical Video A SHA-256 and size ({len(stream_a.content)} bytes)")

    # Missing video stream returns explicit 404, never substitutes
    stream_404 = requests.get(f"{BASE_URL}/api/videos/vid-nonexistent/stream")
    assert stream_404.status_code == 404, f"Expected 404 for missing video, got {stream_404.status_code}"
    print(f"[Step 6 Verified] Missing video returns explicit 404: {stream_404.json()['detail']}")

    # 7. Test Explicit Video Switching
    switch_res = requests.post(f"{BASE_URL}/api/investigations/{inv_id}/set-active-video/{video_a_id}")
    assert switch_res.status_code == 200, f"Switch failed: {switch_res.text}"
    chk3 = requests.get(f"{BASE_URL}/api/investigations/{inv_id}").json()
    assert chk3["active_video_id"] == video_a_id, "Active video should have switched to Video A"
    print(f"[Step 7 Verified] Successfully switched active video to Video A: {video_a_id}")

    # Switch to nonexistent video must be rejected with 400
    bad_switch = requests.post(f"{BASE_URL}/api/investigations/{inv_id}/set-active-video/vid-foreign")
    assert bad_switch.status_code == 400, "Should reject foreign/nonexistent video ID"
    print(f"[Step 7 Verified] Foreign/invalid video switch rejected with 400: {bad_switch.json()['detail']}")

    print("\n>>> ALL REGRESSION CHECKS PASSED WITH 100% SUCCESS! <<<")

if __name__ == "__main__":
    test_pipeline()
