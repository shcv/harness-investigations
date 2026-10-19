#!/usr/bin/env python3
"""Parallel annotation of change batches using the configured agent provider.

Reads batches from archive/claude-code/changes/{version}/batches/
Writes batch-NNN-annotations.json alongside each batch file.

Usage: python3 annotate_changes.py [version]
  e.g.: python3 annotate_changes.py v2.1.48
"""
import asyncio
import hashlib
import json
import os
import re
from pathlib import Path

from agent_runner import (AgentRunRequest, AgentRunnerError, DEFAULT_AGENT_PROVIDER,
                          SUPPORTED_AGENT_PROVIDERS, default_model_for,
                          load_project_env, make_agent_runner)
from pipeline_io import write_json

load_project_env()
SEMAPHORE_LIMIT = 4

ANNOTATION_PROMPT = """\
Analyze these changes to the coding harness source code and classify each one.
Return a JSON array between <result></result> tags.

CRITICAL — "removed" section semantics: Entries in the "removed" section mean those
specific code bodies had NO close match in the new version. This does NOT mean the
feature was deleted — it may have been reorganized, reimplemented, or renamed such
that the diff tool couldn't match it. Only use change_type="removal" if the code
content clearly indicates a capability is gone: e.g., a CLI flag literal removed,
a tool name constant that disappears, or a user-facing error string no longer present.
When uncertain, prefer change_type="refactor" over "removal".

For each change, output an object with:
- "name": identifier name (use the [name] from the diff header)
- "summary": 1-2 sentence plain-English description of what this change does
- "importance": integer 1-5:
    1 = internal refactoring, no user impact
    2 = minor internal change, unlikely visible to users
    3 = notable improvement or infrastructure indirectly affecting users
    4 = clear new user-facing feature or significant behavior change
    5 = major feature, breaking change, or release-defining capability
- "user_facing": true if change produces visible output, adds CLI flags/options,
    new tools, or changes behavior users observe directly
- "feature_flag": string name if gated by a tengu_* flag — look for calls like
    r8("tengu_foo", !1). Use null if no feature flag.
- "disabled": true ONLY if the flag default is explicitly !1 or false
    (r8("tengu_foo", !1) → disabled=true; r8("tengu_foo", !0) → disabled=false)
- "component": pick the MOST SPECIFIC category that applies:
    - models: model capability fields (supportsAdaptiveThinking, effortLevels),
               model version strings, thinking parameters, pricing
    - sdk: ClaudeAgentOptions fields, query() params, SDK-exposed APIs,
            promptSuggestions — things SDK callers configure
    - tools: built-in tool definitions and their schemas/descriptions
              (Bash, Read, Write, Grep, Glob, AskUserQuestion, Skill, TodoWrite,
               CreateWorktree, ListMcpResources, TaskCreate, TaskUpdate, etc.)
    - hooks: hook event types and handlers (PreToolUse, PostToolUse,
              ConfigChange, TaskCompleted, SubagentStop, HttpHook)
    - git: git integration, worktrees, commits, branches, diffs
    - mcp: Model Context Protocol servers, tool results, auth, resources
    - cli: command-line flags, REPL UI, startup flow, shell integration,
            slash commands, session management
    - auth: authentication, OAuth, API keys, login/logout flows
    - config: settings schemas, CLAUDE.md loading/excludes, policy enforcement
    - agent: agent coordination, task management, teams, background agents
    - shell: shell execution, bash/powershell providers, shell detection
    - transport: WebSocket, HTTP, SSE, network communication
    - telemetry: logging, analytics, event tracking
    - internal: refactoring with no user-visible effect (use as last resort)
- "change_type": new_feature | enhancement | bug_fix | removal | refactor |
    documentation | infrastructure
- "evidence": 1-2 key code fragments supporting your classification

Grouping: combine related sub-functions into one entry when clearly part of one feature.
Structural changes often represent feature wiring — a new field or parameter being passed
through usually enables a specific user-visible capability; identify what that is.
A 100% similarity score does not prove unchanged behavior. Inspect the actual
code changes; skip only entries with no substantive content change.

Section: {section}
Batch {batch_id} of changes:

{content}
"""


def validate_annotations(annotations: object) -> list[dict]:
    """Reject malformed model output before it can become a completed cache."""
    if not isinstance(annotations, list):
        raise AgentRunnerError("Annotations must be a JSON array")
    for index, ann in enumerate(annotations):
        if not isinstance(ann, dict):
            raise AgentRunnerError(f"Annotation {index} must be an object")
        for key in ("name", "summary", "component", "change_type"):
            if not isinstance(ann.get(key), str) or not ann[key].strip():
                raise AgentRunnerError(f"Annotation {index} needs a nonempty {key}")
        importance = ann.get("importance")
        if type(importance) is not int or not 1 <= importance <= 5:
            raise AgentRunnerError(f"Annotation {index} importance must be an integer from 1 to 5")
        for key in ("user_facing", "disabled"):
            if not isinstance(ann.get(key), bool):
                raise AgentRunnerError(f"Annotation {index} {key} must be a boolean")
        if ann.get("feature_flag") is not None and not isinstance(ann["feature_flag"], str):
            raise AgentRunnerError(f"Annotation {index} feature_flag must be a string or null")
        evidence = ann.get("evidence")
        if not (isinstance(evidence, str) or
                isinstance(evidence, list) and all(isinstance(item, str) for item in evidence)):
            raise AgentRunnerError(f"Annotation {index} evidence must be text or a list of text")
    return annotations


def parse_annotations(output: str) -> list[dict]:
    match = re.search(r"<result>(.*?)</result>", output, re.DOTALL)
    text = match.group(1).strip() if match else output.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
    try:
        return validate_annotations(json.loads(text))
    except json.JSONDecodeError as exc:
        raise AgentRunnerError(f"Invalid annotation JSON: {exc}") from exc


def batch_paths(batches_dir: Path) -> list[Path]:
    return sorted(path for path in batches_dir.glob("batch-*.json")
                  if re.fullmatch(r"batch-[0-9]+\.json", path.name))


async def annotate_batches(
    batches_dir: Path,
    *,
    agent_provider: str = DEFAULT_AGENT_PROVIDER,
    model: str | None = None,
    codex_reasoning_effort: str = "low",
    codex_bin: str = "codex",
    qwen_base_url: str | None = None,
    cwd: Path | None = None,
    min_importance: int = 2,
    timeout: int = 300,
) -> list[dict]:
    """Annotate current batches through one provider adapter, with resumable caches.

    Successful batches survive a failed run, but partial results never become a
    summary. Each concurrent call owns its runner and model/transcript state.
    """
    agent_provider = agent_provider.lower()
    model = model or default_model_for(agent_provider, "annotation")
    cwd = (cwd or Path.cwd()).resolve()
    files = batch_paths(batches_dir)
    if not files:
        return []
    settings = {
        "schema_version": 1,
        "provider": agent_provider,
        "model": model,
        "reasoning_effort": codex_reasoning_effort if agent_provider == "codex" else None,
        "executable": codex_bin if agent_provider == "codex" else None,
        "base_url": (qwen_base_url or os.getenv("CHANGELOG_OPENAI_BASE_URL"))
                    if agent_provider == "qwen" else None,
        "prompt_sha256": hashlib.sha256(ANNOTATION_PROMPT.encode()).hexdigest(),
    }
    # Preserve the serial Codex policy; SDK/HTTP providers can overlap calls.
    semaphore = asyncio.Semaphore(1 if agent_provider == "codex" else SEMAPHORE_LIMIT)

    async def annotate_one(path: Path) -> list[dict]:
        batch = json.loads(path.read_text(encoding="utf-8"))
        identity = {**settings, "batch_sha256": hashlib.sha256(
            json.dumps(batch, sort_keys=True, ensure_ascii=False).encode()).hexdigest()}
        out_path = path.with_name(path.stem + "-annotations.json")
        annotations = None
        if out_path.exists():
            try:
                cached = json.loads(out_path.read_text(encoding="utf-8"))
                if isinstance(cached, dict) and cached.get("_generation") == identity:
                    annotations = validate_annotations(cached.get("annotations"))
            except (ValueError, AgentRunnerError):
                pass  # A legacy, stale, or damaged cache must be regenerated.
        if annotations is None:
            async with semaphore:
                runner = make_agent_runner(
                    agent_provider, model=model,
                    reasoning_effort=settings["reasoning_effort"],
                    executable=codex_bin, base_url=qwen_base_url,
                )
                prompt = ANNOTATION_PROMPT.format(section=batch["section"],
                                                  batch_id=batch["id"], content=batch["content"])
                print(f"Annotating batch {batch['id']:03d} with {agent_provider}:{model}", flush=True)
                output = await asyncio.to_thread(runner.run, AgentRunRequest(
                    prompt=prompt, cwd=cwd, allowed_tools=[], timeout=timeout,
                ))
                annotations = parse_annotations(output)
                write_json(out_path, {**batch, "annotations": annotations,
                                      "_generation": identity})
        return [{**ann, "_batch_id": batch["id"], "_section": batch["section"]}
                for ann in annotations if ann["importance"] >= min_importance]

    results = await asyncio.gather(*(annotate_one(path) for path in files), return_exceptions=True)
    errors = [(path.name, result) for path, result in zip(files, results)
              if isinstance(result, Exception)]
    if errors:
        detail = "; ".join(f"{name}: {error}" for name, error in errors)
        raise AgentRunnerError(f"{len(errors)}/{len(files)} annotation batches failed: {detail}")
    return [ann for result in results for ann in result]


async def main(
    version: str,
    batches_dir: Path | None = None,
    agent_provider: str = DEFAULT_AGENT_PROVIDER,
    model: str | None = None,
    codex_reasoning_effort: str = "low",
    codex_bin: str = "codex",
):
    if batches_dir is None:
        batches_dir = Path(f"archive/claude-code/changes/{version}/batches")
    if not batch_paths(batches_dir):
        raise AgentRunnerError(f"No batches in {batches_dir}. Run slice_changes.py first.")
    summary_name = f"annotations-{version}"
    if batches_dir.name != "batches":
        summary_name += f"-{batches_dir.name}"
    summary_path = batches_dir.parent / f"{summary_name}.json"
    # Invalidate a previous summary before attempting a new configuration.
    summary_path.unlink(missing_ok=True)
    filtered = await annotate_batches(
        batches_dir, agent_provider=agent_provider, model=model,
        codex_reasoning_effort=codex_reasoning_effort, codex_bin=codex_bin,
    )
    write_json(summary_path, filtered)
    print(f"Wrote {len(filtered)} annotations to {summary_path}")
    return filtered


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("version", nargs="?", default="v2.1.48")
    p.add_argument("--batches-dir", type=Path, help="Override default batches directory path")
    p.add_argument("--agent-provider", choices=SUPPORTED_AGENT_PROVIDERS,
                   default=os.getenv("CHANGELOG_AGENT_PROVIDER") or os.getenv("CHANGELOG_AGENT")
                   or DEFAULT_AGENT_PROVIDER)
    p.add_argument("--model", default=os.getenv("CHANGELOG_ANNOTATION_MODEL"),
                   help="Annotation model; defaults to Luna for Codex")
    p.add_argument("--codex-reasoning-effort", choices=("low", "medium", "high", "xhigh"),
                   default=os.getenv("CHANGELOG_CODEX_ANNOTATION_REASONING_EFFORT") or "low")
    p.add_argument("--codex-bin", default=os.getenv("CHANGELOG_CODEX_BIN") or "codex")
    args = p.parse_args()
    try:
        asyncio.run(main(args.version, args.batches_dir, agent_provider=args.agent_provider,
                         model=args.model, codex_reasoning_effort=args.codex_reasoning_effort,
                         codex_bin=args.codex_bin))
    except (AgentRunnerError, OSError, ValueError) as exc:
        p.exit(1, f"Annotation failed: {exc}\n")
