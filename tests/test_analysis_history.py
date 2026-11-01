import os
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import analysis_history


class AnalysisHistoryTests(unittest.TestCase):
    def test_history_keeps_links_and_continues_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "data" / "history.txt"
            url = "https://www.youtube.com/watch?v=hT_MAAwFLIc&t=109s"
            analysis_history.record_analysis_start(url, path)
            analysis_history.record_analysis_start(url, path)
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 2)
            for number, line in enumerate(lines, 1):
                self.assertRegex(line, rf"^\({number}\) \(\d{{4}}-\d{{2}}-\d{{2}} \d{{2}}:\d{{2}}:\d{{2}} [+-]\d{{4}}\) ")
                self.assertTrue(line.endswith(f"({url})"))
            # Existing records, including one without a final newline, survive.
            path.write_text(lines[0] + "\n" + lines[1], encoding="utf-8")
            analysis_history.record_analysis_start(url, path)
            new_lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(new_lines[:2], lines)
            self.assertTrue(new_lines[2].startswith("(3) "))

    def test_collection_records_start_even_when_youtube_fails(self):
        main_path = analysis_history.ROOT / "main.py"
        url = "https://youtu.be/hT_MAAwFLIc?t=109"
        with patch.dict(os.environ, {"YOUTUBE_VIDEO_URL": url}), \
                patch("googleapiclient.discovery.build") as build, \
                patch("dotenv.load_dotenv"), \
                patch.object(analysis_history, "record_analysis_start") as record:
            build.return_value.commentThreads.return_value.list.return_value.execute.side_effect = RuntimeError("API unavailable")
            with self.assertRaisesRegex(RuntimeError, "API unavailable"):
                runpy.run_path(str(main_path), run_name="__main__")
            record.assert_called_once_with(url)


if __name__ == "__main__":
    unittest.main()
