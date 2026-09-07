"""
CaseIntel — EasyOCR Timestamp & Text Extraction Service
Extracts embedded CCTV timestamps, camera tags, and on-screen display (OSD) text
from video frames using EasyOCR. Transparently reports when no embedded timestamp
is found rather than fabricating timestamps.
"""

import os
import re
import cv2
from typing import Dict, Any, List, Optional

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False


class EasyOCRService:
    """Production EasyOCR service for CCTV on-screen timestamp and text extraction."""

    def __init__(self, languages: Optional[List[str]] = None, gpu: bool = False):
        self.languages = languages or ["en"]
        self.gpu = gpu
        self.reader = None
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._init_reader()

    def _init_reader(self):
        """Lazy-initialize EasyOCR reader."""
        if not EASYOCR_AVAILABLE:
            print("[EasyOCRService] Notice: 'easyocr' library not available.")
            return

        try:
            self.reader = easyocr.Reader(self.languages, gpu=self.gpu)
            print("[EasyOCRService] Successfully initialized EasyOCR reader.")
        except Exception as e:
            print(f"[EasyOCRService] Notice: Could not initialize EasyOCR reader ({e}).")
            self.reader = None

    def extract_timestamp_and_text(
        self,
        video_path: str,
        sample_frame_indices: Optional[List[int]] = None,
        max_sample_frames: int = 4,
    ) -> Dict[str, Any]:
        """
        Inspect video footage frames for embedded CCTV timestamps and OSD text.
        Crops top 18% and bottom 18% of frames where CCTV recorders burn in timestamps.
        If readable timestamps are found, returns the extracted string and ISO format.
        If none are found, reports 'Embedded timestamp not detected' transparently.
        """
        if video_path in self._cache:
            return self._cache[video_path]

        if not os.path.exists(video_path):
            return {
                "detected": False,
                "status": "Video file not found",
                "timestamp": None,
                "text_lines": [],
                "engine": "EasyOCR" if EASYOCR_AVAILABLE else "Unavailable",
                "fallback": "Video frame timing (MM:SS)",
            }

        if not self.reader:
            self._init_reader()

        if not self.reader:
            res = {
                "detected": False,
                "status": "Embedded timestamp not detected (OCR engine offline)",
                "timestamp": None,
                "text_lines": [],
                "engine": "Unavailable",
                "fallback": "Video frame timing (MM:SS)",
            }
            self._cache[video_path] = res
            return res

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {
                "detected": False,
                "status": "Failed to open video file",
                "timestamp": None,
                "text_lines": [],
                "engine": "EasyOCR",
                "fallback": "Video frame timing (MM:SS)",
            }

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

        if not sample_frame_indices:
            # Sample first frame, middle, and a couple intermediate frames
            step = max(1, total_frames // (max_sample_frames + 1))
            sample_frame_indices = [i * step for i in range(1, max_sample_frames + 1)]
            sample_frame_indices.insert(0, 0)

        all_detected_text: List[str] = []
        found_timestamp: Optional[str] = None
        timestamp_conf: float = 0.0

        # Regex patterns for CCTV timestamps
        ts_patterns = [
            # 2026-09-06 22:30:15 or 2026/09/06 22:30:15
            re.compile(r'\b(20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?)\b'),
            # 06-09-2026 22:30:15 or 06/09/2026 22:30:15
            re.compile(r'\b(\d{1,2}[-/.]\d{1,2}[-/.]20\d{2}\s+\d{1,2}:\d{2}(?::\d{2})?)\b'),
            # Time only: 22:30:15 or 10:15:30 PM
            re.compile(r'\b(\d{1,2}:\d{2}:\d{2}(?:\s*[AaPp][Mm])?)\b'),
        ]

        for f_idx in sample_frame_indices:
            if f_idx >= total_frames:
                continue

            cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            h, w = frame.shape[:2]
            # Strip 1: Top 18% (standard CCTV header banner)
            top_strip = frame[0:int(h * 0.18), :]
            # Strip 2: Bottom 18% (standard CCTV footer banner)
            bottom_strip = frame[int(h * 0.82):h, :]

            for strip in [top_strip, bottom_strip]:
                try:
                    ocr_results = self.reader.readtext(strip, detail=1)
                    for bbox, text, conf in ocr_results:
                        clean_text = text.strip()
                        if not clean_text:
                            continue
                        all_detected_text.append(clean_text)

                        # Test against timestamp patterns
                        for pat in ts_patterns:
                            m = pat.search(clean_text)
                            if m and not found_timestamp:
                                found_timestamp = m.group(1)
                                timestamp_conf = round(float(conf), 2)
                                break
                except Exception:
                    continue

            if found_timestamp:
                break

        cap.release()

        # Deduplicate detected text strings
        unique_text = list(dict.fromkeys(all_detected_text))

        if found_timestamp:
            result = {
                "detected": True,
                "status": "Embedded timestamp detected",
                "timestamp": found_timestamp,
                "confidence": timestamp_conf,
                "text_lines": unique_text,
                "engine": "EasyOCR (PyTorch CPU)",
                "fallback": "Video frame timing (MM:SS)",
            }
        else:
            result = {
                "detected": False,
                "status": "Embedded timestamp not detected",
                "timestamp": None,
                "confidence": 0.0,
                "text_lines": unique_text,
                "engine": "EasyOCR (PyTorch CPU)",
                "fallback": "Video frame timing (MM:SS)",
            }

        self._cache[video_path] = result
        return result
