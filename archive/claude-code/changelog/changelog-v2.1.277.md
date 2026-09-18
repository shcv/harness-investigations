# Changelog for version 2.1.277

## Summary

Compared with 2.1.276, this release removes the deprecated `TaskOutput` tool, adds invisible-character checks before sending prompts, and improves `/ultrareview` handling of commit bases and first commits. It also extends plugin hooks and ships gated infrastructure for terminal Mermaid diagrams and cloud-session repository trust.

## New Features


### Plugin hooks for prompt edits and attachments

What: Plugins gain hooks for editing the prompt as it changes and transforming attachment text before it reaches the model.

Usage: Plugin authors can register handlers for `"prompt.edit"` and `"prompt.attachment"` through the function-hook interface.

Details:

- `prompt.edit` receives text-edit information and supports returning revised text and cursor positions.
- Edits are checked against the current draft; an outdated rewrite does not overwrite subsequent typing.
- `prompt.attachment` operates on the model-facing text of supported context attachments. This is not a general-purpose binary upload hook.
- Attachment-hook failures preserve the engine’s original text.
- These additions require a loaded function-hook plugin; they do not introduce new slash commands.

Evidence: New hook registration, validation, composer integration, and pre-request attachment processing; search for `"prompt.edit"`, `"prompt.attachment"`, `"a rewrite no longer fits the draft"`, and `"the dispatch failed, the text stands as the engine rendered it"`.


### Gateway support for proxy-enforced outbound access

What: Gateway operators can explicitly delegate outbound hostname resolution and destination enforcement to their forward proxy.

Usage:

```bash
export HTTPS_PROXY="http://proxy.example:8080"
export NO_PROXY=""
export no_proxy=""
export CLAUDE_GATEWAY_PROXY_IS_EGRESS_BOUNDARY=1
```

Start the gateway with these variables in its environment.

Details:

- Requires a usable HTTP or HTTPS proxy.
- Refuses to activate while either proxy-bypass variable is nonempty.
- Cannot be combined with `CLAUDE_GATEWAY_ALLOW_LOOPBACK`.
- When active, the gateway relies on the proxy’s destination policy instead of its own local address checks. Configure the proxy’s allowlist accordingly.
- Invalid combinations produce explanatory warnings and retain local checks.

Evidence: Original module initialization and request-policy checks; search for `"CLAUDE_GATEWAY_PROXY_IS_EGRESS_BOUNDARY"` and `"outbound requests hand it hostnames and rely on its allowlist"`.

## Improvements


### Invisible-character review before sending prompts

Claude Code now removes selected invisible characters from prompt text and pasted text. When an interactive submission changes, it leaves the cleaned prompt available for review and asks you to press Enter again.

The implementation distinguishes character classes and conditionally preserves characters needed for legitimate text, rather than deleting every invisible Unicode character indiscriminately. Launch prompts also receive a removal notice.

Evidence: Sanitizer calls in prompt submission and dispatch paths; search for `"Removed 1 invisible character"`, `"review and press Enter to send"`, and `"tengu_tranquil_cloud"`. The controlling flag defaults to enabled.


### More useful `/ultrareview` base selection and first-commit handling

`/ultrareview` now explicitly accepts a base commit as well as a branch or PR number:

```text
/ultrareview <base-commit-sha>
```

When the selected comparison has no changes, the command provides more specific recovery guidance, including a parent-commit suggestion for reviewing the latest commit.

An interactive review can also offer to review every file in the repository’s first commit. It shows the scope and estimated cost before proceeding, retains review-size limits, and tells users when untracked files need to be added to Git.

These changes extend the existing ultrareview workflow; its account and service availability requirements still apply.

Evidence: Base-reference validation, empty-diff recovery, and first-commit confirmation; search for `"takes a PR number, a base branch or commit"`, `"To review your latest commit anyway"`, and `"Reviewing every file in the first commit"`.


### Background-task output moves to `Read`

The previously deprecated `TaskOutput` tool is removed. Claude should read a background task’s output file with `Read`; agent results continue to arrive through their existing result and notification paths.

The `taskOutputMaxChars` setting remains recognizable but no longer changes behavior. Legacy output-tool names are also recognized as removed tools during configuration validation.

Evidence: Tool removal, retired-name handling, and the settings schema; search for `"the TaskOutput tool was removed"`, `"rule names a removed tool"`, and `"--tools exclusion names a removed tool"`.


### Plugin reloads respect `ConfigChange` hooks

Watched plugin-file changes now pass through the `ConfigChange` hook check before reloading. If a hook blocks the change or the check fails, the currently loaded plugin stays in place.

This gives users and administrators control over changes that would otherwise become active during a session.

Evidence: Plugin-directory watcher reload gate; search for `"ConfigChange hook blocked the reload, the loaded version stays"` and `"plugin-dir watch: the ConfigChange hooks"`.


### Clearer plugin installation recovery

Plugin replacement now handles occupied version directories and failed swaps more carefully. It can set the existing installation aside, restore it when replacement fails, and recognize when another process has already installed the same staged content.

Errors distinguish a busy directory, insufficient filesystem access, an installation that was restored, and one that needs reinstalling. Restoration is not guaranteed on filesystems that require deleting the old directory before replacement.

Evidence: Original version-directory replacement implementation; search for `"The previously installed copy was moved back"`, `"another process published exactly the staged tree"`, and `"Run the install again once other Claude Code sessions"`.


### More actionable artifact publishing failures

Artifact publishing gains explicit handling for rate limits and temporarily unavailable server contracts. Rate-limit handling includes a bounded retry and explains when nothing was published.

If an artifact was already reserved, the recovery message identifies the existing target so a retry does not unnecessarily create another artifact.

Evidence: Publishing retry and recovery paths; search for `"Artifact publishing is rate-limited right now"`, `"this tool already waited and sent it once more"`, and `"targeting it avoids reserving another"`.


### Optional thinking highlights for hosted sessions

The existing `--thinking-display` option now accepts `highlights`, intended to return short titles for stretches of thinking instead of prose summaries.

```bash
claude --thinking-display highlights
```

The source documents API support as limited to Anthropic-hosted Claude Code sessions. If the API rejects this display mode, the client retries with thinking text omitted and keeps that fallback for the process.

Evidence: CLI option choices, display-mode documentation, and retry handling; search for `"highlights"`, `"--thinking-display"`, and `"server rejected thinking.display highlights"`.

## Bug Fixes

- Search failures caused by process limits, memory pressure, or exhausted file descriptors now explicitly say that ripgrep did not start and that matches may still exist, with recovery guidance. Search for `"ripgrep could not start, so nothing was searched"`.

- `Write` now rejects directories and nonregular files such as devices, FIFOs, and sockets before continuing with normal file-write handling. Search for `"Write only creates or overwrites regular files"`.

- Invalid marketplace allowlists fail closed instead of silently removing the restriction. Invalid `disableSideloadFlags` values also reject sideload flags until corrected; malformed marketplace blocklists produce explicit warnings that they cannot be enforced. Search for `"strictKnownMarketplaces"`, `"no marketplaces admitted"`, and `"sideload CLI flags rejected"`.

- Update checks reject malformed version responses and validate configured minimum and maximum versions before comparing them. Search for `"npm view exited 0 but stdout is not a valid semver version"` and `"requiredMaximumVersion is not a valid semver version"`.

- Agent-memory loading adds checks for links, special files, and paths that cannot be verified inside the working copy. When these checks reject a memory location, Claude is instructed to treat it as read-only for the session. Search for `"was not loaded: it or its folder is a link or a special file"`.

- Attaching a folder already served by another Claude Code process now reports that conflict directly. Search for `"This folder is already served by another Claude Code on this device"`.

- Terminal wrapping gains a plain hard-wrapping fallback when computed wrapped rows do not cover the text correctly. Search for `"Wrapped rows do not tile the text; fell back to plain hard wrapping"`.

## In Development

These changes are present in the shipped source but remain gated or lack a complete activation path. Their presence does not establish general availability.


### Terminal Mermaid diagrams [In Development]

What: A built-in plugin renders Mermaid flowcharts and sequence diagrams as box-drawing text inside terminal replies.

Status: Feature-flagged; **[Gradual Rollout]**, with availability defaulting off.

Details:

- Includes Mermaid parsing, layout, and terminal rendering.
- Integrates through the plugin’s `ui.render` hook.
- Requires the relevant runtime capabilities and the `tengu_mermaid_mod` gate.
- The source does not establish an unrestricted launch or release date.

Evidence: Original built-in plugin source; search for `"Mermaid diagrams in the terminal"` and `"tengu_mermaid_mod"`. Its default-enabled value is false.


### Revised AGENTS.md plugin defaults [In Development]

What: The existing gated `agents-md` plugin changes its default from CLAUDE.md-only behavior to using AGENTS.md when the project lacks its own CLAUDE.md.

Status: Feature-flagged; **[Gradual Rollout]** under the existing default-off `tengu_agents_md_mod` gate.

Details:

- Renames the plugin option from `projectInstructions` to `instructionFiles`.
- Supports `claude-md`, `claude-md-or-agents-md`, `claude-md-and-agents-md`, and `managed-only`.
- Defaults to `claude-md-or-agents-md` when the plugin is active.
- Retains compatibility handling for the old option and logs migration guidance.
- This is a change to an existing plugin, not the first implementation of AGENTS.md support.

Evidence: Old and new plugin schemas and original module implementations; search for `"claude-md-or-agents-md"`, `"option projectInstructions in settings is honoured for now"`, and `"tengu_agents_md_mod"`.


### Repository trust for cloud access to attached computers [In Development]

What: Cloud sessions gain a repository-trust step before using an attached computer’s folder.

Status: Feature-flagged; **[Gradual Rollout]**, with `tengu_violin_bridgepin` defaulting off.

Details:

- Adds trusted, declined, unavailable, and no-repository states.
- Explains that approval covers what is attached to the cloud session.
- Handles terminals that cannot show the complete question or prove the answering device’s identity.
- Provides refusal and retry guidance when trust has not been granted.

Evidence: Trust-state handling and gated availability; search for `"confirm_repository_trust"`, `"Repositories not marked trusted"`, and `"tengu_violin_bridgepin"`.


### Sandboxed project command checks for cloud sessions [In Development]

What: Attached computers gain a guarded way to run project-defined command checks for cloud-originated operations.

Status: Feature-flagged; **[Gradual Rollout]**, with `tengu_violin_peg` defaulting off.

Details:

- Runs eligible checks in a read-only sandbox with restricted write and network access.
- Detects checks that differ from the recorded version.
- Falls back to asking the user when a check cannot finish, is not trusted, or tries to rewrite the command.
- Separate sender-attestation enforcement is controlled by `tengu_vast_tulip`, which defaults to observation rather than enforcement.

Evidence: Original hook-serving and sandbox code; search for `"Project command checks run in a read-only sandbox"`, `"tengu_violin_peg"`, and `"tengu_vast_tulip"`.


### Letting messages interrupt the wait for a tool result [In Development]

What: New infrastructure allows eligible tool calls to continue in the background while Claude responds to an incoming message.

Status: Infrastructure present; a complete message-triggered activation path was not found in the supplied sources.

Details:

- Web search and web fetch are marked as eligible for detachment.
- Includes foreground-call registration, background completion delivery, timeouts, and failure reporting.
- Certain hooks, noninteractive sessions, and nested or remote calls prevent detachment.
- Although `tengu_tool_detach` defaults to true, the shipped `backgroundNow` callbacks were found being registered without a corresponding invocation. The flag alone does not demonstrate that users can trigger this behavior.

Evidence: Original tool execution and registration paths; search for `"backgroundNow"`, `"tengu_tool_detach"`, and `"moved to the background to deliver a message"`.

## Notes

- Update instructions and tool configurations that reference `TaskOutput`, `AgentOutputTool`, `BashOutputTool`, `AgentOutput`, or `BashOutput`. Use output-file reads and agent result notifications instead; remove reliance on `taskOutputMaxChars`.
- For users of the gated `agents-md` plugin, migrate `projectInstructions` values as follows: `claude` → `claude-md`, `agents-fallback` → `claude-md-or-agents-md`, `both` → `claude-md-and-agents-md`, and `none` → `managed-only`.
- This changelog compares the CLI sources for 2.1.276 and 2.1.277, with substantive changes checked against the original Bun modules. Runtime rollout availability was not tested; module-wrapper changes and separate extension or SDK-package features are excluded.


Generated with:
- tool: `harness-investigations@2d591d6-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.277.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.277.txt`
- source modules: `archive/claude-code/original/cli-v2.1.277.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
