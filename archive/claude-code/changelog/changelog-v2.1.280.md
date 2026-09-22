# Changelog for version 2.1.280

## Summary

Compared with 2.1.278, this release adds Opus 5.5 support and environment-based loading of local plugins. It improves cloud-upload safeguards, remote-command recovery, MCP configuration, and auto-mode failure handling. Responsive mode and linked-worktree cloud sync also gain implementation code, but remain disabled by default or unavailable in this build.

## New Features


### Opus 5.5 support

What: Claude Code now recognizes Opus 5.5 and includes it in model selection and provider mappings.

Usage:
```bash
claude --model claude-opus-5-5
claude --model 'claude-opus-5-5[1m]'
```

Details:

- The built-in fallback for the `opus` alias changes from Opus 5 to Opus 5.5. Account-provided model defaults and explicit configuration can override that choice.
- The catalog describes a 1-million-token context window, medium default effort, and support for higher effort levels and fast mode.
- Provider mappings include Bedrock, Vertex, Foundry, and other supported routes. Actual access still depends on the provider and account.
- Vertex users gain the model-specific region override `VERTEX_REGION_CLAUDE_5_5_OPUS`.
- Opus 5 remains selectable as the previous version; Opus 4.8 is labeled legacy.

Evidence: Model catalog, alias resolution, and picker entries—search for `"claude-opus-5-5"`, `"Opus 5.5 for long sessions"`, and `"VERTEX_REGION_CLAUDE_5_5_OPUS"`. These model identifiers are absent from 2.1.278.


### Load local plugins through an environment variable

What: `CLAUDE_CODE_PLUGIN_DIRS` supplies local plugin directories without repeating `--plugin-dir` on each invocation.

Usage:
```bash
CLAUDE_CODE_PLUGIN_DIRS="$HOME/plugins/review:$HOME/plugins/tools" claude
```

Details:

- Use the platform’s path-list separator: `:` on macOS/Linux and `;` on Windows.
- Entries must resolve from absolute local paths or paths beginning with `~`; invalid entries are skipped with a warning.
- Directories are combined with command-line plugin directories and deduplicated.
- The setting is carried into supported background-session launches and recognized by `claude agents`.
- Existing restrictions on loading plugins still apply.

Evidence: Environment parsing and startup registration—search for `"CLAUDE_CODE_PLUGIN_DIRS"` and `"a plugin folder here is an absolute local path or starts with ~"`. The variable is absent from 2.1.278.

## Improvements


### Configurable MCP description length

MCP tool descriptions and server instructions now use a configurable character limit. This lets users retain more information from servers whose descriptions exceed the existing default.

Usage:
```bash
CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH=8192 claude
```

The default remains 2,048 characters. The override accepts a positive integer.

Evidence: Shared description-limit lookup and MCP consumers—search for `"CLAUDE_CODE_MAX_MCP_DESCRIPTION_LENGTH"`. The old version uses a fixed limit.


### Saved model defaults can update account-side selection

When a model choice is saved as the default, eligible sessions also send that choice to the account’s model-selector state. The local settings write remains the primary operation; a background synchronization failure does not undo it.

This applies to primary sessions using an account-scoped, server-provided model catalog. It does not establish synchronization for every provider or session type.

Evidence: Successful default-save handling and account update—search for `"/api/organizations/:orgUUID/model_selector_state/"` and `"selection_source"`. The update endpoint is absent from 2.1.278.


### Retain thinking across more model switches

The previous version supported retaining eligible thinking when upgrading models. This release extends that handling to other model changes on supported first-party connections.

The new `CLAUDE_CODE_RUSTLING_PIXEL` control accepts:

- `all`: request retention across model changes.
- `upgrade`: retain the earlier upgrade-only behavior.
- `none`: disable this retention.

The new path defaults to `all` for eligible connections and falls back when the server rejects it. It does not guarantee that every model accepts every earlier thinking block.

Evidence: Request normalization and retention policy—search for `"CLAUDE_CODE_RUSTLING_PIXEL"`, `"api_keep_thinking_on_model_change"`, and `"api_keep_thinking_on_upgrade"`.


### Safer cloud uploads with clearer recovery instructions

The existing `claude --cloud` workflow adds checks around repository state, file selection, and upload preparation.

Details:

- Additional checks detect changed or irregular Git metadata, invalid index entries, and objects whose contents do not match their IDs.
- Upload handling expands protection for files reachable through Claude Code’s configuration.
- Cloud-start and synchronization controls distinguish machine-owner configuration from repository-provided settings.
- New diagnostics explain conditions such as unfinished Git operations, shallow or partial clones, unreadable settings, and upload limits.
- If a cloud session was created empty and never received the project files, local messages are held instead of being sent to that empty checkout.

Evidence: Upload validation and empty-session handling—search for `"its git directory holds an object that is not what its id names"`, `"linked from your Claude Code configuration"`, and `"This cloud session was created empty and never received"`.


### Re-register a removed computer [Gradual Rollout]

In the existing gated computer-binding workflow, starting a cloud session can now offer to register a computer that was removed from the account’s device list.

Choose **Yes, register this computer again** to restore its eligibility for local commands and synchronization. Choosing **Not now** starts the session cloud-only; a later `claude --cloud` launch can ask again.

Evidence: Device-registration recovery and confirmation dialog—search for `"This computer was removed from your devices"` and `"Yes, register this computer again"`. The enclosing workflow remains gated by `"tengu_violin_wood"`.


### Better recovery for attached-machine commands

Remote-command handling gains more precise follow-up reporting when a machine stops answering.

Details:

- A later result can correct an earlier uncertain outcome: the command ran, remains running, did not run, or finished but no longer has retrievable output.
- Recovery instructions distinguish safe retries from commands whose effects need checking first.
- Replacement cloud workers can request fresh tool announcements from attached clients.
- Claude receives explicit instructions to pause machine-dependent work while that machine is unavailable.

Evidence: Late-outcome reporting and reconnection requests—search for `"That machine now reports it DID run"`, `"remote_tools_reannounce"`, and `"Attached earlier and not reconnected yet:"`.


### Built-in features survive customization shutdown

Safe mode now filters out installed plugins while preserving built-in plugins. Hook-disable settings likewise distinguish installed customization hooks from features built into Claude Code.

The settings descriptions clarify that built-in features have their own switches. Managed-hook handling also explicitly includes plugins enabled by managed settings.

Evidence: Plugin filtering and settings descriptions—search for `"Safe mode: installed plugins are disabled"` and `"Features built into Claude Code are not hooks in this sense and keep working"`.


### Auto mode stops repeated attempts without a safety verdict

Server-classifier failures now receive clearer treatment:

- Transient failures explain that a retry may succeed and apply increasing delays.
- Failures that cannot evaluate the request are distinguished from an actual denial.
- After ten consecutive responses without a usable safety verdict, the turn or subagent stops instead of continuing the same cycle.
- The terminal explains that the user can send another message or switch out of auto mode.

Evidence: Retry accounting, terminal notices, and turn-ending decisions—search for `"Auto mode unavailable — stopped after repeated responses with no safety verdict"` and `"responses in a row, so Claude stopped"`.


### Runner lifecycle hooks use stricter Git configuration

Git commands executed by runner checkout and post-session hooks now receive tighter configuration boundaries.

Details:

- Repository and global Git hooks are not inherited by default.
- Custom SSH commands and credential-prompt programs must come from the runner’s environment.
- With `--configure-git`, signing artifacts are materialized per session for lifecycle-hook use.
- Without `--configure-git`, commit and tag signing are disabled for hook-made commits.
- Startup warnings explain configurations that will no longer be used, including Git LFS hook dependencies.

Evidence: Runner Git setup and migration warnings—search for `"lifecycle-hook git pins"`, `"hook-made commits signed per session"`, and `"core.sshCommand is set in the"`.

## Bug Fixes

- Write, Edit, and NotebookEdit now reject a target that is itself a symbolic link and direct Claude to the resolved target path. This prevents edits from silently following that final link. Search for `"Write target is a symbolic link"`.

- The Write tool can recover from certain incorrectly named arguments: `path` becomes `file_path`, and an unambiguous `file_text` or `file_content` becomes `content`. An extra `description` is discarded, and the correction is reported. This recovery defaults on. Search for ``"`path` was read as `file_path`."`` and `"tengu_noble_mountain"`.

- A plugin manifest that explicitly references its automatically loaded `hooks/hooks.json` no longer produces a duplicate-hook error for that standard file; it is loaded once. Search for `"names the standard hooks/hooks.json, which loads on its own; loaded once"`.

- Agent-type hooks attached to `PermissionRequest` now fail with a specific explanation and guidance to use a command- or HTTP-type hook. Search for `"agent-type hooks are not supported for PermissionRequest events"`.

- Marketplace validation rejects alternative spellings of reserved marketplace names, including normalized Unicode and invisible-character variants. Existing conflicting entries receive removal guidance. Search for `"another spelling of the reserved marketplace name"`.

- A server-side safety block now cancels outstanding streamed tool work and records that already-started calls may have had effects. Search for `"A safety monitor blocked this turn, so this tool call was cancelled"`.

- Cloud code-review reporting distinguishes a remotely stopped review from a failed review or a session that disappeared after an account change. Search for `"cloud review was stopped before it finished"` and `"Review stopped"`.

- Recognized Bash deletions of synced memory files are checked against the existing mass-deletion hold before running. The message explains how to delete in smaller batches instead of triggering restoration. Search for `"Memory sync holds deletions when more than"`.

- Truncated memory-server answers now include an instruction to read the complete file before rewriting it, reducing the chance of replacing a memory file with partial contents. Search for `"Call memory_read on this path before rewriting the file"`.

- MCP tools marked as app-only through `_meta.ui.visibility` are withheld from the model while remaining available in host status metadata. Search for `"its _meta.ui.visibility omits"`.

- Side questions receive an explicit placeholder for tool calls still running, queued, or awaiting approval in the main conversation. Search for `"No result yet — this call is still in progress in the main conversation"`.

## In Development

These additions are gated or disabled in the shipped code. Their presence does not establish general availability or a release date.


### Responsive mode [In Development]

What: An experimental mode asks Claude to acknowledge each user message immediately before thinking or using tools.

Status: Feature-flagged; `"tengu_quiet_ember"` defaults to false.

Details:

- A built-in plugin supplies the response instructions and composer behavior.
- An eligible new message can interrupt the current turn so Claude addresses it promptly.
- The composer hint distinguishes immediate delivery from queuing: “enter answers now · ctrl+x enter queues”.
- Availability is limited to eligible attended sessions; it is not a universally enabled mode.

Evidence: Plugin registration and availability check—search for `"responsive-mode"`, `"tengu_quiet_ember"`, and `"enter answers now · ctrl+x enter queues"`.


### Cloud synchronization for linked Git worktrees [In Development]

What: New infrastructure prepares linked worktrees for cloud upload and file synchronization using a private Git administration directory.

Status: Disabled in this build.

Details:

- The old source rejected linked-worktree snapshots outright.
- The new source adds layout validation, private Git-directory preparation, and checks for worktrees that move or change during a session.
- The shipped `linkedWorktreesServed()` accessor reads a value initialized to false, with no production enablement path.
- Fast-forwarding cloud commits into a linked worktree remains explicitly unavailable.

Evidence: Linked-worktree preparation and disabled enablement—search for `"a linked working tree's git may only run under a private admin dir"`, `"serveLinkedWorktreesForTesting is test-only"`, and `"fast-forwarding a branch from a linked working tree is not enabled yet"`.


### Inline definitions for late-arriving tools [In Development]

What: Claude Code can send newly introduced tool definitions within conversation updates.

Status: Feature-flagged; `"tengu_brisk_meadow"` defaults off, with a `CLAUDE_CODE_INLINE_TOOLS` override.

Details:

- Earlier versions already supported late tool additions; this adds definitions carried directly in those additions.
- The implementation detects unsupported providers, rejected headers, and tool-name conflicts.
- Rejection falls back to declaring tools through the existing mechanism and disables the inline path for the rest of that conversation.

Evidence: Inline-definition construction and fallback—search for `"tool_definition"`, `"CLAUDE_CODE_INLINE_TOOLS"`, and `"falling back to declaring late tools in tools[]"`.


### Warnings for parallel agents sharing a checkout [In Development]

What: Claude can detect another write-capable agent in the same working directory and encourage worktree isolation.

Status: Feature-flagged; `"tengu_twinkling_boole"` defaults to false.

Details:

- The check considers running agents, write-capable tools, working directories, and existing isolation.
- New guidance recommends `isolation: "worktree"` for parallel code-writing agents where supported.
- The change supplies warnings and instructions; it does not automatically isolate every agent.

Evidence: Overlapping-agent detection and prompt guidance—search for `"another write-capable agent is already running"` and `"tengu_twinkling_boole"`.


### Persistent maximum-effort reminder [In Development]

What: A terminal reminder makes it more visible when the session is using maximum effort.

Status: Feature-flagged; `"tengu_proud_clover"` defaults to false, with a `CLAUDE_CODE_MAX_EFFORT_REMINDER` override.

Details:

- The reminder appears when effective effort is `max`.
- It points users to `/effort` to change the setting.
- This adds visibility to an existing effort level.

Evidence: Reminder activation and rendering—search for `"Max effort · "`, `" · /effort to change"`, and `"CLAUDE_CODE_MAX_EFFORT_REMINDER"`.


### Additional capabilities for experimental plugin hooks [In Development]

What: The existing function-hook system gains streaming subprocesses, message sending, clipboard access, and expanded transcript access.

Status: Early access under the existing `"tengu_plugin_hooks_modules"` gate or `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=1`.

Details:

- `$.process.spawn` exposes incremental stdout and stderr.
- `$.session.send` sends messages through the session’s messaging path.
- `$.session.messages` gains agent-targeted transcript access; transcript access itself already existed.
- `$.ui.copy` adds clipboard handling, with explicit unsupported-surface results.
- Installed plugins remain subject to hook-loading and customization restrictions.

Evidence: New hook operations and early-access diagnostics—search for `"$.process.spawn"`, `"$.session.send"`, `"$.ui.copy"`, and `"hooks modules are not turned on for installed plugins"`.

## Notes

- This changelog compares **2.1.278 → 2.1.280**, as identified by the supplied diff. Claims were checked against both versions and the original split-module sources; rebundling changes are excluded.
- If a workflow edits a symlink path, change it to use the actual target path.
- Replace agent-type `PermissionRequest` hooks with command- or HTTP-type hooks.
- Runner operators whose lifecycle hooks depend on `core.sshCommand` or `core.askPass` should configure `GIT_SSH_COMMAND` or `GIT_ASKPASS` in the runner environment. Review the new startup warnings for Git-hook and Git LFS dependencies.
- No version-specific official release notes were supplied; the bundled release-note text stops at 2.1.278.


Generated with:
- tool: `harness-investigations@8c9c30b-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.280.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.280.txt`
- source modules: `archive/claude-code/original/cli-v2.1.280.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
