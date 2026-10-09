# Changelog for version 2.1.296

## Summary

Version 2.1.296 adds context-aware large-file reads, per-agent compaction limits, and a workflow-specific subagent model override. It strengthens file-editing and permission safeguards, improves cloud-session diagnostics, and adds gated support for MCP file uploads and relative subagent effort. Legacy MCP tasks using the 2025-11-25 protocol can no longer be resumed by this version.

## New Features


### Read Large Text Files When Context Allows

What: The Read tool now accepts `allow_large: true` to exceed its usual text-file limits when enough conversation context remains.

Usage:

Ask Claude to read the complete file when that is necessary. The corresponding Read tool input is:

```json
{
  "file_path": "/absolute/path/to/file.txt",
  "allow_large": true
}
```

Details:

- Works for whole text files and selected line ranges.
- Available context determines the raised limit; other large reads in the same turn share that allowance.
- This does not remove context limits or raise the limits for images, PDFs, or notebooks.
- Reads executed through another machine or a remote tool call cannot use the larger allowance.
- Oversized-read errors explain whether to retry with `allow_large` or read the file in portions.

Evidence: Read schema, context-budget calculation, and execution path (search for `"allow_large"`, `"Set to true to read a text file"`, and `"other large reads in the same turn share that room"`). These additions are absent from 2.1.295 and present in the original 2.1.296 modules.


### Per-Agent Compaction Limits

What: Custom agent definitions can set `autoCompactWindow` to make a subagent compact its conversation earlier.

Usage:

Add the field to an agent definition such as `.claude/agents/researcher.md`:

```yaml
name: researcher
description: Investigates a bounded question
autoCompactWindow: 100000
```

Details:

- Accepts an integer from 100,000 to 1,000,000 tokens.
- Supports local agent files and plugin agent definitions.
- Only lowers the compaction window the subagent would otherwise inherit.
- Does not change the main conversation’s compaction window.
- Invalid values produce a warning identifying the agent file and accepted range.

Evidence: Agent frontmatter parsing and subagent compaction ceiling (search for `"Token count at which this agent compacts its own conversation"`, `"It only lowers the window"`, and `"has invalid autoCompactWindow"`). General compaction settings already existed; the agent-definition field is new.


### Workflow-Specific Subagent Model Override

What: `CLAUDE_CODE_WORKFLOW_SUBAGENT_MODEL` selects a default model specifically for agents running within workflows.

Usage:

```bash
CLAUDE_CODE_WORKFLOW_SUBAGENT_MODEL=sonnet claude
```

Details:

- Separates workflow delegation from the general `CLAUDE_CODE_SUBAGENT_MODEL` default.
- `inherit` leaves this override inactive.
- Participates in workflow agent model selection and overrides agent/tool model selections on the workflow-specific resolution path.
- Available-model restrictions still apply.
- When `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` is active, the override must come from the accepted environment source; a conflicting value is ignored.

Evidence: Workflow model resolver and override precedence (search for `"CLAUDE_CODE_WORKFLOW_SUBAGENT_MODEL"` and `"workflow_env"`). The environment variable is absent from 2.1.295.


### Relative Subagent Effort [Gradual Rollout]

What: Eligible sessions can request reasoning effort one step below or above the effort a subagent would normally use.

Usage:

Ask Claude to delegate a bounded lookup with lower effort. The Agent tool can then receive:

```json
{
  "description": "Find configuration references",
  "prompt": "Find references to this configuration key and report their locations.",
  "effort": "lower"
}
```

Details:

- Adds `lower` and `higher` alongside existing named effort levels.
- Adjusts effort on the selected model; it does not itself select a cheaper or more capable model.
- Requires the `tengu_snappy_pelican` gate or its environment override.
- Is unavailable when a forced subagent model or another enforced effort configuration prevents it.
- Relative effort is ignored for forks, remote-isolated agents, and teammates.
- When the feature is unavailable, the input normalization path removes relative-effort values.

Evidence: Gated Agent schema and relative-effort handling (search for `"tengu_snappy_pelican"`, `"CLAUDE_CODE_SNAPPY_PELICAN"`, and `"one step from the effort the agent would otherwise run at"`). These relative options are absent from 2.1.295.


### Local File Inputs for Supported MCP Tools [Gradual Rollout]

What: Supported MCP tools can accept local files that Claude Code validates and uploads before invoking the tool.

Usage:

Ask Claude to attach a local file to a supported connector action. The connector’s tool metadata specifies the local-path field; there is no universal attachment argument.

Details:

- Requires `tengu_walnut_tiller` and a recognized, eligible server.
- Uses the tool’s `anthropic/fileInputs` metadata to identify file arguments.
- Checks file-read permissions, upload policy, file sizes, and protected paths.
- Rejects credential files and protected Claude files.
- Refuses the call if its arguments changed while awaiting approval or an attachment changed before upload.
- Upload failure prevents the MCP tool from being called.

Evidence: File-input metadata, approval preparation, and upload-before-call path (search for `"anthropic/fileInputs"`, `"tengu_walnut_tiller"`, `"MCP tool file input rejected"`, and `"The arguments of this call changed while it waited for approval"`). This metadata and execution infrastructure are absent from 2.1.295.

## Improvements


### Clearer Cloud Tool-List Validation

Cloud `--tools` support already existed. This release adds more precise validation and explains why a requested list cannot be applied.

Details:

- Accepts up to 128 explicit tool names.
- Distinguishes tool names from permission rules, exclusion syntax, presets, and self-hosted operator tools.
- Explains that `default` must be supplied by itself.
- Gives specific guidance for Remote Control, self-hosted, and unknown environment types that cannot apply the list.
- Explains that attaching to an existing session cannot change the tool lists it was created with.
- Reports prompt-delivery failure separately from successful session creation.

Usage:

Where the cloud environment supports explicit tool lists:

```bash
claude --tools "Read,Grep,Glob"
```

Evidence: Cloud tool-list parser and launch diagnostics (search for `"a cloud session takes at most"`, `"a rule is not a tool name"`, `"--tools is not supported in a Remote Control environment"`, and `"The cloud session was created, but"`).


### Unknown Agent Frontmatter Warnings

Agent files now warn about unrecognized frontmatter keys instead of leaving users to discover that a setting had no effect.

Details:

- Applies to local and plugin agent definitions.
- Suggests a recognized key when a likely spelling or naming mistake is detected.
- Avoids repeatedly emitting the same unchanged warning.
- Retains separate explanations for fields recognized but unsupported in plugin agents.

Evidence: Frontmatter key checking and suggestions (search for `"agent-frontmatter-unknown-keys"`, `"Claude Code does not recognize or apply"`, and `"did you mean"`).


### Better Explanations for Inactive Hooks and Plugin Conflicts

Hook diagnostics now identify more reasons that configured hooks are not running, including managed policy, safe mode, bare mode, `--settings`, and alternate Cowork settings files.

Plugin conflict messages also distinguish an inactive `hooks.json` file from an inactive hooks module and name the plugin copy taking precedence.

Evidence: Hook-source diagnostics and plugin conflict descriptions (search for `"The hooks in"`, `"this session runs in safe mode"`, `"the settings file Claude Code was started with (--settings)"`, and `"holds the same plugin name and comes first"`).


### Configurable Overload Retry Delay Ceiling

`CLAUDE_CODE_OVERLOADED_RETRY_MAX_DELAY_MS` now lets users configure the backoff ceiling for overload retries.

Usage:

```bash
CLAUDE_CODE_OVERLOADED_RETRY_MAX_DELAY_MS=30000 claude
```

Details:

- Applies to the overload retry path.
- Works alongside the existing `CLAUDE_CODE_OVERLOADED_RETRY_BASE_DELAY_MS`.
- Other retry paths, watchdog limits, server retry guidance, and jitter can affect actual waiting time.

Evidence: Overload-specific backoff calculation (search for `"CLAUDE_CODE_OVERLOADED_RETRY_MAX_DELAY_MS"`). The maximum-delay variable is new; the base-delay variable already existed.


### Earlier Idle Compaction in Hosted Cloud Workers

The existing sleep-compaction mechanism now has a hosted-worker scheduling deadline measured from the end of a turn.

Details:

- Defaults to 150 seconds after the turn ends.
- `CLAUDE_CODE_SLEEP_COMPACT_AFTER_MS` adjusts that deadline within a 60–210 second range.
- Compaction can occur earlier when the cache-based deadline requires it.
- Still requires sleep compaction to be enabled and the session to satisfy idle, context-size, permission, and usage checks.
- The new after-turn deadline applies to Anthropic-hosted workers, rather than ordinary local sessions.

Evidence: Hosted-worker sleep-compaction scheduling (search for `"CLAUDE_CODE_SLEEP_COMPACT_AFTER_MS"` and `"CLAUDE_CODE_SLEEP_COMPACT"`).


### Optional Bounded Wait for Resume Hooks

Compatible resumed cloud sessions can use `CLAUDE_CODE_RESUME_SESSIONSTART_HOOKS_WAIT_MS` to avoid waiting indefinitely for ordinary SessionStart hooks before loading the conversation.

Details:

- The behavior is opt-in.
- After the configured wait, completed hook output is retained and remaining output can join a later turn.
- Claude Code continues waiting when an administrator’s hook may still be running.
- The implementation requires the cloud transport’s late-hook delivery support; setting the variable alone does not change every local resume flow.

Evidence: Resume-time hook waiting and deferred output delivery (search for `"CLAUDE_CODE_RESUME_SESSIONSTART_HOOKS_WAIT_MS"`, `"reading messages now, their output joins a later turn"`, and `"because an administrator's hook may be among them"`).


### Bounded MCP Discovery Listings

Claude Code now bounds the amount of MCP discovery data it accepts and normalizes, protecting sessions from excessively large listings.

Details:

- Uses a budget of approximately 16 MB, with additional overhead for many small values.
- Separately limits text expensive to normalize, such as combining characters and non-ASCII tool names.
- Reports how many trailing entries were skipped.
- Explains that the server must return fewer or shorter entries to make the omitted items available.

Evidence: Discovery-budget accounting and truncation warning (search for `"the listing is too large"` and `"The server must list fewer or shorter"`).


### More Actionable Cloud and Self-Hosted Diagnostics

Cloud-session errors more clearly distinguish login requirements, device enrollment, pending settings acceptance, and self-hosted runner work-order failures.

Details:

- Trusted-device errors clarify that enrollment requires `/login` in Claude Code; `claude auth login` does not enroll the device.
- Pending local settings acceptance points users to `claude apply-project-settings`.
- Runner registration errors identify expired, superseded, already-used, and otherwise unusable work orders.
- Work-order errors explain when restarting cannot help and when the environment secret is not at fault.

Evidence: Authentication, settings, and runner diagnostics (search for `"claude auth login does not enroll"`, `"served_settings.own_waiting"`, `"RegisterRunner refused because"`, and `"The environment secret is not at fault"`).

## Bug Fixes

- Prevented Edit and notebook editing from silently rewriting invalid UTF-8 bytes as replacement characters. Write also rejects the destructive case where replacement characters are supplied after a lossy read. Use an encoding-preserving shell operation or explicitly convert the file first. Evidence: encoding checks and rejection messages (search for `"File is not valid UTF-8"` and `"If the content came from Read, writing it destroys those characters"`).

- Prevented tool execution when an approval’s permission updates cannot be fully applied and a deny or ask rule may be missing. The call is refused with an explanation rather than proceeding under incomplete restrictions. Evidence: permission-update failure handling (search for `"Nothing that the answer allowed is in force either"`).

- Prevented an inherited approval from proceeding when a PermissionRequest hook fails before the approval can be applied. Evidence: inherited approval hook failure path (search for `"A PermissionRequest hook failed before the approval given earlier could be applied"`).

- Protected bridge-submitted pasted text beginning with `/` from being interpreted as a slash command when the original input was a paste placeholder. Missing paste content also cancels submission rather than sending incomplete text. Evidence: paste expansion and submission preparation (search for `"Pasted text:"` and `"Not sent: the pasted text is blank"`).

- Added a PowerShell parser integrity check that refuses to rely on a parse of a command different from the command submitted. Evidence: parser round-trip comparison (search for `"PowerShell parser did not receive the command intact"` and `"InputMismatch"`).

- Rejected marketplace names that collide with inherited JavaScript object members or cannot form valid plugin identifiers. Evidence: marketplace registration guards (search for `"marketplace add refused: the name is an inherited object member"` and `"Claude Code reserves this name"`).

- Rejected workflow scripts containing control characters that an approval prompt cannot faithfully display. Evidence: workflow input validation (search for `"contains a control character that an approval prompt cannot show"`).

- Added fresh-review handling for artifact operations whose earlier approval lacked current ownership or sharing information. Evidence: artifact approval context checks (search for `"reviewed this call before it had been told whose artifact this is or who it is shared with"`).

## In Development

Features below contain shipped infrastructure whose new behavior is disabled or gated.


### Recovery From Thinking-Only Output Exhaustion [In Development]

What: Claude Code has new recovery logic for responses that exhaust their output budget while producing thinking without a visible answer.

Status: Stubbed.

Details:

- Can distinguish thinking-only exhaustion from ordinary output-limit recovery.
- Contains an alternative continuation prompt and guidance to lower reasoning effort.
- A hardcoded false-returning guard disables the alternative recovery and the new user-facing guidance.
- Existing output-limit recovery remains in use.
- No related orphaned tip was identified.

Evidence: The guard returns `!1` in the original module, leaving both new branches inactive (search for `"The last attempt reached the limit while still thinking"` and `"Lower the effort level to leave room for a reply"`).


### Additional Stalled Remote-Tool Detection [In Development]

What: New monitoring infrastructure can investigate accepted remote tool calls whose connection goes silent.

Status: Feature-flagged.

Details:

- Requires both `tengu_lazy_dove` and `tengu_violin_pernambuco`, which default to false.
- Also requires the remote host to advertise `says_still_here`.
- Tracks missed liveness probes and subsequent connection evidence before treating a waiting call as stalled.
- Availability depends on rollout flags and the remote host’s capabilities.
- No related orphaned tip was identified.

Evidence: Capability-checked remote-call silence monitoring (search for `"tengu_lazy_dove"`, `"tengu_violin_pernambuco"`, and `"says_still_here"`).

## Notes

### Legacy MCP Task Resume Is Removed

Version 2.1.296 no longer restores MCP tasks using the **2025-11-25 tasks protocol**. When it encounters a legacy resume record, it deletes that local record and explicitly reports that the task was **not cancelled on the server**.

Before restarting important work, check its status through the server’s own interface to avoid unintentionally duplicating a still-running task. SEP-2663 task records are handled separately.

Evidence: Legacy task resume removal (search for `"it used the 2025-11-25 tasks protocol, which this version no longer supports"` and `"the task was not cancelled on the server"`).

This changelog compares the 2.1.295 and 2.1.296 CLI snapshots, with substantive additions checked against the original 2.1.296 Bun modules. Rollout labels describe source-code gates; they do not establish which accounts currently receive access. Separate VSCode extension, SDK-package, and Windows native-installer changes are outside this analysis.


Generated with:
- tool: `harness-investigations@6c0ae2a-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.296.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.296.txt`
- source modules: `archive/claude-code/original/cli-v2.1.296.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
