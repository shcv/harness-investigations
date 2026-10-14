# Changelog for version 2.1.299

## Summary

Version 2.1.299 adds controls for future sessions in agent view, a launch-time fast-mode override, and configurable shutdown draining for self-hosted runner orchestrators. Compared with 2.1.296, it also strengthens MCP skill verification, reports actual cron execution times, improves configuration diagnostics, and adds protections against unsafe file writes and sandbox execution. Artifact publishing edits and additional Project document capabilities ship behind rollout gates.

## New Features


### Model, Effort, and Fast-Mode Defaults in Agent View

What: Set defaults for sessions launched from the current agent-view window.

Usage:

```bash
claude agents
```

At the agent-view prompt, use:

```text
/model sonnet
/effort high
/fast on
```

Details:

- These choices apply to new sessions launched from that window.
- They are not saved as persistent settings.
- Use `default` to clear a window-specific override.
- The interface explains when a model does not support the selected effort level or an environment variable overrides it.
- Fast mode remains subject to account and model availability. The interface warns that cloud sessions do not receive this window’s fast-mode choice.

Evidence: Agent-view command handlers update launch defaults and display their scope; search for `"Set model for new sessions from this window (not saved)"`, `"Set effort for new sessions from this window (not saved)"`, and `"Unknown /fast option"`.


### Launch-Time Fast-Mode Override

What: Turn existing fast mode on or off for a session directly from the command line.

Usage:

```bash
claude --fast-mode on
claude --fast-mode off
```

Details:

- Accepts `on` or `off`.
- Applies through session settings during startup.
- The override is carried into supported background-session launch paths.
- The flag is hidden from ordinary help output.
- It does not bypass fast-mode eligibility or model restrictions.

Evidence: CLI parsing, startup settings, and background-launch arguments handle `"--fast-mode <on|off>"`. This flag is absent from 2.1.296; fast mode itself already existed.


### Disable Automatic Reading of File Mentions

What: Keep file mentions as references instead of automatically reading their contents from disk.

Usage:

```bash
CLAUDE_CODE_DISABLE_FILE_MENTIONS=1 claude
```

Details:

- Changes how `@` file references are expanded into conversation attachments.
- Files supplied through the session’s attachment mechanism can still be included when available and permitted.
- References without supplied contents remain references for Claude to resolve through available tools.
- The setting is propagated into background agents.

Evidence: File-mention expansion selects the reference-oriented path when `"CLAUDE_CODE_DISABLE_FILE_MENTIONS"` is enabled.


### Graceful Shutdown for Self-Hosted Orchestrators

What: Give in-flight polling and runner-spawn hooks time to finish when a self-hosted orchestrator receives SIGTERM.

Usage:

```bash
claude self-hosted-runner orchestrator \
  --hooks-dir /path/to/hooks \
  --shutdown-drain-sec 120
```

Details:

- Accepts a whole number from `0` to `3600` seconds.
- The default is `0`, preserving immediate shutdown.
- SIGTERM stops polling and starts the configured drain period.
- SIGINT or a second SIGTERM stops remaining work immediately.
- Shutdown handling returns eligible unstarted work to the service.
- Built-in guidance recommends a drain period of at least `--hook-timeout + 10` seconds and a process-manager kill delay of at least the drain period plus 15 seconds.

Evidence: Orchestrator option parsing and signal handling implement `"--shutdown-drain-sec"` and `"Received SIGTERM, stopping poll loop"`.

## Improvements


### Cron Results Show the Actual Next Run

Cron creation and listing now report the next execution time with the scheduler’s per-job offset included. This helps distinguish the time a job will actually run from the minute written in its cron expression.

Details:

- `CronCreate` and `CronList` expose an optional `nextFireAt` timestamp.
- Terminal results display a readable “next run” time.
- Tool instructions tell Claude to report that actual time when explaining a schedule.

Evidence: Scheduler results and renderers use `"nextFireAt"` and `"Epoch ms of the job's next run, the scheduler's per-job offset included"`.


### More Detailed Usage-Credit Advice

Usage reporting can now explain additional spending patterns: maximum effort, workflows, large amounts of always-on context, and oversized tool results.

Details:

- Advice recommends lowering effort for ordinary tasks, reserving workflows for larger tasks, inspecting `/context`, and narrowing noisy tool output.
- These categories extend existing usage reporting.
- They appear when the returned usage data contains the corresponding behaviors.

Evidence: Usage summaries and advice include `"% of your usage was at max effort"`, `"% of your usage came from workflows"`, and `"% of your usage went to tool results over 10k tokens"`.


### Clearer Settings-Loading Diagnostics

Configuration errors now distinguish an entire settings file that failed to load from individual unsupported entries that were skipped.

Details:

- A failed-file notice explicitly says that its hooks and permission rules are not in effect.
- A skipped-entry notice explains that the rest of the file remains active.
- Diagnostics identify the file, setting path, and problem.
- Inline JSON passed through `--settings` receives an identifiable label.
- These plain-text notices are suppressed for JSON and stream-JSON output.

Evidence: Settings diagnostics print `"These settings files did not load"` and `"These settings entries were skipped"`.


### Visible Context-Window Warnings for Unknown Models

When Claude Code cannot recognize a model identifier, it now explains the context window it assumes and links to guidance for gateways and custom model IDs.

Details:

- The warning makes the assumed token limit visible.
- It explains how that assumption affects automatic compaction.
- Where applicable, it points to the existing `CLAUDE_CODE_MAX_CONTEXT_TOKENS` override.
- This improves visibility into existing context-window handling.

Evidence: Model diagnostics contain `"Claude Code doesn't recognize the model"` and `"context assumed to be"`, with the documentation anchor `"#correct-the-window-for-a-gateway-or-custom-model-id"`.


### Stronger MCP Skill Verification and Recovery

MCP skill loading now checks that the invoked skill still belongs to the connection that listed it and that its downloaded definition matches the advertised metadata.

Details:

- Verification checks the resource URI, byte size, checksum, and frontmatter.
- A changed skill entry can be refreshed through `skills/get`; the user is then told to invoke it again.
- Removed skills and reconfigured or disconnected servers receive specific reconnect guidance.
- Invalid listing entries receive clearer explanations.
- Skills sharing a short name can receive distinct qualified names instead of colliding.

Evidence: MCP skill loaders check `"skills/get"`, `"frontmatter_mismatch"`, and `"digest_mismatch"`, and report `"MCP skill no longer served"` or `"MCP skill failed verification"`.


### Cloud Sessions Check Synced Plugins Between Turns

Cloud sessions using account-plugin synchronization now check plugin freshness at turn boundaries.

Details:

- The check can trigger plugin reloading after an account-side change.
- If checking fails, the session explains that previously loaded versions remain in use.
- If reloading fails, it warns that parts of earlier versions may remain active.
- This applies to eligible remote sessions with plugin synchronization enabled. Its server flag defaults to enabled.

Evidence: Turn-start checks use `"tengu_ccr_plugins_turn_start_check_enabled"` and display `"Couldn't check your plugins for updates"` or `"Couldn't finish reloading your plugins after a change"`.


### Exclude Built-In Tools from Plugin Evaluations

The existing plugin evaluation command gains a tool-removal option for testing behavior without selected built-in tools.

Usage:

```bash
claude plugin eval ./my-plugin --disallow-tools Agent TaskStop
```

Details:

- `--disallow-tools` removes named built-in tools from every case, even if otherwise granted.
- Cases can also specify `disallowed_tools`.
- Use bare tool names; permission patterns and MCP tool names are not accepted by this option.
- Validation detects some cases whose graders cannot succeed with the selected tools removed.
- Evaluation reporting also explains model API failures rather than treating them as ordinary successful grading.

Evidence: Evaluation parsing and validation use `"--disallow-tools <tools...>"`, `"disallowed_tools"`, and `"that this version of Claude Code can remove"`.


### Better Worktree Errors and Resume Instructions

Worktree failures now explain more precisely whether Git failed to start, timed out, returned no commit, encountered an unsuitable repository layout, or could not resolve the requested base.

Details:

- Guidance distinguishes a repository with no initial commit from a bare repository or an unresolved ref.
- Upload guidance asks users to commit the specific files intended for the cloud session.
- Exit-time resume hints can include the worktree name.
- When a suitable worktree command cannot be displayed, guidance explains how to locate the folder with `git worktree list`.

Evidence: Diagnostics include `"git rev-parse returned no commit for HEAD"`, `"worktree base not resolved"`, `"To find that folder, try git worktree list"`, and `"claude --worktree"`.


### Plan Mode Adapts to Sessions Without a Disk

Plan-mode instructions now support sessions that cannot persist a plan file.

Details:

- Claude is instructed to deliver the plan in its reply.
- The workflow explicitly states that no plan file exists.
- Attempts to save an unsupported plan receive a specific error.
- A separate notice explains that sessions launched with bypass permissions will not ask before most edits or commands, even in plan mode.

Evidence: Plan handling contains `"This session has no plan file"`, `"Cannot save the plan: this session does not write to disk"`, and `"Session was started with bypass permissions"`.


### Feedback Bundles Explain Missing Transcript Content

Feedback-bundle results now disclose when the session transcript was unavailable, only partly readable, or too large to include in full.

Evidence: Bundle notices include `"This session has no transcript on disk"`, `"The session transcript couldn't be read in full"`, and `"The session transcript is too large for one archive"`.

## Bug Fixes

- Strengthened file-encoding checks to reject UTF-16 big-endian files and NUL-containing data before Edit or Write can rewrite them as ordinary text. Read results explain the restriction; existing UTF-16LE handling remains supported. Search for `"has NUL bytes in its first 8 KB"` and `"is UTF-16 big-endian"`.

- Lost or expired MCP tasks now produce an explicit “outcome unknown” notification. Claude is instructed to check what happened before repeating a call that could duplicate work. Search for `"Task outcome unknown:"` and `"Calling the tool again may repeat the work"`.

- Duplicate deliveries of a side-question request join its existing in-flight run. A deadline also bounds how long Claude Code waits for an answer. Search for `"side_question: duplicate delivery joins the run in flight"` and `"side_question: no answer by the deadline"`.

- Agent completion notifications now explain when messages arrived too late for the reported result and the agent is being resumed with them. This helps prevent premature completion reports or duplicate follow-ups. Search for `"One or more messages sent to this agent arrived after this run's last step"`.

- Agent launch and resume paths reject unsupported working-directory requests, including unsuitable paths and worktree resumes in sessions without the required filesystem support. Search for `"cwd must be a local path with no"` and `"Cannot resume this agent, which was started in a worktree"`.

- Windows shell snapshots fall back to the snapshot-creating shell’s PATH when a login-shell probe fails, rather than using an unusable probe result. Search for `"The snapshot will take PATH from the shell that creates it"`.

- Windows users receive a warning when a hook or skill command falls back to PowerShell because Git Bash is missing. Explicit Bash requirements receive actionable installation or shell-selection guidance. Search for `"Git Bash wasn't found"`.

- Added Windows sandbox checks that refuse a command when Claude Code cannot confirm renewal of its own file protections. Related diagnostics explain unsafe working folders, executable access failures, and oversized command environments. Search for `"SandboxProtectionNotRenewedError"`, `"Windows refused to start this copy of Claude Code"`, and `"more than 30,000 characters"`.

- Added a read-only shell safety check for `awk` programs whose `print`, `printf`, or `getline` pipes can execute commands. The diagnostic also explains alternatives for harmless literal pipes that trigger the conservative check. Search for `"with a | after print/printf or before getline"`.

- Authentication paths now explicitly refuse to send an API key when its configured base URL is not recognized as an Anthropic host. Search for `"API key not sent: ANTHROPIC_BASE_URL is not an Anthropic host"`.

- MCP connection and authentication errors distinguish addresses reserved by Claude Code from administrator-imposed restrictions. Server-name validation also rejects additional JavaScript prototype-related names. Search for `"MCP server refused at a reserved address"` and `"__lookupSetter__"`.

## In Development

The following capabilities have new implementation in this release, but access depends on rollout gates, managed-plugin policy, or service-provided session configuration.


### Edit an Artifact While Publishing [In Development]

What: Apply small text replacements and publish the updated artifact in one call.

Status: Feature-flagged; disabled by default unless enabled through the rollout configuration or environment override.

Details:

- Publishing accepts `edits` containing `old_str` and `new_str` pairs.
- Each old string must occur exactly once; edits apply in order, all or none.
- JSON edits are checked for valid resulting JSON.
- Edit permission checks and file-identity protections apply.
- After publishing, the implementation attempts to update the local file and reports if that write-back failed.
- The option has restrictions for multi-file publishing, new artifacts created from a type, review pages, and other specialized publishing paths.

Evidence: Publishing checks `"CLAUDE_CODE_ARTIFACT_PUBLISH_EDITS"` or the `publishEdits` field of `"tengu_cobalt_plinth_orpine"`. Search for `"publish: small changes"` and `"No edits were applied and nothing was published"`.


### Original Project Document Downloads [In Development]

What: Open the original bytes of an uploaded Project document instead of relying only on extracted text.

Status: Feature-flagged through `tengu_mossy_wirth`, defaulting to off.

Details:

- `project_read` gains `original: true` for document uploads such as PDFs and DOCX files.
- The result returns a local file path.
- Text documents and other upload types retain their existing handling.
- A session needs a usable destination for downloaded files.
- When unavailable, Claude Code explicitly reports that `original` was ignored.

Evidence: Project tool schemas and handlers use `"project_read: true saves the original file"` and `"tengu_mossy_wirth"`.


### Version-Checked Project Document Writes [In Development]

What: Prevent an existing Project document from being overwritten after another chat changes it.

Status: Feature-flagged through `tengu_quill_marten`, defaulting to off.

Details:

- Project read and write results can return a document version.
- `project_write` accepts that version as `if_version`.
- A stale version causes the write to be refused.
- New documents can omit the version.
- Sessions without this capability warn when `if_version` was ignored and no version check occurred.

Evidence: Project tools use `"project_write to an existing doc"`, `"Nothing was changed. if_version must be"`, and `"tengu_quill_marten"`.


### Expanded Plugin Hook Capabilities [In Development]

What: Extend the existing function-hook system with attachment access, restricted session identity access, and support for helpers spread across a plugin’s own source files.

Status: Subject to the existing `tengu_plugin_hooks_modules` rollout and managed-plugin restrictions.

Details:

- `$.prompt.media` reads an attachment associated with the prompt submission currently being handled.
- It accepts an attachment ID and an optional byte offset.
- `$.session.identity` is restricted to plugins enabled and sourced through managed settings.
- Hook-source analysis can follow supported function declarations through imports and re-exports within the module’s own files.
- Personally installed hook modules can remain unloaded while their rollout switch is off; built-in and eligible organization-managed modules follow separate rules.
- The framework existed in 2.1.296; these are extensions and enablement changes.

Evidence: Original modules contain `"prompt.media"`, `"session.identity"`, `"outside the hook's own file"`, and `"hooks modules a person installed wait for the rollout switch"`.


### Self-Hosted Sessions That Host MCP Tools [In Development]

What: Let a self-hosted runner serve MCP tools for a session without running its model loop locally.

Status: Service-selected infrastructure; general availability cannot be established from the CLI source.

Details:

- A tool-hosting descriptor selects a new `tool-server` runner path.
- The runner starts `mcp serve` using rendered results and a session tunnel.
- It maintains separate tool-server configuration state.
- The path includes checks for runner identity, token expiry, and incompatible proxy routing.
- It is not exposed as a standalone new end-user command.

Evidence: Runner and tunnel implementations contain `"hosts tools only, no worker"`, `".tool-server-config"`, and `"--session-tunnel cannot see the runner that started it"`.

## Notes

This changelog compares **2.1.296 → 2.1.299**. Substantive changes were checked against both version snapshots and, where needed, the original 2.1.299 Bun modules; wrapper changes, renamed identifiers, and module ordering were excluded.

If an MCP server or skill stops loading after upgrading, inspect `/mcp` and `claude --debug` for the specific address, name, or verification error. Feature-gated code in the package does not establish that a particular account has received the rollout.


Generated with:
- tool: `harness-investigations@9f9aa55-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.299.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.299.txt`
- source modules: `archive/claude-code/original/cli-v2.1.299.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
