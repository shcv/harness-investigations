# Changelog for version 2.1.288

## Official Release Highlights

Version 2.1.288 adds recoverable prompt drafts, configurable code-review finding limits, fullscreen selection access for mods, and better MCP authentication prompts. It also improves conversation recovery, plugin reliability, shell permission checks, accessibility, and cloud-session continuity.

These highlights summarize the published release notes for the CLI changes, with evidence from the v2.1.287 → v2.1.288 comparison and the original Bun module sources.


### Recover a Prompt Cleared with Ctrl+C

What: You can recover an unsent prompt after clearing it with Ctrl+C.

Usage: Press Up while the prompt is empty.

Details:

- Recovery includes pasted text and images.
- This helps recover a long draft without reconstructing its attachments.

Evidence: Prompt clearing and history restoration preserve draft attachment data; search for `"history:previous"` and `"pastedContents"`.


### Choose How Many Code-Review Findings to Report

What: `/code-review` accepts a finding limit instead of always using the usual limit.

Usage:

```text
/code-review --max-findings 12
/code-review --max-findings all
/code-review --max-findings default
```

Details:

- Use a positive whole number to cap the findings.
- `all` requests every finding that survives verification.
- The choice is saved and reused until you supply another value or `default`.
- Invalid values are ignored with an explanatory notice.
- Low-effort reviews already have no maximum, so this option does not change them.
- The review instructions explicitly prohibit inventing findings to reach a target.

Evidence: Argument parsing, saved preferences, and review prompts use `"--max-findings"`, `"codeReviewLastMaxFindings"`, and `"Keep every finding that survives. There is no maximum."`.


### Read Fullscreen Selections from Mods

What: Mods can retrieve the last text selection through `$.ui.selection()`.

Usage:

```javascript
const selection = await $.ui.selection();
```

Details:

- The method reads the selection retained by the fullscreen interface.
- When the selection belongs to one transcript row, the result also identifies that row.
- This extends the existing mod API; Claude Mods themselves were introduced in the previous version.

Evidence: The mod API forwards `"ui.selection"` to the interface’s selection reader.


### Find and Navigate Sessions More Easily

What: The agents view gains keyboard actions for finding sessions and jumping between groups.

Usage: Press Ctrl+F to search by name, or Alt+↑/↓ to move between groups.

Details:

- Search, group navigation, and rename actions can be rebound in `keybindings.json`.
- Enter now opens the best name match when using Ctrl+F or the existing `n:` filter.
- The `n:` filter itself is not new in this release.

Evidence: Search for `"agents:find"`, `"agents:nextGroup"`, `"agents:previousGroup"`, and `"agents:rename"`.


### Built-In GitHub REST Access in More Cloud Sessions

What: Cloud sessions without an installed GitHub CLI can use Claude Code’s built-in `gh api`.

Usage:

```bash
gh api repos/{owner}/{repo}/pulls
gh api --paginate repos/{owner}/{repo}/issues
```

Details:

- The built-in client supports GitHub REST requests through the session’s GitHub proxy.
- It is not a complete replacement for the GitHub CLI.
- Unsupported common commands now suggest their `gh api` equivalent.
- Repository-list pagination follows subsequent pages.
- Nested Claude processes preserve the enclosing session’s client.
- Terminal output is sanitized so file names, jq expressions, and GitHub errors cannot inject control characters.
- `--jq` requires a separately installed `jq`.
- GraphQL and downloads served through unsupported external hosts remain unavailable.

The self-hosted-runner version of this client already existed in v2.1.287; this release extends availability and behavior.

Evidence: Search for `"Claude Code's built-in GitHub client, not the GitHub CLI"`, `"--paginate"`, `"--jq needs jq"`, and `"GitHub GraphQL is not available through this session's GitHub proxy"`.


### MCP Prompts Handle Authentication and Browser Completion Better

What: MCP tool calls can request re-authentication when a server requires additional OAuth scope.

Usage: Approve the re-authentication prompt, complete the browser flow, then return to Claude Code.

Details:

- Scope expansion is presented as a user decision.
- For MCP browser prompts whose servers cannot report completion, select “I'm done, continue” after finishing in the browser.
- This prevents the tool call from continuing before you have completed the external step.

Evidence: Search for `"needs additional permissions for this tool"`, `"Re-authenticate now?"`, and `"I'm done, continue"`.


### Conversation Recovery and Resume Are More Reliable

Several fixes reduce lost context and incomplete transcripts:

- Non-interactive sessions and subagents can continue from a partial response after a mid-response timeout.
- Thinking-only responses are retried rather than immediately failing the turn.
- Automatic compaction handles conversations whose latest reply reported zero token usage.
- Resume retains files and context restored by compaction.
- The final response of a turn is saved more reliably.
- Transcript loading coordinates with rewrites to avoid reading a temporarily truncated file.
- Conversations started on v2.1.286 or earlier retain their earlier thinking when resumed.

Usage:

```bash
claude --resume
```

Evidence: Streaming recovery contains `"after thinking-only yield"` and `"retrying streaming"`; transcript coordination contains `"Transcript rewrite stopped waiting"`; compaction and replay paths retain `"input_tokens"`, `"thinking"`, and restored attachments.


### Auto-Compaction Settings Follow Each Model

What: `/autocompact` saves a separate window for each model.

Usage:

```text
/autocompact 200000
/autocompact auto
```

Details:

- Switching models no longer replaces another model’s preferred window.
- The per-model setting supports a token count or `"auto"`.
- Within one settings file, a model-specific value takes precedence over the top-level window.
- Canonical model keys also match supported dated, `[1m]`, Bedrock, and Vertex spellings.
- Before the first request in a fresh environment or after a model switch, Claude Code can wait up to 1.5 seconds for server-provided model limits.

Evidence: Search for `"Auto-compact window for this model"` and `"modelSettings"`. The model-information wait is controlled by `"tengu_deep_shore"` with a default-on check.


### Better Compatibility with Mantle and API Gateways

What: Auxiliary features can recover when a provider rejects structured outputs.

Usage:

```bash
CLAUDE_CODE_DISABLE_STRUCTURED_OUTPUTS=1 claude
```

Details:

- Session titles, memory recall, and prompt hooks can retry without the unsupported output format.
- The new environment variable lets you disable structured outputs explicitly.
- Stopping a Bedrock credential lookup ends the request instead of unexpectedly selecting a fallback model.
- Concurrent credential-refresh coordination avoids opening another browser sign-in after a laptop wakes.

Evidence: Search for `"CLAUDE_CODE_DISABLE_STRUCTURED_OUTPUTS"`, `"rejected output_config.format"`, `"gcpAuthRefresh"`, and `"awsAuthRefresh"`.


### Auto Mode Handles Long Conversations and Provider Changes Better

What: Auto mode can compact an oversized conversation instead of repeatedly failing to review tool calls.

Details:

- A classifier context overflow is distinguished from a judgment that the proposed action is unsafe.
- Claude Code attempts compaction before the next request.
- Denial guidance names the blocked tool rather than always recommending a Bash rule.
- On Bedrock and Mantle, an auxiliary request to an older model no longer forces the session permanently onto the local classifier.
- A Sonnet 5.5 or Opus 5.5 pin in `ANTHROPIC_DEFAULT_SONNET_MODEL` is ignored for the client-side classifier, which uses Sonnet 5.

Evidence: Search for `"The conversation was compacted because it had become too long for auto mode's classifier"`, `"To allow this type of action in the future"`, and `"cannot serve as the classifier; using the Sonnet 5 default instead"`.


### Safer Shell Permission Checks

Shell permission checking now handles several previously troublesome cases:

- Dangerous removals inside `bash -c` or `sh -c` require approval, including under bypassPermissions or a shell allow rule.
- Assignments to `BASHPID` that can trigger arithmetic evaluation require a permission check.
- Under sandbox auto-allow, simple unquoted heredocs can run without repeated approval when their bodies contain only plain text and simple variable references.
- Permission explanations are shorter when part of a command cannot be checked before execution.
- Credential-file protection for git configuration works with `permissions.blockReadsOutsideWorkingDirectories`.

Evidence: Search for `"Dangerous rm operation in a shell -c script"`, `"BASHPID"`, `"plainUnquotedHeredocs"`, `"tengu_amber_larch"`, and `"sandbox.credentials"`.


### Hooks and Scoped Instructions Apply More Consistently

What: Instruction loading and permission hooks no longer silently miss important checks.

Details:

- Write and Edit now load applicable path-scoped `.claude/rules` and nested `CLAUDE.md` files.
- `InstructionsLoaded` reports subagent identity and effort for instruction files loaded during file access.
- `PreToolUse` and `PermissionRequest` failures to match hooks or serialize tool input block the call.
- `idle_prompt` notification hooks wait while background agents are still running.

Evidence: Search for `"InstructionsLoaded"`, `"Blocked: Claude Code could not work out which hooks apply"`, `"this call's input can't be written as JSON"`, and `"idle_prompt"`.


### Plugin Installation, Configuration, and Execution Fixes

Plugin workflows receive several corrections:

- GitHub-source installs can fall back from SSH to HTTPS when SSH authentication fails.
- Marketplace fetch failures show both transport errors.
- `git-subdir` installs work with older git versions and avoid caching incomplete sparse checkouts.
- Plugins supplied through `--plugin-dir` expose “Configure options” in `/plugin`.
- Reloading or disabling a plugin no longer ends a background session because a timer or read was still running.
- A `tool.call` hook preserves the correct execution folder for worktree subagents.
- Agent-team members spawned by a plugin-defined agent name receive that agent’s prompt, tool restrictions, and effort.
- Large `Agent(...)` allowlists no longer stall agent launch.
- `claude plugin test` refreshes stale rollout state before reporting that mods are remotely disabled.

Usage:

```bash
claude plugin install <plugin>
claude plugin test <plugin>
```

Evidence: Search for `"clone failed, retrying with"`, `"Fetching the marketplace from GitHub failed on both attempts"`, `"plugin git-subdir read-tree"`, `"Configure options"`, `"tool.call"`, and `"Start \`claude\` once with network access"`.


### LSP Calls Time Out and Receive Expanded Configuration

What: Language-server requests stop waiting indefinitely, and plugin configuration placeholders are substituted consistently.

Details:

- Requests time out after 60 seconds by default.
- A server’s `requestTimeout` setting overrides that duration in milliseconds.
- Dynamic capability registration requests receive a response instead of leaving the connection hanging.
- `${user_config.*}` and `${CLAUDE_PLUGIN_ROOT}` substitutions apply inside `initializationOptions` and `settings`, including manifest defaults.

Example server configuration field:

```json
{
  "requestTimeout": 120000
}
```

Evidence: Search for `"Maximum time to wait for the server to answer a request"`, `"client/registerCapability"`, and `"Left unexpanded in plugin LSP initializationOptions/settings"`.


### MCP Failures No Longer Encourage Duplicate Execution

What: Unreadable or oversized MCP results are reported without automatically repeating a potentially completed tool call.

Details:

- Oversized responses and unparseable server messages produce an explicit result-not-read error.
- The error warns that the tool may already have run.
- Users should check the operation’s effects before retrying and request a smaller result where possible.
- Subagents in Claude Desktop’s Code tab can access tools from a user-configured MCP server named `memory`.
- Eligible cloud sessions no longer wait on the first turn for an unused stdio MCP server configured with `alwaysLoad: false`.

Evidence: Search for `"McpToolResultNotReadError"`, `"The tool may have run"`, `"MCP connection closed after an unreadable server message"`, and `"alwaysLoad"`.


### Cloud Sessions and Remote Control Recover More Cleanly

Cloud and Remote Control fixes include:

- Restarted cloud sessions respect server model refusals and the organization’s enforced model list.
- An unanswered WebFetch URL permission request is withdrawn after its timeout rather than leaving Cowork marked as waiting for input.
- Prompt suggestions reach a phone joining a session started elsewhere.
- Edit and Retry can use saved messages from before `/compact`.
- Remote Control keeps sessions connected during credential renewal and preserves them when renewal fails during a server outage.
- Cleanup avoids archiving a session that remains connected or has just been reattached.
- Cross-session messaging distinguishes delivery from a message held by the receiving session; Claude is no longer told that a held message was delivered.

Evidence: Search for `"This permission request was withdrawn because it was not answered in time"`, `"Remote Control credential renewed"`, `"Could not renew the Remote Control credential yet"`, and `"NOT delivered"`.


### Long-Running Commands and Headless Sessions Behave Better

What: Background command time limits apply to unattended sessions rather than interactive sessions.

Details:

- Terminal, desktop, and VS Code sessions have no background command time limit.
- Unattended sessions, including `-p`, CI, and cloud sessions, retain the limit.
- With `CLAUDE_CODE_RETRY_WATCHDOG`, recovery from a failed long stream uses streaming again and stops after three timeouts.
- Headless sessions handle SIGTERM correctly when a supervisor also sends SIGCONT.

Evidence: Search for `"Set to true to run this command in the background"`, `"CLAUDE_CODE_RETRY_WATCHDOG"`, `"retrying streaming"`, and `"SIGCONT"`.


### Login and Updating Report Real Failures

What: Authentication and updater messages more accurately reflect whether the operation succeeded.

Details:

- `/login` reports a secure-storage failure instead of claiming an unqualified success.
- It distinguishes a temporary login from credentials that will persist and offers a retry when the new login did not take effect.
- In `--bare` mode, `/login` explains that the session reads `ANTHROPIC_API_KEY` or an `apiKeyHelper` supplied through `--settings`.
- The npm auto-updater detects when only the placeholder `claude` stub was installed because the platform-native binary did not download.

Evidence: Search for `"Sign-in completed in the browser, but your credentials could not be saved"`, `"Bare mode doesn't use the sign-in from /login"`, and `"platform-native package missing"`.


### Accessibility and Fullscreen Interface Fixes

Interface changes make interaction more reliable:

- Approving a plan announces the resulting permission mode in screen-reader mode, including approval through Shift+Tab.
- Short screen-reader announcements remain visible until the next keypress or a change above them.
- Answered question-dialog entries display “answered.”
- In screen-reader mode, typing a rule number in `/permissions` selects it.
- Search cursors follow typed text in the fullscreen transcript viewer and custom theme-color search.
- Opening background tasks no longer crashes fullscreen sessions when mods or plugins add rows above the prompt.
- Stale mod buttons cannot invoke another button’s action after a restart.
- Invalid diff content in a plugin `Code` element falls back to plain code.
- Sending queued messages no longer leaves an inappropriate “What should Claude do instead?” hint.
- Windows keyboard input survives supported CLI self-restarts.

Evidence: Search for `"CLAUDE_AX_REWRITE_HELD_ANNOUNCEMENT"`, `"answered"`, `"ui.press"`, `"drawn as plain code"`, and `"What should Claude do instead?"`.


### Other Published CLI Improvements

- `/usage-credits` clearly reports when an organization disables credit requests. Search for `"Usage credit requests are turned off for your organization."`
- “You should know” notes distinguish decisions made by the user, the main agent, or both. Search for `"the main agent"` and `"Make sure to use"`.
- Artifact database size errors explain the storage limit and that deleting or shrinking documents frees space. Search for `"the total size of its documents, not their count"`.
- Artifact-tool guidance includes organization design systems where applicable. Search for `"design systems"` in the artifact guidance.
- Claude 3 Opus and Claude 3 Sonnet conversations containing whole PDFs recover by removing unsupported document input and directing Claude to page images. Search for `"Document removed: this model does not accept whole PDF documents"`.
- Claude in Chrome can perform permitted screenshots and page reads without asking on every call when auto mode is unavailable; typing, navigation, and JavaScript retain approval requirements. Search for `"is allowed, but Claude asks"` and `"disableAutoMode"`.
- The Agent tool served by `claude mcp serve` receives the available agent definitions instead of rejecting every agent type. Search for `"Available agent types:"`.


### Project Purge Command Renamed

What: The project-state purge command is now available directly under `claude`.

Usage:

```bash
claude purge
```

Details:

- `claude project purge` remains accepted for compatibility.
- The old spelling prints a notice directing users to the new spelling.

Evidence: Search for `"\`claude project purge\` is now \`claude purge\`"`.

## Additional Changes Beyond Official Notes

The following changes extend CLI behavior beyond the published highlights. They are verified against both version snapshots and the original v2.1.288 modules.

## New Features


### Host-Declared Worktree Boundaries

What: A host launching Claude Code can declare a worktree and shared paths where file-tool writes must stay inside that worktree.

Usage:

```bash
cd /srv/project-worktree

CLAUDE_CODE_HOST_WORKTREE=/srv/project-worktree \
CLAUDE_CODE_HOST_WORKTREE_FENCE='["/srv/project"]' \
claude
```

Details:

- `CLAUDE_CODE_HOST_WORKTREE` identifies the worktree.
- `CLAUDE_CODE_HOST_WORKTREE_FENCE` contains a JSON array of absolute paths to protect.
- The session must start inside the declared worktree.
- File-tool validation rejects writes into protected shared paths outside the applicable worktree.
- Rejected writes tell Claude to edit the worktree copy.
- Invalid declarations are logged and may be ignored; this is a file-tool guard, not a general shell sandbox.

Evidence: Both environment variables are absent from v2.1.287. Search for `"CLAUDE_CODE_HOST_WORKTREE"`, `"CLAUDE_CODE_HOST_WORKTREE_FENCE"`, and `"Edit the worktree copy of this file instead of the shared-checkout path"`.

## Bug Fixes

- File tools reject paths whose meaning changes when normalization and whitespace handling are repeated. The error asks for the ambiguous whitespace or trailing path portion to be removed. Search for `"UnstablePathError"` and `"ends in white space once its"`.
- Deny and ask rules supplied through a permission answer cannot use a leading `!` path exception to remove earlier restrictions. This correction applies to rules returned in permission answers; it does not establish a general removal of exception syntax from settings. Search for `"an answer may only add restrictions"`.

## In Development

These implementations are shipped behind server-controlled gates. Their presence does not establish that they are available in a particular account or session.


### Expanded In-Session Restart Workflow [In Development]

What: Restart Claude Code on the installed version while retaining the current conversation.

Status: Feature-flagged; default off through `tengu_fancy_wand`.

Usage, when available:

```text
/restart
```

Details:

- `/update` is retained as an alias.
- The implementation saves the conversation and relaunches it with continuity checks.
- It refuses a restart when the conversation cannot be saved, background work is active, or restrictions cannot be carried over.
- The normal command gate requires an eligible native installation and interactive terminal on macOS or Linux.
- Remote Control requests are refused.
- A disabled `/update` command with a `/restart` alias already existed in v2.1.287. This release expands its implementation and introduces conditional availability.

Evidence: Search for `"tengu_fancy_wand"`, `"Restart Claude Code and keep this session"`, and `"Can't restart automatically. Type /restart at the prompt."`.


### Specialized Artifact Editing and Republishing [In Development]

What: Eligible artifact-edit requests can use a specialized patch path that applies edits and republishes the artifact.

Status: Feature-flagged; default off through `tengu_cobalt_plinth_orpine`.

Details:

- A separate model request proposes structured edits.
- Proposed patches are checked before being applied through normal tool calls.
- Republishing follows successful edits.
- Ineligible requests and unsuccessful patch attempts return control to the ordinary conversation flow.
- The default eligible-model list contains `claude-opus-5-5`; server configuration can replace it.
- This extends existing artifact functionality rather than introducing artifacts themselves.

Evidence: Search for `"tengu_cobalt_plinth_orpine"`, `"artifact_patch_edit"`, `"Your previous patch was not applied"`, and `"Made ${e===1"` in the original modules.


### Instruction-Size Warnings for Desktop Code Sessions [In Development]

What: Claude Code can notify its host when loaded instruction files exceed the model’s recommended size.

Status: Feature-flagged; default off through `tengu_jolly_aurora`.

Details:

- The warning measures `CLAUDE.md`, rules files, and their imported instructions.
- It reports the combined character count, recommended limit, and file count.
- Where useful, it also identifies the largest file’s size.
- The CLI implementation targets Claude Desktop’s Code tab.
- The emitted data supports a host-rendered warning; it does not prove that every host displays one.

Evidence: Search for `"tengu_jolly_aurora"`, `"instruction_size_warning"`, `"total_limit_chars"`, and `"largest_chars"`.


### Preserve Completed Home-Directory Writes During Cloud Handoff [In Development]

What: A cloud turn handoff can carry files from already-completed Write calls into the receiving worker.

Status: Feature-flagged; default off through `tengu_fizzy_petal`.

Details:

- The receiving worker validates the completed calls and their success results before reconstructing files.
- The implementation limits transfers to 16 files and 8 MiB of combined content.
- It rejects conflicting paths, files subsequently changed by Edit or NotebookEdit, and calls that do not match the built-in Write tool.
- The session must be working from its home directory.
- Auto mode and permission modes that would ask before writing are excluded.
- This is managed cloud-session handoff infrastructure, not a new public command.

Evidence: Search for `"tengu_fizzy_petal"`, `"carried_writes"`, `"carried Writes are not placed in auto mode"`, and `"handleHandedOffTurn: could not write the files"`.


### Review Updated Project Command Checks for Cloud Work [In Development]

What: A person can decide whether a cloud session should use an updated project command-check script.

Status: Feature-flagged; default off through `tengu_violin_overstand`.

Details:

- The implementation compares recorded and current command-check scripts.
- A changed check can trigger a decision about accepting the updated version.
- If a check stops working after project files change, the person can choose whether the session continues without it.
- Acceptance is recorded so later sessions can compare against the approved version.
- This extends existing cloud hook verification rather than introducing cloud hooks.

Evidence: Search for `"tengu_violin_overstand"`, `"This project's command check changed since the last time"`, and `"Run commands without it for the rest of this session?"`.

## Notes

- Update scripts that use `claude project purge` to `claude purge`; the old spelling still works.
- `/autocompact` now writes per-model preferences, so inspect model-specific settings when troubleshooting an unexpected window.
- Separate VS Code extension, SDK-package, admin-console, and Claude Tag changes in the published notes are outside this CLI-source analysis.
- Bun module wrappers, renamed identifiers, reordered modules, and rebundling artifacts are excluded from the changelog.


Generated with:
- tool: `harness-investigations@a4a08d7-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.288.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.288.txt`
- source modules: `archive/claude-code/original/cli-v2.1.288.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
- official release notes: `archive/claude-code/changes/release-notes-v2.1.288.md`
