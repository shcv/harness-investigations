# Changelog for version 2.1.212

## Summary

This release ships the SendFeedback tool — Claude can now draft product feedback for users to review and send — alongside a major overhaul of the auto-mode setup wizard, full live-edit support for published artifacts, and significant Windows sandbox improvements. Several internal systems were consolidated or removed, including the situational-context-tips catalog.


## New Features


### SendFeedback Tool and /feedback Command

What: Claude can now autonomously draft product-feedback reports at high-signal moments. Drafts land in a local queue; nothing is sent without your explicit approval. You review, edit, and submit (or discard) via `/feedback`.

Usage:
```
/feedback          # open the feedback draft panel
/feedback          # view, review & send, or discard queued drafts
```

Details:
- Claude queues drafts silently (no interruption mid-task). A footer counter shows how many are waiting.
- Each draft includes session context, request IDs, and optionally a transcript excerpt.
- If the transcript contains third-party markers (e.g. content from other providers), it is withheld from the draft automatically.
- Per-session cap: once the limit is hit, Claude stops queuing new drafts for that session (existing ones are unaffected).
- The `feedbackDrafts` setting controls notification behaviour: `"notify"` (default) shows a one-line notice; `"quiet"` shows only the footer counter; `"off"` disables the tool entirely for that session.
- Drafts are local-only and expire after 30 days if unsent.

Evidence: SendFeedback tool definition (search for `"SendFeedback"`) and feedback draft queue (search for `"Feedback draft queued locally"`)


### Artifact Live-Edit Action

What: The Artifact tool now has a `live-edit` action that updates an already-published artifact in place without minting a new URL.

Details:
- Pass `action: "live-edit"` to apply incremental `ops` to a deployed artifact.
- Requires the live-edit module to be present in the build; returns `"live-edit is not available in this build"` if absent.
- `ops` is not valid with any other action — validation rejects it with a clear error message.
- `live-edit` suppresses the always-allow permission rule and bypasses the whole-tool-allow rule, so it always prompts for permission separately.

Evidence: Artifact tool handler (search for `"live-edit is not available in this build"`)


### Artifact lang Parameter

What: Published artifacts now accept (and documentation requires) a `lang` parameter — a BCP-47 language tag for the page's text content.

Details:
- The tag becomes the page's `<html lang>` attribute, which screen readers, hyphenation engines, and search rely on.
- Match the content's language, not the conversation's. For mixed-language pages, use the dominant one.
- Example values: `"en"`, `"ja"`, `"pt-BR"`.

Evidence: Artifact prompt documentation (search for `"BCP-47 language tag of the page's text content"`)


### Web Search Per-Session Budget Control

What: A new environment variable caps how many WebSearch calls Claude can make in a single session.

Usage:
```bash
CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION=20 claude
```

Details:
- Once the cap is hit, Claude receives an explicit message instructing it not to issue more searches and to proceed with already-gathered information.
- The cap applies across the full session including subagents.

Evidence: Budget-exceeded message (search for `"this session has used its web search budget"`)


## Improvements


### Auto-Mode Setup: GitHub Org Scanning and Reset Command

What: The `/auto-mode-setup` wizard now optionally scans your GitHub organisation in addition to your local repo and recent sessions. A new `claude auto-mode reset` CLI subcommand resets classifier configuration to factory defaults.

Usage:
```bash
/auto-mode-setup       # run the full scan + proposal review
claude auto-mode reset # reset autoMode section in user settings to defaults
claude auto-mode config # show current effective auto-mode rules
```

Details:
- When GitHub org scanning is active, the background tasks list shows a stoppable entry for the scan.
- The reset command removes the `autoMode` section from user settings only; managed or `--settings` flag sources are unaffected.
- Better error handling: if a previous setup is already in progress you get a specific message instead of a silent failure.

Evidence: Wizard orchestrator (search for `"also scanning your GitHub org — stoppable from the background tasks list"`)


### Windows Sandbox: Hardened Install and Richer Error Messages

What: The Windows sandbox install process (`srt-win`) now exposes named arguments and returns structured error codes with actionable guidance. Three new error classes give Claude better context for recovery.

Details:
- New `srt-win install` flags: `--proxy-port-range`, `--sandbox-user`, `--sublayer-guid`, `--force`.
- New exit-code map: 10 = cancelled at elevation prompt (sandbox user already provisioned), 12 = WFP filter install failed, 13 = conflicting filters (use `--force` or a different sublayer GUID), 14 = sandbox user provisioning failed.
- `SandboxCommandTooLongError`: raised when an assembled Windows sandbox command line is near the OS limit (~32 KB). The message explains that PowerShell base64-encodes the script (~2.7×) and suggests writing to a file instead.
- `SandboxPolicyRefusalError`: raised when enterprise policy requires sandboxing but the command cannot run sandboxed on this platform.
- `SandboxUnavailableForShellError`: raised when the requested shell is not a bash-family executable that the sandbox runtime accepts (falls back to Git Bash).
- CA cert errors from srt-win now suggest `Ask your administrator to trust the sandbox CA` with a docs link.

Evidence: srt-win install handler (search for `"srt-win install: filters already exist under this sublayer"`)


### Ctrl+J as an Alternative Newline Shortcut

What: In the input box, pressing Ctrl+J now inserts a newline — the same as Enter in multiline mode. The hint `ctrl+j for newline` is shown with multiline input tips.

Evidence: Input key handler (search for `"ctrl+j for newline"`)


### Fork Session: Clearer Refusal Messages

What: `/fork` now gives specific explanations when a fork is not possible, rather than a generic error.

Details:
- "Cannot fork — session persistence is off, so the new session would have nothing to start from."
- "Cannot fork — this session was started with launch flags (safe or bare mode, a custom system prompt, a tool allowlist, or restricted settings) that the copy wouldn't inherit."
- "Nothing to fork yet — send a message first."
- "Couldn't fork — this conversation is still being saved. Try again in a moment."
- Forked sessions now carry `CLAUDE_CODE_RESUME_SOURCE_ALIVE` in the environment, allowing the new session to know whether its source is still running.

Evidence: Fork refusal messages (search for `"Cannot fork — session persistence is off"`)


### Worktree Creation: Symlink Safety Check

What: Creating a git worktree is now rejected if any of the relevant paths (`.claude`, `.claude/worktrees`, or the target path) is a symbolic link.

Details:
- A repository-committed symlink at these locations could redirect worktree creation outside the repository root, which is a security concern.
- The error message names the symlink path and asks you to remove it before retrying.

Evidence: Worktree creation guard (search for `"is a symlink. A repository-committed symlink at .claude"`)


### Shell CWD Read-Back: Network and Automount Guards

What: The CWD read-back that updates Claude's working directory after shell commands now has several new rejection cases to avoid silently adopting a bad path.

Details:
New cases that cause the read-back to be ignored (with a debug log entry):
- Path contains a dot-segment (`.` or `..` component).
- Path is a network path on Windows (UNC or mapped drive).
- Path crosses an automount host boundary.
- Path resolves through a network symlink or junction.
- Path is not an absolute path.
- Path is not readable.
- Path is not a directory.

Evidence: CWD validation function (search for `"shell cwd read-back contains a dot-segment; ignoring"`)


### MCP: WebSocket Subprotocol Display

What: When an MCP server advertises WebSocket subprotocols, they are now shown in parentheses in the connection info display.

Evidence: Subprotocol formatter (search for `"subprotocols:"`)


### TLS Certificate Env Vars Passed Through Agent Isolation

What: Six TLS and OAuth environment variables are now propagated into isolated subagent and worktree environments.

Details:
The new pass-through set: `CLAUDE_CODE_CLIENT_CERT`, `CLAUDE_CODE_CLIENT_KEY`, `CLAUDE_CODE_CLIENT_KEY_PASSPHRASE`, `NODE_EXTRA_CA_CERTS`, `NODE_TLS_REJECT_UNAUTHORIZED`, `CLAUDE_CODE_OAUTH_SCOPES`.

Evidence: Env-var pass-through set (search for `"CLAUDE_CODE_CLIENT_CERT"`)


### CA Cert Skipping Warning

What: When `NODE_EXTRA_CA_CERTS` is set in settings but the session is running under a host-managed provider, Claude Code now logs an explicit warning instead of silently ignoring the cert.

Evidence: Warning message (search for `"CA certs: skipping settings-sourced NODE_EXTRA_CA_CERTS under host-managed provider"`)


### forceLoginMethod: Improved Enforcement Messages

What: The `forceLoginMethod` setting now produces more specific error messages when the actual login method doesn't match.

Details:
- Gateway-forced: "forceLoginMethod is 'gateway' in managed settings; run /login from an interactive terminal to authenticate."
- Claude.ai forced: "forceLoginMethod is 'claudeai' in settings; log in with a Claude.ai subscription account instead."
- Console forced: "forceLoginMethod is 'console' in settings; log in with an Anthropic Console account instead."

Evidence: Login method validator (search for `"forceLoginMethod is 'gateway' in managed settings"`)


### PreToolUse Hook Error Message Improvement

What: When a PreToolUse hook crashes unexpectedly, Claude now receives a more informative message explaining that the tool call was not executed and other hooks may not have completed.

Evidence: Hook error constant (search for `"PreToolUse hook failed with an unexpected error"`)


### Artifact Syntax Highlighting: Deferred Bundle Loading

What: Syntax highlighting in published artifacts now loads the highlight.js runtime as a deferred bundle rather than inlining it on every publish. This reduces artifact size when the page contains no code blocks.

Details:
- Controlled by feature flag `tengu_artifact_hljs_highlight` (default: enabled).
- The bundle is only appended when the page body contains fenced code blocks with recognised language classes.
- The inline runtime applies per-element budget limits and skips blocks that are already highlighted or too large.

Evidence: Bundle feature flag (search for `"tengu_artifact_hljs_highlight"`) and bundle loader (search for `"/$bunfs/root/hljsBundle.generated.min.js"`)


## Bug Fixes

- Plan mode now correctly skips the sandbox auto-allow path, so sandboxed tool calls in Plan mode continue to require confirmation rather than being auto-approved. (search for `"mode === \"plan\""`)
- PR resolution state is now returned explicitly from git command handlers instead of being stored as a side effect, fixing a class of missed-PR-close events. (search for `"prResolved"`)
- The `--resume-session-at` CLI flag is now passed as a single `--resume-session-at=VALUE` argument rather than two separate tokens, fixing argument parsing edge cases in subprocesses. (search for `"--resume-session-at="`)
- Effort parameter rejection from the API now correctly latches per-model instead of per-session, so swapping to a model that does support effort later in the conversation works as expected. (search for `"rejected output_config.effort; latching unsupported"`)


## In Development

Features with infrastructure added but not yet enabled for general use.


### Stone Shell Memory Guidelines [In Development]

What: A comprehensive, opinionated guidance system for Claude's persistent memory across sessions — when to write, what makes a good memory file, and how to treat memory as a starting point rather than ground truth.

Status: Feature-flagged (`tengu_stone_shell`, default off)

Details:
- When enabled, Claude receives a detailed in-context guide covering: applicability, durability, legibility criteria for memory files; when it must save (on corrections, on environmental discoveries); how to write (before finishing the turn, not after).
- Replaces simpler memory-guidelines approaches; the guide is ~1,500 words and covers anti-patterns in depth.

Evidence: Memory guidelines text (search for `"Your memory system helps you act as a more effective collaborator"`)


### Propose Skills Tool [In Development]

What: A new `propose_skills` tool that surfaces recurring multi-step procedures from a session as skill proposals, showing the user a review card to save them as reusable slash commands.

Status: Feature-flagged (`tengu_propose_skills`, default off). Additionally requires a remote environment (`CLAUDE_CODE_REMOTE_ENVIRONMENT_TYPE`) and `CLAUDE_CODE_SYNC_SKILLS` to be set.

Details:
- Render-only: calling the tool shows the review card but does not write any files; the user saves from the card.
- Accepts up to 3 proposals per call; each can be a new skill or an improvement to an existing one.
- Claude is instructed to call it when the same multi-step procedure has recurred, not for one-off tasks.

Evidence: Tool definition (search for `"Show the user a review card of proposed skills to save"`)


Generated with:
- tool: `harness-investigations@d5cccf8-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.212.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.212.txt`
