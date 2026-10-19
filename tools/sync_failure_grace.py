#!/usr/bin/env python3
"""Track consecutive scheduled sync failures across wrapper invocations."""

import argparse
from collections import deque
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time


DEFAULT_STATE = Path.home() / ".local/state/ai-cli-changelog-sync/failures.json"
CODEX_MODEL = "gpt-6-sol"
DIAGNOSIS_LIMIT = 160


def _read_state(state_path):
    try:
        state = json.loads(state_path.read_text())
    except FileNotFoundError:
        state = {}
    if not isinstance(state, dict):
        raise ValueError(f"invalid failure state in {state_path}")
    return state


def _write_state(state_path, state):
    state_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".failures-", dir=state_path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(state, handle, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, state_path)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def update_failure_state(state_path, project, exit_code, grace_seconds, now=None):
    """Return (message, escalated, notify) after recording one project run."""
    now = time.time() if now is None else now
    state = _read_state(state_path)

    previous = state.get(project)
    if previous is not None and (
        not isinstance(previous, dict)
        or not isinstance(previous.get("first_failed_at"), (int, float))
        or not isinstance(previous.get("count"), int)
        or not isinstance(previous.get("notified"), bool)
    ):
        raise ValueError(f"invalid {project} failure state in {state_path}")

    if exit_code == 0:
        if previous is None:
            return "", False, False
        age = max(0, int(now - previous["first_failed_at"]))
        del state[project]
        message = f"{project}: recovered after {previous['count']} failed run(s) over {age}s"
        escalated = notify = False
    else:
        first = previous["first_failed_at"] if previous else now
        count = previous["count"] + 1 if previous else 1
        age = max(0, int(now - first))
        escalated = age >= grace_seconds
        notify = escalated and not (previous and previous["notified"])
        state[project] = {
            "first_failed_at": first,
            "last_failed_at": now,
            "count": count,
            "last_exit_code": exit_code,
            "notified": bool(previous and previous["notified"]),
        }
        if previous and "diagnosis" in previous:
            state[project]["diagnosis"] = previous["diagnosis"]
        status = "persistent failure" if escalated else "within grace period"
        message = (
            f"{project}: {status}; {count} failed run(s), age {age}s/"
            f"{grace_seconds}s, last exit {exit_code}"
        )

    _write_state(state_path, state)
    return message, escalated, notify


def mark_notification_attempted(state_path, project, diagnosis):
    """Acknowledge the alert only after the Codex and notification attempts."""
    state = _read_state(state_path)
    if project not in state:
        raise ValueError(f"missing {project} failure state in {state_path}")
    state[project]["notified"] = True
    state[project]["diagnosis"] = diagnosis
    _write_state(state_path, state)


def _brief(text):
    text = re.sub(r"\s+", " ", text).strip().strip('`"')
    if len(text) > DIAGNOSIS_LIMIT:
        text = text[:DIAGNOSIS_LIMIT - 1].rsplit(" ", 1)[0] + "…"
    return text


def _failure_excerpt(log_path):
    if log_path is None:
        return ""
    markers = ("Error:", "Warning:", "FAILED", "failed", "fatal:", "Traceback", "TIMED OUT")
    important = deque(maxlen=40)
    tail = deque(maxlen=80)
    with log_path.open(errors="replace") as handle:
        for line in handle:
            tail.append(line)
            if any(marker in line for marker in markers):
                important.append(line)
    return ("Recent output:\n" + "".join(tail) + "\nFailure lines:\n" + "".join(important))[-16000:]


def diagnose_failure(project, exit_code, log_path):
    """Ask read-only Codex for one sentence; return a log-grounded fallback."""
    try:
        excerpt = _failure_excerpt(log_path)
    except OSError:
        excerpt = ""
    fallback = "Codex analysis unavailable; see the sync log for the recorded error."
    if not excerpt.strip():
        return fallback, False

    prompt = (
        "Analyze this failed scheduled archive sync using only the supplied log. "
        "Do not run commands or inspect files. Give one plain sentence of at most "
        "160 characters naming the most likely cause. If the evidence is insufficient, "
        "say so. Do not include credentials, tokens, file paths, or full URLs. "
        "Do not propose a fix or use Markdown.\n\n"
        f"Project: {project}; process exit: {exit_code}\n\n{excerpt}"
    )
    codex_bin = os.getenv("CHANGELOG_CODEX_BIN") or "codex"
    try:
        with tempfile.TemporaryDirectory(prefix="changelog-diagnosis-") as temp_dir:
            answer_path = Path(temp_dir) / "answer.txt"
            result = subprocess.run(
                [
                    "timeout", "--signal=TERM", "--kill-after=5s", "45s",
                    codex_bin, "--model", CODEX_MODEL,
                    "--config", 'model_reasoning_effort="low"',
                    "--sandbox", "read-only", "--ask-for-approval", "never",
                    "--cd", temp_dir, "exec", "--ephemeral", "--ignore-rules",
                    "--skip-git-repo-check", "--output-last-message", str(answer_path),
                    "--color", "never", "-",
                ],
                input=prompt, text=True, capture_output=True, timeout=55,
            )
            if result.returncode == 0 and answer_path.exists():
                answer = _brief(answer_path.read_text())
                if answer:
                    return answer, True
    except (OSError, subprocess.TimeoutExpired):
        pass
    return fallback, False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--grace-seconds", type=int, default=900)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--log", type=Path, help="output from this project's failed run")
    args = parser.parse_args()
    if args.exit_code < 0 or args.grace_seconds < 0:
        parser.error("exit code and grace period must be nonnegative")

    try:
        message, escalated, notify = update_failure_state(
            args.state, args.project, args.exit_code, args.grace_seconds
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"{args.project}: cannot track sync failures: {exc}")
        return 2
    if notify:
        summary, analyzed = diagnose_failure(args.project, args.exit_code, args.log)
        message += f"; {'Codex Sol analysis' if analyzed else 'fallback'}: {summary}"
        try:
            subprocess.run(
                ["notify-send", "--urgency=critical", f"{args.project}: sync failure", message],
                check=False, capture_output=True, timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        try:
            mark_notification_attempted(args.state, args.project, summary)
        except (OSError, ValueError) as exc:
            print(f"{args.project}: could not record notification attempt: {exc}")
            return 2
    if message:
        print(message)
    return 1 if escalated else 0


if __name__ == "__main__":
    raise SystemExit(main())
