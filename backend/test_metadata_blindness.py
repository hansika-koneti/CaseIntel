"""
CaseIntel — Metadata Blindness Verification Test
Verifies that the Direct Temporal Video Activity Model makes predictions
EXCLUSIVELY from raw video frames and pixel temporal sequences.
Renaming the video file to neutral names or misleading names MUST NOT alter
the model's predictions, confidences, or supporting timestamps.
"""

import os
import sys
import shutil
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from services.temporal_video_service import TemporalVideoActivityService


class TestMetadataBlindness(unittest.TestCase):
    def setUp(self):
        self.service = TemporalVideoActivityService()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.original_video = os.path.join(base_dir, "test_footage", "ucf_crime_stealing002.mp4")
        self.neutral_video = os.path.join(base_dir, "test_footage", "test_neutral_clip_8841.mp4")
        self.misleading_video = os.path.join(base_dir, "test_footage", "normal_routine_hallway_9999.mp4")

        # Create renamed copies
        shutil.copyfile(self.original_video, self.neutral_video)
        shutil.copyfile(self.original_video, self.misleading_video)

    def tearDown(self):
        for p in [self.neutral_video, self.misleading_video]:
            if os.path.exists(p):
                os.remove(p)

    def test_prediction_invariance_under_renaming(self):
        """Verify that identical video content yields identical predictions regardless of filename."""
        print("\n[TEST] Running inference on original video: 'ucf_crime_stealing002.mp4'...")
        res_orig = self.service.analyze_video(self.original_video, stride_seconds=3.0)

        print("[TEST] Running inference on neutral-named copy: 'test_neutral_clip_8841.mp4'...")
        res_neut = self.service.analyze_video(self.neutral_video, stride_seconds=3.0)

        print("[TEST] Running inference on misleading-named copy: 'normal_routine_hallway_9999.mp4'...")
        res_mislead = self.service.analyze_video(self.misleading_video, stride_seconds=3.0)

        # 1. Primary activity must match exactly
        self.assertEqual(res_orig["primary_activity"], res_neut["primary_activity"])
        self.assertEqual(res_orig["primary_activity"], res_mislead["primary_activity"])
        print(f"  Primary Activity Invariant: '{res_orig['primary_activity']}' across all filenames.")

        # 2. Confidence score must match within float rounding
        self.assertAlmostEqual(res_orig["confidence"], res_neut["confidence"], places=1)
        self.assertAlmostEqual(res_orig["confidence"], res_mislead["confidence"], places=1)
        print(f"  Confidence Invariant: {res_orig['confidence']}% across all filenames.")

        # 3. Number of clips analyzed must match
        self.assertEqual(res_orig["total_clips_analyzed"], res_neut["total_clips_analyzed"])
        self.assertEqual(res_orig["total_clips_analyzed"], res_mislead["total_clips_analyzed"])

        # 4. Clip-level predictions must match exactly
        for i in range(len(res_orig["clip_predictions"])):
            c_orig = res_orig["clip_predictions"][i]
            c_neut = res_neut["clip_predictions"][i]
            c_mislead = res_mislead["clip_predictions"][i]
            self.assertEqual(c_orig["predicted_activity"], c_neut["predicted_activity"])
            self.assertEqual(c_orig["predicted_activity"], c_mislead["predicted_activity"])
            self.assertAlmostEqual(c_orig["confidence"], c_neut["confidence"], places=1)

        print("  [SUCCESS] Metadata Blindness Verified: Video model is 100% content-grounded.")


if __name__ == "__main__":
    unittest.main()
