import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import analyze
import report_pdf
import telegram_bot as bot


class BilingualReportsTests(unittest.TestCase):
    def test_analysis_translates_matching_sources_and_saves_both_languages(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "comments.csv"
            source.write_text("number;comment;likes;replies\n1;Great video;2;0\n", encoding="utf-8")
            labels = json.dumps({"comments": [{"number": 1, "sentiment": "positive", "topic": "Video"}]})
            outputs = {
                "--output": "analysis.md", "--english-output": "en_analysis.md",
                "--summary-output": "analysis_summary.txt",
                "--english-summary-output": "en_analysis_summary.txt",
                "--data-output": "analysis_data.json",
            }
            argv = ["analyze.py"]
            for flag, name in outputs.items():
                argv.extend([flag, str(root / name)])
            answers = ["Latest report", labels, "Top report", labels, "Comparison",
                       "Russian summary", "# English report", "English summary"]
            with patch.object(analyze, "DEFAULT_FILES", {"Latest comments": source, "Top comments": source}), \
                    patch.object(analyze, "ask_ollama", side_effect=answers) as model, \
                    patch("sys.argv", argv), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(analyze.main(), 0)
            for name, expected in [("analysis_summary.txt", answers[5]),
                                   ("en_analysis.md", answers[6]),
                                   ("en_analysis_summary.txt", answers[7])]:
                self.assertEqual((root / name).read_text(encoding="utf-8").strip(), expected)
            report = (root / "analysis.md").read_text(encoding="utf-8")
            self.assertIn(report, model.call_args_list[6].args[2])
            self.assertIn(answers[5], model.call_args_list[7].args[2])
            self.assertIn("Do not include advice", model.call_args_list[7].args[2])

    def test_pdf_command_creates_both_requested_filenames(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            (root / "data/analysis.md").write_text("# \u0410\u043d\u0430\u043b\u0438\u0437\n\n\u041e\u0442\u0437\u044b\u0432\u044b.", encoding="utf-8")
            (root / "data/en_analysis.md").write_text("# Analysis\n\nViewer feedback.", encoding="utf-8")
            with patch.object(report_pdf, "ROOT", root), patch("sys.argv", ["report_pdf.py"]), \
                    contextlib.redirect_stdout(io.StringIO()):
                report_pdf.main()
            for filename in ("ru_analysis.pdf", "en_analysis.pdf"):
                content = (root / "data" / filename).read_bytes()
                self.assertTrue(content.startswith(b"%PDF-"))
                self.assertIn(b"/FontFile2", content)

    def test_bot_delivers_both_summaries_and_pdfs_to_the_same_chat(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "data"
            (data / "graphs").mkdir(parents=True)
            for name, text in [("analysis_summary.txt", "Russian text"),
                               ("en_analysis_summary.txt", "English text")]:
                (data / name).write_text(text, encoding="utf-8")
            for name in ("ru_analysis.pdf", "en_analysis.pdf"):
                (data / name).write_bytes(b"%PDF-test")
            for name in ("sentiment_distribution", "topic_distribution", "engagement_by_sentiment"):
                (data / "graphs" / f"{name}.png").write_bytes(b"test image")
            with patch.object(bot, "ROOT", root), patch.object(bot, "run_pipeline"), \
                    patch.object(bot, "send_message") as messages, \
                    patch.object(bot, "send_document") as documents, \
                    patch.object(bot, "send_photo") as photos:
                bot.process_video(42, "https://youtu.be/hT_MAAwFLIc")
                texts = [call.args[1] for call in messages.call_args_list]
                self.assertIn("Russian summary\n\nRussian text", texts)
                self.assertIn("English summary\n\nEnglish text", texts)
                self.assertEqual([call.args[1].name for call in documents.call_args_list],
                                 ["ru_analysis.pdf", "en_analysis.pdf"])
                self.assertEqual(photos.call_count, 3)
                for call in messages.call_args_list + documents.call_args_list + photos.call_args_list:
                    self.assertEqual(call.args[0], 42)
                # Missing translations must not cause an incomplete delivery.
                (data / "en_analysis.pdf").unlink()
                documents.reset_mock()
                photos.reset_mock()
                with contextlib.redirect_stderr(io.StringIO()):
                    bot.process_video(42, "https://youtu.be/hT_MAAwFLIc")
                documents.assert_not_called()
                photos.assert_not_called()
                self.assertIn("Processing failed", messages.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
