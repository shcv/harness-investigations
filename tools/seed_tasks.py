#!/usr/bin/env python3
"""Variant A: Pre-seed Claude Code task list with annotation tasks.

Creates a task list directory and populates it with one task per batch.
The coordinator Claude agent reads tasks via TaskList, spawns Haiku agents,
and each Haiku agent writes annotations to batches/batch-NNN-annotations.json.

Usage: python3 seed_tasks.py [version] [task_list_id]
  e.g.: python3 seed_tasks.py v2.1.48 changelog-annotate-v2148
"""
import json
import sys
from pathlib import Path

TASKS_ROOT = Path.home() / ".claude" / "tasks"

TASK_DESCRIPTION_TEMPLATE = """\
Annotate this batch of Claude Code source changes. Write results to:
  {out_path}

Section: {section}
Batch {batch_id} of {total_batches}

Return a JSON array in <result></result> tags with objects having:
- name, summary, importance (1-5), user_facing (bool), feature_flag (str|null),
  component (cli/sdk/mcp/tools/hooks/git/models/auth/config/telemetry/shell/agent/transport/internal),
  change_type (new_feature/enhancement/bug_fix/removal/refactor/documentation/infrastructure),
  disabled (bool), evidence (key code fragment)

importance scale:
1=internal refactor  2=minor internal  3=notable infra/indirect  4=clear user feature  5=major feature

{content}
"""


def seed_tasks(version: str, task_list_id: str, batches_dir: Path) -> int:
    task_dir = TASKS_ROOT / task_list_id
    task_dir.mkdir(parents=True, exist_ok=True)

    batch_files = sorted(
        f for f in batches_dir.glob("batch-*.json")
        if "-annotations" not in f.name
    )
    total = len(batch_files)
    task_ids = []

    for f in batch_files:
        batch = json.loads(f.read_text())
        out_path = f.parent / (f.stem + "-annotations.json")

        # Skip already done
        if out_path.exists():
            continue

        task_id = f"annotate-batch-{batch['id']:03d}"
        task_ids.append(task_id)

        description = TASK_DESCRIPTION_TEMPLATE.format(
            out_path=str(out_path),
            section=batch["section"],
            batch_id=batch["id"],
            total_batches=total,
            content=batch["content"],
        )

        task = {
            "id": task_id,
            "subject": f"Annotate batch {batch['id']:03d} ({batch['section']}, {batch['count']} items)",
            "description": description,
            "status": "pending",
            "blocks": [],
            "blockedBy": [],
        }
        task_path = task_dir / f"{task_id}.json"
        task_path.write_text(json.dumps(task, indent=2))

    print(f"Seeded {len(task_ids)} tasks in {task_dir}")
    print(f"Task list ID: {task_list_id}")
    print("\nRun coordinator with:")
    print(f"  CLAUDE_CODE_TASK_LIST_ID={task_list_id} claude -p '<coordinator-prompt>'")
    return len(task_ids)


COORDINATOR_SYSTEM_PROMPT = """\
You are orchestrating annotation of Claude Code source changes for a changelog.

{total_tasks} annotation tasks are pre-loaded in your task list. Each task contains
a batch of source code diffs and asks you to annotate each change with importance,
component, user_facing status, feature flags, etc.

Your job:
1. Use TaskList to see all pending annotation tasks
2. Create a team of Haiku agents (spawn 4-6 at once for parallelism)
3. Assign tasks to agents — each agent should:
   a. Read its assigned task (TaskGet)
   b. Analyze the diff content in the task description
   c. Write a JSON annotation array to the file path specified in the task
   d. Mark the task complete (TaskUpdate status=completed)
4. Monitor progress; assign new tasks as agents finish
5. Once ALL tasks are complete, read all annotation files from {batches_dir}
6. Filter to importance >= 3, then generate the final changelog

The final changelog should follow the same format as previous changelogs in
{changelog_dir} (read one for reference). Focus on user-facing changes.

Output the final changelog to: {output_file}
"""


def print_coordinator_prompt(version: str, task_list_id: str, batches_dir: Path):
    base = batches_dir.parent.parent.parent  # archive/claude-code
    prompt = COORDINATOR_SYSTEM_PROMPT.format(
        total_tasks="(check TaskList)",
        batches_dir=batches_dir,
        changelog_dir=base / "changelog",
        output_file=base / "changelog" / f"changelog-{version}-variant-a.md",
    )
    print("\n=== Coordinator System Prompt ===")
    print(prompt)
    print("=================================\n")


if __name__ == "__main__":
    version = sys.argv[1] if len(sys.argv) > 1 else "v2.1.48"
    task_list_id = sys.argv[2] if len(sys.argv) > 2 else f"changelog-annotate-{version.replace('.', '')}"
    batches_dir = Path(f"archive/claude-code/changes/{version}/batches")

    if not batches_dir.exists():
        print(f"Error: {batches_dir} not found")
        sys.exit(1)

    count = seed_tasks(version, task_list_id, batches_dir)
    if count > 0:
        print_coordinator_prompt(version, task_list_id, batches_dir)
