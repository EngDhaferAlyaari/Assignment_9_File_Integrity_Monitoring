"""Local automated tests for Assignment 9."""

import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fim_monitor as fim


class FileIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.target = self.root / "document.txt"
        self.data = self.root / "hashes"
        self.target.write_text("original content\n", encoding="utf-8")

    def check(self, reset=False):
        return fim.check_file(self.target, self.data, reset=reset)

    def test_sha256_matches_python(self):
        self.assertEqual(fim.sha256_file(self.target), hashlib.sha256(self.target.read_bytes()).hexdigest())

    def test_binary_mode_handles_null_bytes(self):
        self.target.write_bytes(b"\x00\x01\xff\r\n")
        self.assertEqual(fim.sha256_file(self.target), hashlib.sha256(b"\x00\x01\xff\r\n").hexdigest())

    def test_empty_file(self):
        self.target.write_bytes(b"")
        self.assertEqual(fim.sha256_file(self.target), hashlib.sha256(b"").hexdigest())

    def test_chunked_large_file(self):
        blob = b"a" * (1024 * 1024 + 13)
        self.target.write_bytes(blob)
        self.assertEqual(fim.sha256_file(self.target), hashlib.sha256(blob).hexdigest())

    def test_first_check_creates_baseline(self):
        status, _, _ = self.check()
        self.assertEqual(status, "BASELINE")
        self.assertTrue(fim.baseline_path(self.target, self.data).exists())

    def test_saved_baseline_valid_json(self):
        self.check()
        data = json.loads(fim.baseline_path(self.target, self.data).read_text())
        self.assertEqual(data["sha256"], fim.sha256_file(self.target))

    def test_unchanged_file_ok(self):
        self.check()
        self.assertEqual(self.check()[0], "OK")

    def test_single_character_change_alert(self):
        self.check()
        self.target.write_text("original contEnt\n", encoding="utf-8")
        status, message, _ = self.check()
        self.assertEqual(status, "ALERT")
        self.assertIn("CRITICAL ALERT", message)

    def test_same_length_change_detected(self):
        self.check()
        self.target.write_text("original contenX\n", encoding="utf-8")
        self.assertEqual(self.check()[0], "ALERT")

    def test_append_detected(self):
        self.check()
        with open(self.target, "a", encoding="utf-8") as file:
            file.write("new line\n")
        self.assertEqual(self.check()[0], "ALERT")

    def test_truncation_detected(self):
        self.check()
        self.target.write_bytes(b"")
        self.assertEqual(self.check()[0], "ALERT")

    def test_original_restored_ok(self):
        self.check()
        self.target.write_bytes(b"changed")
        self.assertEqual(self.check()[0], "ALERT")
        self.target.write_text("original content\n", encoding="utf-8")
        self.assertEqual(self.check()[0], "OK")

    def test_baseline_unchanged_on_alert(self):
        self.check()
        baseline_file = fim.baseline_path(self.target, self.data)
        initial = baseline_file.read_bytes()
        self.target.write_bytes(b"tampered")
        self.check()
        self.assertEqual(initial, baseline_file.read_bytes())

    def test_baseline_survives_second_call(self):
        self.check()
        self.assertEqual(fim.check_file(self.target, self.data)[0], "OK")

    def test_explicit_reset(self):
        self.check()
        self.target.write_bytes(b"approved change")
        self.assertEqual(self.check()[0], "ALERT")
        self.assertEqual(self.check(reset=True)[0], "BASELINE")
        self.assertEqual(self.check()[0], "OK")

    def test_missing_file_without_baseline(self):
        self.target.unlink()
        self.assertEqual(self.check()[0], "MISSING")
        self.assertFalse(fim.baseline_path(self.target, self.data).exists())

    def test_missing_file_with_baseline(self):
        self.check()
        self.target.unlink()
        self.assertEqual(self.check()[0], "MISSING")

    def test_corrupt_baseline_error(self):
        self.check()
        fim.baseline_path(self.target, self.data).write_text("this is not json")
        self.assertEqual(self.check()[0], "ERROR")

    def test_malformed_hash_error(self):
        self.check()
        fim.baseline_path(self.target, self.data).write_text('{"sha256":"123"}')
        self.assertEqual(self.check()[0], "ERROR")

    def test_cannot_read_file_error(self):
        with patch.object(fim, "sha256_file", side_effect=PermissionError("blocked")):
            self.assertEqual(self.check()[0], "ERROR")

    def test_different_paths_unique_baselines(self):
        second = self.root / "other.txt"
        self.assertNotEqual(fim.baseline_path(self.target, self.data), fim.baseline_path(second, self.data))

    def test_log_written_when_alert(self):
        self.check()
        self.target.write_bytes(b"changed")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(fim.monitor(self.target, self.data, once=True), 1)
        self.assertIn("CRITICAL ALERT", (self.data / "alerts.log").read_text())

    def test_one_time_baseline_exit_zero(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(fim.monitor(self.target, self.data, once=True), 0)

    def test_one_time_ok_exit_zero(self):
        self.check()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(fim.monitor(self.target, self.data, once=True), 0)

    def test_one_time_missing_exit_two(self):
        self.target.unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(fim.monitor(self.target, self.data, once=True), 2)

    def test_interval_validation(self):
        with self.assertRaises(ValueError):
            fim.monitor(self.target, self.data, interval=0)

    def test_loop_checks_repeatedly(self):
        out = io.StringIO()
        with patch.object(fim.time, "sleep") as mocked_sleep:
            with contextlib.redirect_stdout(out):
                self.assertEqual(fim.monitor(self.target, self.data, interval=3, max_checks=3), 0)
            self.assertEqual(mocked_sleep.call_count, 2)
            mocked_sleep.assert_called_with(3)

    def test_repeated_alert_is_not_spammed(self):
        self.check()
        self.target.write_bytes(b"bad")
        out = io.StringIO()
        with patch.object(fim.time, "sleep"):
            with contextlib.redirect_stdout(out):
                self.assertEqual(fim.monitor(self.target, self.data, max_checks=3), 1)
        self.assertEqual(out.getvalue().count("CRITICAL ALERT"), 1)

    def test_main_once_cli(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(fim.main([str(self.target), "--once", "--baseline-dir", str(self.data)]), 0)

    def test_main_rejects_zero_interval(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                fim.main([str(self.target), "--interval", "0"])
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
