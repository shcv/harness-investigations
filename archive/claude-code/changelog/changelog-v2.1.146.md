# Changelog for version 2.1.146

## Summary
Claude Code 2.1.146 adds a new `/code-review` skill for multi-agent cleanup reviews, with `/simplify` retained as an alias. The largest diff-backed change is a new Workflow orchestration system for deterministic multi-agent scripts, but it is gated behind `CLAUDE_CODE_WORKFLOWS` and `tengu_workflows_enabled`, so it should be treated as in development or opt-in rather than generally enabled.


### `/code-review` Skill
What: A new user-invocable `/code-review` skill reviews changed code for reuse, quality, and efficiency, then fixes confirmed issues.

Usage:
```bash
/code-review
/code-review high
/simplify xhigh
```

Details:
- `/simplify` is preserved as an alias, but the primary command is now `code-review`.
- The command accepts an optional effort level: `low`, `medium`, `high`, `xhigh`, or `max`.
- When an effort is supplied, the prompt tells each of the three review agents to apply that level of rigor.
- Unrecognized effort strings are ignored with a clear valid-values message.

Evidence: `code-review` skill registration is present only in v2.1.146 (search for `"name: \"code-review\""`, `"aliases: [\"simplify\"]"`, `"argumentHint: \"[low|medium|high|xhigh|max]\""`, and `"Ignoring unrecognized effort"`).


### More Reliable Version Checks and Update Fetches
What: Update checks now retry transient failures before giving up, with clearer attempt counts in logs and telemetry.

Details:
- GCS version fetches now retry and log `Failed to fetch ... from GCS on attempt`.
- Binary-repository version checks now retry and record the attempt count, platform, channel, timeout status, and HTTP status.
- Final failure messages now include the number of attempts made.

Evidence: retry wrapper and version-check messages (search for `"Version check failed on attempt"`, `"Failed to fetch ${H} from GCS on attempt"`, and `"after ${_} attempt(s)"`).


### Native Binary Download Hardening
What: Native binary downloads now retry checksum mismatches as well as stalled downloads, and the stall timeout was extended.

Details:
- Previous builds retried stalled downloads after `Download stalled on attempt`.
- v2.1.146 also retries checksum mismatch failures with `Download checksum mismatch on attempt`.
- The stall timeout message changed from 60 seconds to 120 seconds, reducing false stalls on slow connections.

Evidence: binary download retry path (search for `"Download ${D ? \"checksum mismatch\" : \"stalled\"} on attempt"` and `"Download stalled: no data received for 120 seconds"`).


### Clearer Image Attachment Failures
What: Image resizing failures now distinguish “processor unavailable” from “image too large” when dimensions cannot be verified.

Details:
- If native image processing is unavailable but the file header exposes dimensions within API limits, Claude Code can still fall back to sending the original image.
- If dimensions cannot be read, the error now asks the user to convert the image to PNG, JPEG, GIF, or WebP.
- This should make attachment failures easier to fix without guessing whether the issue is format, dimensions, or local image-processing support.

Evidence: image fallback and error text (search for `"image processing is unavailable and dimensions could not be read from the file header"` and `"Please convert the image to PNG, JPEG, GIF, or WebP"`).


### Better Managed-Settings Login Error
What: Machines with managed settings that require first-party login now get a targeted error when a non-OAuth auth method is active.

Details:
- The old path validated managed organization settings only after detecting first-party auth.
- v2.1.146 explicitly rejects third-party provider, API key, auth token, or `apiKeyHelper` auth when managed settings require first-party login.
- The message tells users to remove the non-OAuth configuration and run `claude auth login`.

Evidence: managed-settings auth check (search for `"This machine's managed settings require a first-party login"` and `"Remove the non-OAuth configuration and run: claude auth login"`).


## Bug Fixes

- Prevented isolated agent worktree launches from silently falling back into the parent repo when the worktree directory is missing after creation. Evidence: worktree guard (search for `"Refusing to launch agent in parent repo"` and `"Worktree directory does not exist at"`).

- On Windows, worktree removal now unlinks top-level reparse-point symlinks before forced removal, reducing cleanup failures for agent worktrees. Evidence: Windows cleanup path (search for `"[worktree] unlinked top-level reparse point before removal"`).

- Workflow/subagent throttling now backs off once for degraded throttle responses before giving up, reducing unnecessary agent abandonment on transient throttle states. Evidence: throttling retry path (search for `"sleeping 45s before retry"`, `"(throttle-retry)"`, and `"giving up on throttle backoff"`).


## In Development

Features with infrastructure added but not yet enabled for all users. These are shipped dark or opt-in and may become available in future versions.


### Workflow Orchestration [In Development]
What: A new `Workflow` tool can run deterministic JavaScript orchestration scripts that spawn subagents, group them into phases, pipeline work, enforce structured outputs, and return cached results on resume.

Status: Opt-in and feature-gated. The tool is disabled unless `CLAUDE_CODE_WORKFLOWS` is truthy, then additionally controlled by `tengu_workflows_enabled` with a default of true.

Usage:
```bash
CLAUDE_CODE_WORKFLOWS=1 claude
```

```js
Workflow({name: "review-branch"})
Workflow({scriptPath: "/path/to/workflow.js", resumeFromRunId: "wf_abc123"})
```

Details:
- Scripts must start with `export const meta = { name, description, phases }`.
- Script helpers include `agent()`, `parallel()`, `pipeline()`, `phase()`, `log()`, `budget`, and nested `workflow()`.
- `resumeFromRunId` reuses completed `agent()` calls when the script prefix is unchanged.
- Determinism is enforced by rejecting `Date.now()`, `Math.random()`, and argless `new Date()`.
- Built-in workflows include code review, bug hunting, bug fixing, dashboard generation, documentation generation, root-cause investigation, deep research, planning, and autopilot-style task execution.
- Remote workflow support exists for some bundled workflows when remote mode is active.

Evidence: Workflow tool and gate (search for `"CLAUDE_CODE_WORKFLOWS"`, `"tengu_workflows_enabled"`, `"Execute a workflow script that orchestrates multiple subagents deterministically"`, `"resumeFromRunId"`, and `"Workflow scripts must be deterministic"`).


### `/workflows` History Browser [In Development]
What: A new `/workflows` command browses running and completed workflow runs, including progress, transcript paths, script files, and controls for running workflows.

Status: Same Workflow gate as above: requires `CLAUDE_CODE_WORKFLOWS` and `tengu_workflows_enabled`.

Usage:
```bash
/workflows
```

Details:
- Shows running and completed workflow history.
- Supports viewing workflow details, stopping a running workflow, saving a script, and resuming from a saved script/run ID.
- Completed workflow snapshots can be loaded back into task state.

Evidence: `/workflows` command (search for `"Browse workflow history (running and completed)"`, `"No workflows in this session."`, `"Workflow saved to"`, and `"To resume after editing the script"`).


### Saved and Plugin-Provided Workflows [In Development]
What: Workflows can be saved as `.js` files and loaded from user, project, or plugin workflow directories.

Status: Same Workflow gate as above. Plugin manifest schema support is present, but the user-facing system depends on Workflow enablement.

Usage:
```text
~/.claude/workflows/<name>.js
.claude/workflows/<name>.js
```

Details:
- Saved workflows can be invoked as `/<name>` or `Workflow({name: "<name>"})`.
- Plugin manifests can declare `workflows` as a directory, file path, or list of paths.
- If a plugin has both a default `workflows/` directory and an explicit manifest `workflows` field, the default folder is treated as shadowed by the manifest.

Evidence: saved and plugin workflow loading (search for `"Workflow saved to"`, `"Path to a workflows directory or .js file"`, `"Total plugin workflows loaded"`, and `"workflows from plugin"`).


### Workflow Permission Review [In Development]
What: Workflow execution has a dedicated permission dialog that previews the script or a phase diagram before running.

Status: Same Workflow gate as above.

Details:
- Unknown workflows default to asking permission with `Review workflow before running`.
- Named workflows can be allowed persistently through permission rules.
- The dialog can show a workflow diagram, raw script, args, estimated agent count, and phase structure.
- Users can edit the script in `$EDITOR` with `ctrl+g` before approval.

Evidence: workflow permission UI (search for `"Review workflow before running"`, `"Run this workflow?"`, `"View workflow diagram"`, `"View raw script"`, and `"ctrl+g to edit script in $EDITOR"`).


### `ultrawork` Trigger [In Development]
What: A new `ultrawork` keyword can signal explicit user opt-in for Workflow-based multi-agent orchestration.

Status: Same Workflow gate as above. The detector and reminder are only active when Workflows are enabled.

Details:
- When enabled, user prompts containing `ultrawork` produce a system reminder telling Claude to use the Workflow tool.
- The Workflow tool prompt says the keyword is one valid explicit opt-in signal for multi-agent orchestration.
- Without the Workflow gate enabled, the trigger is not active.

Evidence: `ultrawork` request attachment (search for `"The user included the keyword \"ultrawork\""`, `"tengu_ultrawork"`, and `"ultrawork_request"`).


## Notes
No official release-note file for 2.1.146 was present in the archive paths, so this changelog is based on the filtered AST diff, AST-extracted string diff, and direct searches of `pretty-v2.1.145.js` and `pretty-v2.1.146.js`.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.146.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.146.txt`
