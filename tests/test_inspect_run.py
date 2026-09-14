import tempfile
import unittest
from pathlib import Path
from tools.inspect_run import render


class RunViewerTests(unittest.TestCase):
    def test_missing_outputs_and_untrusted_text_display_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run/'manifest.json').write_text('{}', encoding='utf-8')
            (run/'evidence.json').write_text('{"data":"<script>alert(1)</script>"}', encoding='utf-8')
            page = render(run)
            self.assertIn('未生成', page)
            self.assertIn('&lt;script&gt;', page)
            self.assertNotIn('<script>', page)
            self.assertIn('M6', page)

    def test_invalid_run_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'manifest'): render(tmp)
