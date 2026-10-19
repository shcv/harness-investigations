#!/usr/bin/env python3
"""Agent provider adapters for changelog generation."""

from __future__ import annotations

import asyncio
import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence


SUPPORTED_AGENT_PROVIDERS = ("claude", "codex", "qwen")
DEFAULT_AGENT_PROVIDER = "codex"
SESSION_LOG_KEEP = 5
DEFAULT_SESSION_LOG_DIR = Path(__file__).resolve().parents[1] / ".agent-logs"


def load_project_env() -> None:
    """Use the same checkout configuration in all pipeline entry points."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class AgentRunnerError(RuntimeError):
    """Raised when an agent provider cannot complete a request."""


def _tail(text: str, max_chars: int = 4000) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


@dataclass(frozen=True)
class AgentRunRequest:
    prompt: str
    system_prompt: str = ""
    cwd: Path = field(default_factory=Path.cwd)
    allowed_tools: Optional[Sequence[str]] = None
    env: Optional[dict[str, str]] = None
    timeout: Optional[int] = None
    read_roots: Optional[Sequence[Path]] = None


class SessionLog:
    """Private, bounded provider transcripts; active runs are never pruned."""

    def __init__(self, runner: BaseAgentRunner, request: AgentRunRequest):
        configured = (request.env or {}).get("CHANGELOG_AGENT_LOG_DIR") or os.getenv(
            "CHANGELOG_AGENT_LOG_DIR"
        )
        self.root = Path(configured).expanduser().resolve() if configured else DEFAULT_SESSION_LOG_DIR
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.metadata = {
            "schema_version": 1,
            "provider": runner.provider,
            "requested_model": getattr(runner, "model", None),
            "reasoning_effort": getattr(runner, "reasoning_effort", None),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "status": "running",
            "cwd": str(request.cwd),
            "allowed_tools": request.allowed_tools,
            "read_roots": [str(p) for p in request.read_roots or []],
            "timeout": request.timeout,
        }
        with self._locked_root():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
            self.path = Path(tempfile.mkdtemp(prefix=f"run-{stamp}-{runner.provider}-", dir=self.root))
            self._active = (self.path / ".active.lock").open("w")
            fcntl.flock(self._active, fcntl.LOCK_EX)
            self._write_metadata()
        # Deliberately exclude request.env and provider credentials from logs.
        self.write_text("request.json", json.dumps({
            "prompt": request.prompt, "system_prompt": request.system_prompt,
        }, ensure_ascii=False, indent=2))
        self.prune()

    @contextmanager
    def _locked_root(self):
        with (self.root / ".retention.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            yield

    def write_text(self, name: str, content: str) -> None:
        (self.path / name).write_text(content, encoding="utf-8")

    def record(self, event_type: str, data: object) -> None:
        with (self.path / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"type": event_type, "data": data}, ensure_ascii=False) + "\n")

    def _write_metadata(self) -> None:
        self.write_text("metadata.json", json.dumps(self.metadata, ensure_ascii=False, indent=2))

    def finish(self, status: str, resolved_model: Optional[str]) -> None:
        try:
            self.metadata.update(status=status, resolved_model=resolved_model,
                                 finished_at=datetime.now(timezone.utc).isoformat())
            self._write_metadata()
        finally:
            self._active.close()
        self.prune()

    def prune(self) -> None:
        # A kernel lock also distinguishes a live run from one killed before
        # finish(). Only directories created by this logger are candidates.
        with self._locked_root():
            finished = 0
            for path in sorted(self.root.glob("run-*"), reverse=True):
                if path.is_symlink() or not (path / "metadata.json").is_file():
                    continue
                try:
                    active = (path / ".active.lock").open("r+")
                except FileNotFoundError:
                    continue
                with active:
                    try:
                        fcntl.flock(active, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        continue
                    finished += 1
                    if finished > SESSION_LOG_KEEP:
                        shutil.rmtree(path)


class BaseAgentRunner:
    provider = "base"
    supports_file_write_tool = False
    # The concrete model ID that actually served the last run(), if the
    # provider can report one (e.g. resolving a "sonnet"-style alias).
    # None means: no better information than the requested model string.
    last_resolved_model: Optional[str] = None
    last_log_dir: Optional[Path] = None

    def check_available(self) -> None:
        raise NotImplementedError

    def run(self, request: AgentRunRequest) -> str:
        self.last_resolved_model = None
        log = SessionLog(self, request)
        self.last_log_dir = log.path
        print(f"Agent session log: {log.path}", file=sys.stderr, flush=True)
        status = "failed"
        try:
            result = self._run(request, log)
            log.write_text("final.txt", result)
            status = "succeeded"
            return result
        except BaseException as exc:
            log.write_text("error.txt", f"{type(exc).__name__}: {exc}\n")
            raise
        finally:
            log.finish(status, self.last_resolved_model)

    def _run(self, request: AgentRunRequest, log: SessionLog) -> str:
        raise NotImplementedError


class ClaudeSdkRunner(BaseAgentRunner):
    provider = "claude"
    supports_file_write_tool = True

    def __init__(self, model: Optional[str] = None):
        self.model = model
        self.last_resolved_model = None

    def check_available(self) -> None:
        try:
            import claude_agent_sdk  # noqa: F401
        except ImportError as exc:
            raise AgentRunnerError(
                "claude-agent-sdk is not installed. Install with: pip install claude-agent-sdk"
            ) from exc

    def _run(self, request: AgentRunRequest, log: SessionLog) -> str:
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ResultMessage,
            query,
        )

        # Use the caller's default CLAUDE_CONFIG_DIR (normally ~/.claude). We do
        # NOT isolate the config dir: a separate dir needs its own credentials,
        # and either a copy (goes stale) or a symlink (claude clobbers it on
        # token refresh) ends up as a second credential store for the same
        # account. Two stores doing independent OAuth refresh rotate the
        # single-use refresh token out from under each other and log the user
        # out. Session-list tidiness is handled by running the agent in a
        # dedicated cwd instead (claude buckets sessions by cwd).
        env = dict(request.env or {})

        kwargs = {
            "system_prompt": request.system_prompt,
            "allowed_tools": list(request.allowed_tools or []),
            "permission_mode": "bypassPermissions",
            "cwd": str(request.cwd),
            "env": env,
        }
        if self.model:
            kwargs["model"] = self.model

        options = ClaudeAgentOptions(**kwargs)

        async def _execute() -> str:
            result = ""
            async for msg in query(prompt=request.prompt, options=options):
                # SDK messages include tool-use and tool-result content blocks.
                log.record(type(msg).__name__, asdict(msg) if is_dataclass(msg) else vars(msg))
                if isinstance(msg, AssistantMessage) and msg.model:
                    # Track the last-seen resolved model in case an alias
                    # (e.g. "sonnet") or a fallback_model switch changed which
                    # concrete model actually served the request.
                    self.last_resolved_model = msg.model
                if isinstance(msg, ResultMessage):
                    if msg.is_error:
                        raise AgentRunnerError(msg.result or "Claude query failed")
                    result = msg.result or ""
            return result

        if request.timeout:
            async def _with_timeout() -> str:
                return await asyncio.wait_for(_execute(), timeout=request.timeout)

            return asyncio.run(_with_timeout())

        return asyncio.run(_execute())


class CodexExecRunner(BaseAgentRunner):
    provider = "codex"
    supports_file_write_tool = False

    def __init__(
        self,
        model: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
        executable: str = "codex",
    ):
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.executable = executable

    def check_available(self) -> None:
        if shutil.which(self.executable) is None:
            raise AgentRunnerError(f"{self.executable!r} was not found on PATH")

    def _run(self, request: AgentRunRequest, log: SessionLog) -> str:
        self.check_available()

        cwd = Path(request.cwd).resolve()
        output_path = log.path / "last-message.txt"
        output_path.touch()

        with (log.path / "events.jsonl").open("w", encoding="utf-8") as events, \
             (log.path / "stderr.log").open("w", encoding="utf-8") as stderr:
            cmd = [self.executable]
            if self.model:
                cmd.extend(["--model", self.model])
            if self.reasoning_effort:
                cmd.extend([
                    "--config",
                    f'model_reasoning_effort="{self.reasoning_effort}"',
                ])
            cmd.extend([
                "--sandbox",
                "read-only",
                "--ask-for-approval",
                "never",
                "--cd",
                str(cwd),
                "exec",
                "--ephemeral",
                "--json",
                "--ignore-rules",
                "--output-last-message",
                str(output_path),
                "--color",
                "never",
                "-",
            ])

            env = os.environ.copy()
            if request.env:
                env.update(request.env)

            prompt = self._compose_prompt(request)
            log.write_text("prompt.txt", prompt)
            log.write_text("command.json", json.dumps(cmd, indent=2))
            completed = subprocess.run(
                cmd,
                input=prompt,
                text=True,
                stdout=events,
                stderr=stderr,
                cwd=str(cwd),
                env=env,
                timeout=request.timeout,
                check=False,
            )

            output = output_path.read_text(encoding="utf-8", errors="replace")
            log.metadata["exit_code"] = completed.returncode
            if completed.returncode != 0:
                detail = "\n".join(
                    part for part in (
                        f"codex exec exited with code {completed.returncode}",
                        "stdout tail:",
                        self._log_tail(log.path / "events.jsonl"),
                        "stderr tail:",
                        self._log_tail(log.path / "stderr.log"),
                        "last-message tail:",
                        _tail(output),
                    )
                    if part
                )
                raise AgentRunnerError(detail)

            if not output.strip():
                raise AgentRunnerError("codex exec produced no final message")
            return output.strip()

    @staticmethod
    def _log_tail(path: Path) -> str:
        with path.open("rb") as stream:
            stream.seek(0, os.SEEK_END)
            stream.seek(max(0, stream.tell() - 4000))
            return stream.read().decode("utf-8", errors="replace")

    @staticmethod
    def _compose_prompt(request: AgentRunRequest) -> str:
        parts = []
        if request.system_prompt.strip():
            parts.append(
                "Treat the following as the task instructions that govern this run.\n"
                "<task_instructions>\n"
                f"{request.system_prompt.strip()}\n"
                "</task_instructions>"
            )

        if request.allowed_tools is not None:
            tools = ", ".join(request.allowed_tools) or "none"
            parts.append(
                "Tool policy for this run: use only read-only inspection commands "
                f"equivalent to these capabilities: {tools}. Do not edit files."
            )

        parts.append(request.prompt.strip())
        return "\n\n".join(parts).strip() + "\n"


def make_agent_runner(
    provider: str,
    model: Optional[str] = None,
    reasoning_effort: Optional[str] = None,
    executable: str = "codex",
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    max_tokens: int = 4096,
    max_tool_rounds: int = 40,
) -> BaseAgentRunner:
    provider = provider.lower()
    if provider == "claude":
        return ClaudeSdkRunner(model=model)
    if provider == "codex":
        return CodexExecRunner(
            model=model,
            reasoning_effort=reasoning_effort,
            executable=executable,
        )
    if provider == "qwen":
        return QwenOpenAICompatRunner(
            model=model,
            base_url=base_url,
            api_key=api_key,
            max_tokens=max_tokens,
            max_tool_rounds=max_tool_rounds,
        )
    raise AgentRunnerError(
        f"Unsupported agent provider {provider!r}; choose one of: "
        f"{', '.join(SUPPORTED_AGENT_PROVIDERS)}"
    )


class QwenOpenAICompatRunner(BaseAgentRunner):
    """OpenAI-compatible chat-completions provider (e.g. llama.cpp / vLLM serving Qwen).

    The model is READ-ONLY: it cannot write files, so the caller writes the
    final answer to disk. It CAN call a ``read_file`` tool so it can page
    through large diff inputs (the changelog diff for one version is ~200 KB,
    far larger than a single prompt). The tool loop mirrors the OpenAI
    chat-completions ``tools`` contract using only the standard library.
    """

    provider = "qwen"
    supports_file_write_tool = False

    _READ_FILE_TOOL = {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read a text file. Returns 1-indexed, line-numbered content in "
                "'N|content' form, plus total line count. Use offset/limit to "
                "page through large files."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute path of the file to read.",
                    },
                    "offset": {
                        "type": "integer",
                        "description": "1-indexed first line to read. Default 1.",
                        "minimum": 1,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum lines to read. Default 2000.",
                        "minimum": 1,
                        "maximum": 2000,
                    },
                },
                "required": ["path"],
            },
        },
    }

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        max_tokens: int = 4096,
        max_tool_rounds: int = 40,
        request_timeout: int = 600,
    ):
        self.model = model
        self.base_url = (base_url or os.getenv("CHANGELOG_OPENAI_BASE_URL") or "").rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("CHANGELOG_OPENAI_API_KEY") or "no-key"
        self.max_tokens = max_tokens
        self.max_tool_rounds = max_tool_rounds
        self.request_timeout = request_timeout
        self.last_resolved_model = None

    def check_available(self) -> None:
        if not self.base_url:
            raise AgentRunnerError(
                "qwen provider needs a base URL: set CHANGELOG_OPENAI_BASE_URL "
                "or pass --qwen-base-url (e.g. http://sandbox.home:11434/v1)"
            )

    # ── HTTP helper (stdlib only) ──────────────────────────────────────
    def _post(self, path: str, payload: dict, timeout: int) -> dict:
        url = self.base_url + path
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            raise AgentRunnerError(
                f"OpenAI-compatible HTTP {exc.code} from {url}: {_tail(body, 1200)}"
            ) from exc
        except urllib.error.URLError as exc:
            raise AgentRunnerError(f"Could not reach {url}: {exc.reason}") from exc
        except (TimeoutError, OSError) as exc:
            raise AgentRunnerError(f"Request to {url} failed: {exc!r}") from exc

    # ── read_file tool execution ───────────────────────────────────────
    @staticmethod
    def _exec_read_file(args: dict, cwd: Path, read_roots: Sequence[Path]) -> str:
        if not isinstance(args, dict):
            return "ERROR: read_file arguments must be an object."
        path = str(args.get("path", "")).strip()
        if not path:
            return "ERROR: read_file requires a 'path' argument."
        try:
            offset = int(args.get("offset", 1) or 1)
        except (TypeError, ValueError):
            offset = 1
        try:
            limit = int(args.get("limit", 2000) or 2000)
        except (TypeError, ValueError):
            limit = 2000
        limit = max(1, min(limit, 2000))
        p = (cwd / path).resolve()
        if not any(p.is_relative_to(Path(root).resolve()) for root in read_roots):
            return "ERROR: file is outside the allowed source directories."
        if not p.exists():
            return f"ERROR: file not found: {path}"
        if not p.is_file():
            return f"ERROR: not a regular file: {path}"
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception as exc:  # noqa: BLE001
            return f"ERROR: could not read {path}: {exc!r}"
        total = len(lines)
        start = max(1, offset)
        end = min(total, start + limit - 1)
        if start > total:
            return (
                f"FILE {path} — total_lines={total} — "
                f"offset {start} is past the end; nothing to read."
            )
        out_lines = [f"{i + 1}|{lines[i].rstrip(chr(10))}" for i in range(start - 1, end)]
        header = f"FILE {path} — lines {start}-{end} of {total}"
        if end < total:
            header += f" (continue with offset={end + 1})"
        return "\n".join([header, *out_lines])

    def _run(self, request: AgentRunRequest, log: SessionLog) -> str:
        self.check_available()
        if not self.model:
            raise AgentRunnerError("qwen provider needs a model id (e.g. --changelog-model qwen-3.8-27b)")

        messages: list[dict] = []
        if request.system_prompt and request.system_prompt.strip():
            messages.append(
                {"role": "system", "content": request.system_prompt.strip()}
            )
        if request.allowed_tools is not None:
            # Mirror the codex read-only policy: the model may inspect files
            # via read_file but must not be told it can edit anything.
            tools = ", ".join(request.allowed_tools) or "none"
            policy = (
                "\n\nTool policy for this run: you may only read files with the "
                f"read_file tool (capabilities: {tools}). Do not edit any file."
            )
            if messages and messages[0]["role"] == "system":
                messages[0]["content"] += policy
            else:
                messages.insert(0, {"role": "system", "content": policy.strip()})

        messages.append({"role": "user", "content": request.prompt.strip()})
        can_read = bool(set(request.allowed_tools or ()) & {'Read', 'Grep', 'Glob'})
        read_roots = request.read_roots if request.read_roots is not None else [request.cwd]
        deadline = time.monotonic() + request.timeout if request.timeout else None

        last_error = ""
        for _round in range(self.max_tool_rounds):
            payload: dict = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.max_tokens,
                "stream": False,
            }
            # Only offer the tool when the caller actually allows inspection.
            if can_read:
                payload["tools"] = [self._READ_FILE_TOOL]
                payload["tool_choice"] = "auto"

            timeout = self.request_timeout
            if deadline is not None:
                timeout = min(timeout, deadline - time.monotonic())
                if timeout <= 0:
                    raise AgentRunnerError('qwen request deadline exceeded')
            # Only the new messages are logged; repeated context is not copied
            # on every tool round. HTTP auth headers are never recorded.
            if _round == 0:
                log.record("initial_messages", messages)
            data = self._post("/chat/completions", payload, timeout)
            log.record("response", data)
            try:
                choice = data["choices"][0]
                message = choice.get("message") or {}
            except (KeyError, IndexError, TypeError) as exc:
                raise AgentRunnerError(
                    f"Unexpected chat-completions response shape: {_tail(json.dumps(data), 1200)}"
                ) from exc

            if data.get("model"):
                self.last_resolved_model = data["model"]

            tool_calls = message.get("tool_calls") or []
            if tool_calls:
                if not can_read:
                    raise AgentRunnerError('qwen returned tool calls when tools are disabled')
                # Record the assistant tool-call turn, then answer each call.
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.get("content") or "",
                        "tool_calls": tool_calls,
                    }
                )
                for tc in tool_calls:
                    fn = (tc.get("function") or {})
                    name = fn.get("name") or ""
                    raw_args = fn.get("arguments") or "{}"
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
                    except (ValueError, TypeError):
                        args = {}
                    if name == "read_file":
                        result = self._exec_read_file(args, Path(request.cwd), read_roots)
                    else:
                        result = f"ERROR: unknown tool {name!r}; only read_file is available."
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.get("id", ""),
                            "content": result[:60000],
                        }
                    )
                    log.record("tool_result", messages[-1])
                continue

            if choice.get('finish_reason') == 'length':
                raise AgentRunnerError('qwen final answer was truncated by its token limit')
            content = message.get("content")
            if content is None:
                last_error = "model returned an empty final message"
                # Nudge once; some backends return finish_reason=length with
                # an empty body under a low max_tokens.
                messages.append({"role": "user", "content": "Please provide the full answer now."})
                log.record("message", messages[-1])
                if _round >= self.max_tool_rounds - 1:
                    break
                continue
            if not isinstance(content, str) or not content.strip():
                raise AgentRunnerError('qwen returned an empty final answer')
            return content.strip()

        raise AgentRunnerError(
            f"qwen run did not finish within {self.max_tool_rounds} tool rounds "
            f"(last issue: {last_error or 'ran out of rounds'})"
        )


def default_model_for(provider: str, role: str) -> str:
    provider = provider.lower()
    role = role.lower()
    if provider == "claude":
        return (
            "claude-haiku-4-5-20251001"
            if role == "annotation"
            else "sonnet"
        )
    if provider == "codex":
        return "gpt-6-luna" if role == "annotation" else "gpt-6.1-sol"
    if provider == "qwen":
        # The served model id is explicit in the user's Hermes config; default
        # to it so `--agent-provider qwen` works without a separate --model.
        return os.getenv("CHANGELOG_QWEN_MODEL", "qwen-3.8-27b")
    raise AgentRunnerError(f"Unsupported agent provider {provider!r}")
