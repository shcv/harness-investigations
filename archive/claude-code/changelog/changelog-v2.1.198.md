# Changelog for version 2.1.198

## Summary

This release ships a significantly expanded `claude plugin eval` framework for testing plugins with structured eval suites, three new artifact-publishing skills (code walkthrough, PR walkthrough, plan artifact), and `/auto-mode-setup` — a guided workflow that triggers automatically when you first enter auto mode. The `/agents` interactive wizard is retired in favour of asking Claude directly; SSH sessions gain model selection support; and the Node.js minimum version rises to 22.


## New Features


### `claude plugin eval` — Plugin Evaluation Framework (Early Access)

What: A full CLI command for running structured, ablation-based eval suites against plugins. Guides you through writing graders and measuring whether a plugin actually improves Claude's answers.

Usage:
```bash
# Guided interview — walks you through building an eval suite
claude plugin eval init

# Blank template for a single case
claude plugin eval init --bare <case-name>

# Run the full eval suite
claude plugin eval .

# Run with ablation to measure plugin uplift
claude plugin eval . --ablation with-without

# Filter by tag or name
claude plugin eval . --tag smoke --threshold 0.9

# Custom judge model, cost ceiling, run count
claude plugin eval . --judge-model sonnet --max-cost-usd 2.00 --runs 5
```

Details:
- The interview reads the plugin's README, SKILL.md, and commands, asks you to define quality criteria, sources inputs (real traffic preferred, synthesis fallback), and proposes grader rows (regex, file_exists, llm, baseline, tool_order, tool_used types).
- Ablation mode (`--ablation with-without`) runs each case twice — once with the plugin, once without — and reports Δ (uplift). This is the headline number that makes results meaningful.
- Results are written to `evals/results/<timestamp>/aggregate-result.json` by default; `--output-dir` overrides.
- `--keep-temp` preserves each run's sandbox (workspace + `trace.jsonl`) for debugging.
- `--scaffold` runs each case's `scaffold_script` (opt-in; only use on cases you authored).
- Exit code 2 if any case score falls below `--threshold` (default 1.0) — CI-friendly.
- Currently in early access.

Evidence: Guided interview system prompt (search for `"You are running inside \`claude plugin eval init\`"`); CLI flag parsing (search for `"--ablation must be"`)


### `/auto-mode-setup` — Guided Auto Mode Configuration

What: A skill that Claude automatically triggers the first time you enter auto mode. It explores your repo, CLAUDE.md, and recent sessions, then checks its draft configuration with you before writing anything.

Usage:
```bash
# Re-run anytime to revisit your auto mode configuration
/auto-mode-setup
```

Details:
- Fires automatically in auto mode on new sessions that haven't been configured yet.
- Proposes trusted repos, domains, buckets, and registries from what it finds.
- After setup, run `/auto-mode-setup` again whenever the environment changes.

Evidence: Auto-trigger logic (search for `"/auto-mode-setup"`); skill description (search for `"Guided setup and customisation for auto mode"`)


### `/code-walkthrough` — Interactive Code Explainer Artifacts

What: New slash command that generates a self-contained HTML artifact explaining code to a newcomer — expandable sections, annotated snippets, and "why this matters" callouts.

Usage:
```bash
/code-walkthrough <path | PR# | ref>
/code-walkthrough src/auth/
/code-walkthrough 1234
/code-walkthrough HEAD~3
```

Details:
- Produces a single-file HTML page with a one-paragraph summary, a map of the main pieces, per-piece `<details>` blocks with annotated code and "why this matters" callouts, and an open-questions section.
- Pitches the writing at "capable engineer, never seen this codebase" — not at experts.
- If no target is given, Claude asks one clarifying question before proceeding.
- The artifact footer contains a link so the reader can bring it back into Claude Code for iteration.

Evidence: Command registration (search for `"Generate an interactive walkthrough artifact for code"`); prompt scaffolding (search for `"Walkthrough target:"`)


### PR Walkthrough Skill

What: A skill that generates a shareable HTML artifact explaining a pull request — what changed, why, and a reviewer-oriented before/after narrative.

Usage:
```bash
# Invoke via the skill menu or ask Claude directly
# "Generate a PR walkthrough for PR #1234"
```

Details:
- Produces a self-contained HTML page a reviewer can read before opening the diff.
- Covers: what changed, why the change is being made, and where to focus review effort.
- Traces the diff actually does rather than inferring from names.
- Includes an "unclear to me" section rather than guessing at ambiguous changes.

Evidence: Skill registration (search for `"Generate a shareable walkthrough artifact for a pull request"`); PR walkthrough prompt (search for `"Produce a **shareable PR walkthrough artifact**"`)


### `plan-artifact` Skill — Publish Plans as Shareable Artifacts

What: A skill to publish an implementation plan, design doc, or RFC as a shareable HTML artifact.

Usage:
```bash
/plan share          # built-in publish from plan approval dialog
# or ask Claude: "publish this plan as an artifact"
```

Details:
- Use when asked to publish a plan manually, restyle an existing plan artifact, or customize what the built-in `/plan share` publish produced.
- The built-in approval-dialog publish path fills the same template automatically; this skill is for hand-initiated or customized cases.

Evidence: Skill registration (search for `"Publish a plan as a shareable Artifact"`); description (search for `"plan-artifact"`)


### `/design consent | /design revoke` — Design Agent Access Management

What: Two new commands to grant or revoke Claude agent access to your Claude Design projects, replacing the older `/design-login` flow.

Usage:
```bash
/design consent    # opens browser to grant access
/design revoke     # removes the server-side access grant
```

Details:
- When a tool requests Design access, Claude now shows a consent prompt: "Connect to Claude Design? Claude can read and edit your Design projects from this tool. Change anytime with /design revoke."
- Consent is a server-side grant; `/design revoke` clears it.
- Attempting Design operations without consent now produces a clear message directing the user to run `/design consent`.

Evidence: Consent command strings (search for `"Usage: /design consent | /design revoke"`); grant message (search for `"Design agent access granted for your Claude Design projects"`)


### SSH Sessions Now Support Model Selection

What: The model catalog capability is now enabled for SSH-connected sessions, allowing `/model` to work over SSH.

Details:
- Previously `modelCatalog` was disabled (`!1`) for SSH connections — model selection was unavailable.
- Now enabled (`!0`): the session queries the worker for its available models, and `/model` works as in CCR sessions.
- The old `Use /model to change the model in cloud sessions` hint now applies to SSH sessions too.

Evidence: Capability table change — `ssh: { modelCatalog: !0 }` (was `!1`, search for `"modelCatalog"` in capability map)


## Improvements


### `/agents` Wizard Retired

The interactive `/agents` management UI has been removed. Running `/agents` now shows a short message:

> The /agents wizard has been removed. Ask Claude to create or update subagents for you (e.g. "create a code-reviewer subagent that ..."), or edit the files directly:
> - `.claude/agents/` (this project)
> - `~/.claude/agents/` (all projects)
>
> Docs: https://code.claude.com/docs/en/sub-agents

The "Use /agents to optimize specific tasks" tip is also updated to "Ask Claude to create subagents for specific tasks."

Evidence: Replacement handler (search for `"The /agents wizard has been removed"`); tip text update (search for `"Ask Claude to create subagents for specific tasks"`)


### TaskStop Now Accepts Agent Names and Team IDs

The `TaskStop` tool (used to stop background tasks and agents) now accepts agent IDs and teammate names, not just numeric task IDs.

Details:
- Pass `"name@team"` to stop a team teammate by agent ID.
- Pass the bare agent name to stop a named background agent.
- When a name is ambiguous — matching both a teammate and a background agent — Claude now reports: `"<name>" matches both teammate <id> and background agent <id>. Use the full agent ID (name@team) for the teammate or the task ID for the background agent.`

Evidence: TaskStop description update (search for `"To stop an agent-team teammate, pass its agent ID"`); disambiguation function (search for `"matches both teammate"`)


### Node.js Minimum Version Raised to 22

Claude Code now requires Node.js 22 or higher. If an older Node.js is detected at startup, the error message reads:

> Error: Claude Code requires Node.js version 22 or higher.

Previously the minimum was Node.js 18.

Evidence: Error string (search for `"Error: Claude Code requires Node.js version 22 or higher."`)


### New Tip for `/code-review low`

A new contextual tip appears after you've used code-review skills a few times:

> For a fast, cheap code review, try `/code-review low`. It runs the built-in skill at its lightest effort level.

The tip fires with an 8-session cooldown and only when a code-review–flavored skill has been invoked.

Evidence: Tip definition (search for `"code-review-low-fast"`)


### `--bg` + `--print` Conflict Now Errors Clearly

Using `--bg` and `--print` together now produces a clear error:

> --bg and --print conflict: --print never starts the interactive session that `claude agents` attaches to, so the job would be unattachable. The prompt is the positional — drop --print: `claude --bg '<task>'`.

Evidence: Conflict check (search for `"--bg and --print conflict"`)


### Background Attach UI — Clearer Keyboard Help

The text shown when attaching to a background session was updated from:

> Open the background session in this terminal. Detach with Ctrl+Z; the session keeps running.

to:

> Open the background session in this terminal. ← returns to agent view, Ctrl+Z drops back to your shell. The session keeps running either way.

Evidence: UI string update (search for `"← returns to agent view, Ctrl+Z drops back to your shell"`)


### Atomic Write Security Hardening

File writes inside sandboxed commands now go through a staging directory (`~/.cc-writes/`) whose identity (device + inode) is verified before every write. If the directory is replaced or its path manipulated, the write is refused and a `StagingDirTamperedError` is raised, preventing TOCTOU-style attacks on atomic file operations.

Evidence: Tamper check (search for `"Staging dir ${e} identity changed"`); error class (search for `"StagingDirTamperedError"`)


### CA Certificate Expiry Filtering

Expired certificates are now silently filtered out of the system CA store at startup, with a diagnostic log:

> CA certs: Dropped N expired certificate(s) from system store

Evidence: Filter function (search for `"CA certs: Dropped"`)


### Agent Launch Messages Trimmed to Essentials

Internal metadata strings from `Task` and `Agent` tool results were updated to more explicitly instruct Claude not to echo them:

- `"Async agent launched successfully. (This tool result is internal metadata — never quote or paste any part of it, including the agentId below, into a user-facing reply.) agentId:"`

Previously the instructions were shorter. The updated wording prevents raw tool result IDs leaking into user-facing responses.

Evidence: Agent launch string (search for `"never quote or paste any part of it, including the agentId below"`)


### `run_in_background` Default Documented Clearly

The Agent tool description now states explicitly:

> Subagents run in the background by default; you'll be notified when one completes. Pass `run_in_background: false` for a synchronous run when you need the result before continuing.

Previously the default was less clearly communicated.

Evidence: Tool description update (search for `"Subagents run in the background by default"`)


## Bug Fixes

- Git `commondir` path traversal: UNC paths and paths that escape the worktree root via symlinks in `.git/commondir` are now rejected rather than silently followed (search for `"Staging dir parent"` and `kB()` path containment logic)
- Hook error messages for unknown hook events now list valid event names: `"unknown hook event. Valid events: ..."` (search for `"unknown hook event. Valid events:"`)
- Hooks with malformed structure now report the specific path and reason rather than a generic parse failure (search for `"must be an array of matchers; received"`)
- PowerShell hook commands that reference `$CLAUDE_PROJECT_DIR` now warn that PowerShell reads bare `$VAR` as undefined — the warning directs users to use `$env:CLAUDE_PROJECT_DIR` instead (search for `"PowerShell hook command references $CLAUDE_PROJECT_DIR"`)
- OAuth profile responses that fail shape validation are now logged and discarded rather than silently accepted (search for `"OAuth profile: response body failed shape validation"`)


Generated with:
- tool: `harness-investigations@03136fb-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.198.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.198.txt`
