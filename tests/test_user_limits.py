import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import telegram_bot as bot
from user_limits import record_success, remaining_analyses


class UserLimitsTests(unittest.TestCase):
    def test_counts_survive_reopening_and_are_separate_per_user(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "usage.sqlite3"
            self.assertEqual(remaining_analyses(101, path), 3)
            for expected in (2, 1, 0):
                self.assertEqual(record_success(101, path), expected)
            # Each function opens a new connection, just as after a restart.
            self.assertEqual(remaining_analyses(101, path), 0)
            self.assertEqual(remaining_analyses(202, path), 3)

    def test_fourth_video_is_blocked_and_other_user_can_still_analyze(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "data"
            (data / "graphs").mkdir(parents=True)
            for name in ("analysis_summary.txt", "en_analysis_summary.txt"):
                (data / name).write_text("Summary text", encoding="utf-8")
            for name in ("ru_analysis.pdf", "en_analysis.pdf"):
                (data / name).write_bytes(b"%PDF-test")
            for name in ("sentiment_distribution", "topic_distribution", "engagement_by_sentiment"):
                (data / "graphs" / f"{name}.png").write_bytes(b"test image")
            url = "https://youtu.be/hT_MAAwFLIc"
            with patch.object(bot, "ROOT", root), patch.object(bot, "run_pipeline") as pipeline, \
                    patch.object(bot, "send_message") as messages, \
                    patch.object(bot, "send_photo") as photos, \
                    patch.object(bot, "send_document") as documents:
                for _ in range(3):
                    bot.process_video(101, url, user_id=101)
                self.assertEqual(pipeline.call_count, 3)
                self.assertEqual(remaining_analyses(101, data / "user_limits.sqlite3"), 0)
                photos.reset_mock()
                documents.reset_mock()
                bot.process_video(101, url, user_id=101)
                self.assertEqual(pipeline.call_count, 3)
                photos.assert_not_called()
                documents.assert_not_called()
                self.assertIn("limit has been reached", messages.call_args.args[1])
                bot.process_video(202, url, user_id=202)
                self.assertEqual(pipeline.call_count, 4)
                self.assertEqual(remaining_analyses(202, data / "user_limits.sqlite3"), 2)

                # A failed pipeline must not consume a user's remaining attempts.
                pipeline.side_effect = RuntimeError("test failure")
                with contextlib.redirect_stderr(io.StringIO()):
                    bot.process_video(202, url, user_id=202)
                self.assertEqual(remaining_analyses(202, data / "user_limits.sqlite3"), 2)

    def test_polling_uses_the_senders_user_id(self):
        update = {"update_id": 1, "message": {
            "from": {"id": 123}, "chat": {"id": 123, "type": "private"},
            "text": "https://youtu.be/hT_MAAwFLIc",
        }}
        with patch.object(bot, "BOT_TOKEN", "test"), \
                patch.object(bot, "telegram", side_effect=[[update], KeyboardInterrupt]), \
                patch.object(bot, "process_video") as process, \
                patch("sys.argv", ["telegram_bot.py"]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bot.main(), 0)
        process.assert_called_once_with(123, update["message"]["text"], user_id=123)


if __name__ == "__main__":
    unittest.main()
