"""Scheduled failure episodes survive invocations and escalate after grace."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from sync_failure_grace import diagnose_failure, main, mark_notification_attempted, update_failure_state


class FailureGraceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name) / "state" / "failures.json"

    def record(self, project="claude-code", exit_code=1, now=1000):
        return update_failure_state(self.state, project, exit_code, 900, now)

    def test_consecutive_failure_escalates_once_and_recovery_resets(self):
        self.assertEqual(self.record(), (
            "claude-code: within grace period; 1 failed run(s), age 0s/900s, last exit 1",
            False, False,
        ))
        self.assertEqual(self.record(now=1300)[1:], (False, False))
        self.assertEqual(self.record(now=1900)[1:], (True, True))
        mark_notification_attempted(self.state, "claude-code", "The binary package is missing.")
        self.assertEqual(self.record(now=2200)[1:], (True, False))
        self.assertEqual(json.loads(self.state.read_text())["claude-code"]["count"], 4)
        self.assertIn("recovered after 4 failed run(s)", self.record(exit_code=0, now=2300)[0])
        self.assertEqual(json.loads(self.state.read_text()), {})
        self.assertEqual(self.record(now=2400)[1:], (False, False))

    def test_projects_have_independent_failure_ages(self):
        self.record(now=1000)
        self.record(project="codex", now=1800)
        self.assertEqual(self.record(now=1900)[1:], (True, True))
        self.assertEqual(self.record(project="codex", now=1900)[1:], (False, False))
        self.record(exit_code=0, now=2000)
        self.assertIn("codex", json.loads(self.state.read_text()))

    def test_invalid_state_does_not_reset_grace(self):
        self.state.parent.mkdir(parents=True)
        self.state.write_text("{not json")
        with self.assertRaises(json.JSONDecodeError):
            self.record()
        self.assertEqual(self.state.read_text(), "{not json")

    def test_cli_alerts_only_when_grace_expires(self):
        log = Path(self.temp.name) / "project.log"
        log.write_text("✗ Error: git fetch timed out\n")
        args = [
            "sync_failure_grace.py", "--project", "codex", "--exit-code", "1",
            "--grace-seconds", "900", "--state", str(self.state), "--log", str(log),
        ]
        with patch.object(sys, "argv", args), \
             patch("sync_failure_grace.time.time", side_effect=[1000, 1900, 2200]), \
             patch("sync_failure_grace.diagnose_failure", return_value=(
                 "GitHub timed out while fetching tags.", True,
             )) as diagnose, \
             patch("sync_failure_grace.subprocess.run") as notify:
            self.assertEqual(main(), 0)
            diagnose.assert_not_called()
            self.assertEqual(main(), 1)
            self.assertEqual(main(), 1)
        diagnose.assert_called_once_with("codex", 1, log)
        notify.assert_called_once()
        self.assertIn("GitHub timed out", notify.call_args.args[0][-1])
        self.assertEqual(
            json.loads(self.state.read_text())["codex"]["diagnosis"],
            "GitHub timed out while fetching tags.",
        )

    def test_sol_diagnosis_uses_failed_run_log_and_read_only_exec(self):
        log = Path(self.temp.name) / "project.log"
        log.write_text("Fetching version\n✗ Error: git fetch timed out\nTotal failures: 1\n")

        def fake_codex(command, **kwargs):
            self.assertIn("exec", command)
            self.assertIn("gpt-6-sol", command)
            self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
            self.assertIn("git fetch timed out", kwargs["input"])
            answer = Path(command[command.index("--output-last-message") + 1])
            answer.write_text("GitHub did not answer the tag fetch before its timeout.\n")
            return subprocess.CompletedProcess(command, 0, "", "")

        with patch("sync_failure_grace.subprocess.run", side_effect=fake_codex):
            self.assertEqual(
                diagnose_failure("codex", 1, log),
                ("GitHub did not answer the tag fetch before its timeout.", True),
            )

    def test_codex_failure_keeps_plain_alert(self):
        log = Path(self.temp.name) / "project.log"
        log.write_text("✗ Error: npm registry unavailable\n")
        with patch("sync_failure_grace.subprocess.run", side_effect=OSError("offline")):
            summary, analyzed = diagnose_failure("claude-code", 1, log)
        self.assertFalse(analyzed)
        self.assertIn("Codex analysis unavailable", summary)


if __name__ == "__main__":
    unittest.main()
