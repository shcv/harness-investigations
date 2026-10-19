#!/usr/bin/env python3
"""Generate a changelog from pre-computed change annotations.

Takes the filtered annotations-{version}.json (output of annotate_changes.py)
and uses the configured agent provider to generate the final changelog.

Usage: python3 generate_annotated_changelog.py [version] [--min-importance N]
  e.g.: python3 generate_annotated_changelog.py v2.1.48
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from annotation_summary import format_annotation_summary
from agent_runner import (AgentRunRequest, DEFAULT_AGENT_PROVIDER, SUPPORTED_AGENT_PROVIDERS,
                          default_model_for, load_project_env, make_agent_runner)

load_project_env()

MIN_IMPORTANCE = 2
SYSTEM_PROMPT_PATH = Path("archive/claude-code/changelog/system-prompt.md")


async def generate(
    version: str,
    min_importance: int = MIN_IMPORTANCE,
    agent_provider: str = DEFAULT_AGENT_PROVIDER,
    model: str | None = None,
    codex_reasoning_effort: str = "medium",
    codex_bin: str = "codex",
):
    changes_dir = Path(f"archive/claude-code/changes/{version}")
    annotations_file = changes_dir / f"annotations-{version}.json"
    changelog_dir = Path("archive/claude-code/changelog")
    output_file = changelog_dir / f"changelog-{version}-annotated.md"

    if not annotations_file.exists():
        print(f"Error: {annotations_file} not found. Run annotate_changes.py first.")
        sys.exit(1)

    annotations = json.loads(annotations_file.read_text())
    filtered = [a for a in annotations if a.get("importance", 0) >= min_importance]
    print(f"Loaded {len(annotations)} annotations, {len(filtered)} at importance >= {min_importance}")

    system_prompt = SYSTEM_PROMPT_PATH.read_text() if SYSTEM_PROMPT_PATH.exists() else ""

    user_prompt = f"""Generate a changelog for Claude Code {version}.

{format_annotation_summary(filtered, version)}

Generate the changelog following the standard format from the system prompt.
Return the complete Markdown document as your final answer. Do not edit files.
You do NOT need to read source files — the pre-analyzed changes above are your primary input.
However, you may read the prettified source file (pretty/pretty-{version}.js) if you want to
verify specific details or find additional context for important changes.
"""

    print(f"\nGenerating annotated changelog for {version}...")
    runner = make_agent_runner(
        agent_provider,
        model=model or default_model_for(agent_provider, "changelog"),
        reasoning_effort=codex_reasoning_effort
        if agent_provider == "codex"
        else None,
        executable=codex_bin,
    )
    runner.check_available()

    result = await asyncio.to_thread(
        runner.run,
        AgentRunRequest(
            prompt=user_prompt,
            system_prompt=system_prompt,
            allowed_tools=["Read"],
            cwd=Path("archive/claude-code").resolve(),
        ),
    )

    changelog_dir.mkdir(parents=True, exist_ok=True)
    if not result.lstrip().startswith("# "):
        result = f"# Changelog for version {version.removeprefix('v')}\n\n{result}"
    output_file.write_text(result, encoding="utf-8")
    print(f"Written to {output_file}")


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("version", nargs="?", default="v2.1.48")
    p.add_argument("min_importance", nargs="?", type=int, default=MIN_IMPORTANCE)
    p.add_argument("--min-importance", dest="min_importance_option", type=int)
    p.add_argument(
        "--agent-provider",
        choices=SUPPORTED_AGENT_PROVIDERS,
        default=os.getenv("CHANGELOG_AGENT_PROVIDER") or os.getenv("CHANGELOG_AGENT")
        or DEFAULT_AGENT_PROVIDER,
        help="Agent provider. Default: CHANGELOG_AGENT_PROVIDER or codex",
    )
    p.add_argument(
        "--model",
        default=None,
        help="Changelog model. Default: provider-specific or CHANGELOG_AGENT_MODEL",
    )
    p.add_argument(
        "--codex-reasoning-effort",
        choices=("low", "medium", "high", "xhigh"),
        default=os.getenv("CHANGELOG_CODEX_REASONING_EFFORT") or "medium",
    )
    p.add_argument(
        "--codex-bin",
        default=os.getenv("CHANGELOG_CODEX_BIN") or "codex",
    )
    args = p.parse_args()
    model = args.model or os.getenv("CHANGELOG_AGENT_MODEL") or os.getenv("CHANGELOG_CHANGELOG_MODEL") or default_model_for(
        args.agent_provider, "changelog"
    )
    asyncio.run(
        generate(
            args.version,
            args.min_importance_option if args.min_importance_option is not None else args.min_importance,
            agent_provider=args.agent_provider,
            model=model,
            codex_reasoning_effort=args.codex_reasoning_effort,
            codex_bin=args.codex_bin,
        )
    )
