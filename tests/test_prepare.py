import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from prepare import plan, validate_row, month_usage

SETTINGS = {"timezone": "America/Sao_Paulo", "start_delay_days": 1,
            "days_between_clips": 3, "slots": {"tiktok": "12:30", "instagram": "17:00"}}
CLIP = {"clip_id": "clipe_001", "filename": "clipe.mp4", "media_url": "",
        "caption": "Momento gamer!", "approved": "sim", "rights_cleared": "sim", "credit": "@criador", "platforms": "both"}

class TestPrepare(unittest.TestCase):
    def test_valid_clip(self):
        self.assertIsNone(validate_row(CLIP))
    def test_no_rights(self):
        self.assertIsNotNone(validate_row({**CLIP, "rights_cleared": "nao"}))
    def test_invalid_filename(self):
        self.assertIsNotNone(validate_row({**CLIP, "filename": "../video.mp4"}))
    def test_unknown_month_blocks(self):
        p, warn = plan([CLIP], SETTINGS, {}, date(2026,11,12))
        self.assertFalse(p)
        self.assertTrue(warn)
    def test_two_scheduled_on_same_date(self):
        p, warn = plan([CLIP], SETTINGS, {"2026-11":{"published":0,"already_scheduled":0}}, date(2026,11,12))
        self.assertEqual(len(p), 2)
        self.assertEqual(p[0]["scheduled_at"], "2026-11-13T12:30-03:00")
        self.assertEqual(p[1]["scheduled_at"], "2026-11-13T17:00-03:00")
        self.assertIn("Créditos: @criador", p[0]["caption"])
    def test_limit(self):
        p, warn = plan([CLIP], SETTINGS, {"2026-11":{"published":19,"already_scheduled":0}}, date(2026,11,12))
        self.assertEqual(p, [])
        self.assertTrue(warn)
    def test_spacing(self):
        clips=[{**CLIP,"clip_id":f"clip_{i:03d}"} for i in range(2)]
        p,_=plan(clips, SETTINGS, {"2026-11":{"published":0,"already_scheduled":0}}, date(2026,11,12))
        self.assertEqual([x["scheduled_at"] for x in p[::2]], ["2026-11-13T12:30-03:00","2026-11-16T12:30-03:00"])
    def test_usage(self):
        self.assertEqual(month_usage("2026-11", {"2026-11":{"published":4,"already_scheduled":7}}),11)

if __name__ == "__main__": unittest.main()
