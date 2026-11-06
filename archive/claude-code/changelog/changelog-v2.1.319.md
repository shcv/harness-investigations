# Changelog for version 2.1.319

## Summary

The model picker gains an expandable `More models` list, and plugins can supply their own subagent status-line scripts. Moving a local conversation to the cloud now sends a generated summary, while non-interactive auto-mode runs can exit with an error when safety checks prevent work from running. File transfers through claude.ai connectors and a summary-based resume option are implemented behind gates that default to off.

## New Features


### Expandable Model Picker

The `/model` picker can tuck secondary choices under `More models`, keeping the main list shorter without removing access to the rest.

```text
/model
```

Searching includes the full model list. If your current model belongs to the collapsed group, that group starts expanded. Grouping appears when the catalog supplies at least two primary and two secondary choices.


### Plugin Subagent Status Lines

Plugins supplying a `subagentStatusLine` command through their own `settings.json` now receive `CLAUDE_PLUGIN_ROOT` and `CLAUDE_PLUGIN_DATA`. This lets a plugin run its bundled status-line script and use its persistent data directory without hard-coded installation paths.

These variables belong to the plugin-provided command. Commands configured elsewhere do not inherit another plugin’s paths, and execution is withheld if the required plugin data directory is unavailable.

## In Development


### Send Local Files to claude.ai Connectors

A new upload path lets compatible connector tools receive a local file’s contents when Claude supplies its path—for example, to upload a document or attach it to an email.

The implementation includes tool-schema discovery, upload handling, and an approval prompt naming the files and destination. It is gated by `tengu_steady_quail`, off by default.

Uploads require a claude.ai sign-in, a compatible connector, and approval at Claude Code’s own terminal prompt. Non-interactive runs, remotely started sessions, and teammate sessions cannot provide that approval. Organization policy and account eligibility can also block uploads.


### Download Files Offered by Connectors

Claude Code can recognize files offered in connector results, ask permission to download them, and save them under `connector-downloads`. Downloads retain their connector provenance and are kept out of Git.

The download path is wired into connector results but gated by `tengu_piped_planet`, off by default.

- Downloads are limited to 10 files per tool result and 100 MB per file.
- Each download has a five-minute timeout.
- A claude.ai sign-in and organization permission are required.
- Downloaded settings, skills, and MCP configuration are treated as connector data rather than loaded as project configuration.
- Worktree removal checks for downloaded files that Git would otherwise overlook.


### Resume an Inactive Conversation from a Summary

The existing quota warning shown when resuming an inactive conversation gains a `Resume from summary` choice. Claude writes a summary and continues from it, offering an alternative to resending the full conversation.

The dialog and continuation path are implemented behind `tengu_eager_brooks`, off by default. The option applies when resuming a conversation; it is not added to the warning shown during an already-open session’s idle period.


### Longer Bash Commands on Windows

A new Windows execution path splits long Bash commands across multiple process arguments, reconstructs them in Bash, and checks that the command arrived intact. This is intended to avoid truncation of commands with long text or heavy quoting.

The path is gated by `tengu_mossy_melody`, off by default. Administrators can prevent splitting with the managed setting:

```json
{
  "disableWindowsBashCommandSplit": true
}
```

Only managed settings honor this key. Keeping commands in one argument helps endpoint tools inspect the complete command line, but retains the existing length limitation.

## Other Changes

- Changed `claude --cloud <session-id>` to transfer a generated conversation summary instead of the previous conversation-text handoff; failed summarization prevents the move.
- Changed non-interactive text and JSON runs to exit with code `1` when unresolved auto-mode safety-check failures leave actions unexecuted; controlled by `tengu_truthful_wren`, on by default.
- Removed the Chrome browser tools `shortcuts_list` and `shortcuts_execute`; calls to them now return `Unknown tool`.
- Changed background-worktree checks to reject Git options that bypass worktree isolation, including `--ignore-other-worktrees`, forced worktree creation, `--update-head-ok`, and `git apply --unsafe-paths`.
- Changed plugin discovery from `--add-dir` folders to require the added folder’s own trust record before using its marketplace and plugin settings.
- Changed nested skill discovery to withhold newly discovered subfolder skills after the Bash sandbox has been enabled; turning the sandbox off does not clear that restriction.
- Added `CLAUDE_CODE_DISABLE_FEATURE_FLAGS=1` as a dedicated environment switch for disabling feature-flag evaluation.
- Added support for claude.ai Project addresses shaped like `https://claude.ai/code/project/<ID>` in `/project`.
- Improved auto-mode recovery with explicit choices to approve actions individually or leave auto mode when its server-side check is unavailable.
- Improved background MCP task notifications to distinguish temporary tracking failures from stopped tracking, and explain when reconnecting or resuming can restore updates.
- Improved authentication notices to identify usage billed through `ant auth login`, including when a previous claude.ai login has ended.
- Improved startup diagnostics when both legacy `.config.json` and `.claude.json` configuration files exist, identifying the file actually in use.
- Fixed Remote Control setup waiting indefinitely when an onboarding question receives end-of-input; it now exits with instructions for completing setup in a terminal.
- Fixed file rewind racing with unfinished backups; rewind now refuses to restore files until those backups finish.
- Fixed interrupted tool turns losing completed results while `PostToolUse` hooks are still running.
- Improved compaction so an already-submitted summary request can finish after an interruption and remain available for later use.

## Notes

Cloud handoffs now carry a summary, so the cloud session does not receive the original conversation itself. Local context such as mentioned files, selections, and hook output may remain behind. The original local session remains available through `claude --resume <session-id>`.

If a conversation is too long to summarize for a cloud move, resume it locally, run `/compact`, exit, and retry:

```bash
claude --resume <session-id>
# Run /compact in that session, then exit.
claude --cloud <session-id>
```

Automation using auto mode should handle the new nonzero exit when required checks cannot run. Switching permission modes changes which actions require approval; the new recovery dialog explains those consequences before switching.

If subfolder skills stop appearing after sandbox use, start Claude Code in the skill’s folder or use `/cd` there. For plugin settings from an added directory, open that directory directly and accept its trust dialog before reloading plugins.

When resolving a duplicate-config warning across machines sharing a home directory, update every machine to 2.1.319 or later, stop Claude processes on all of them, and move aside the unwanted file before restarting.


Generated by `harness-investigations@5d3a44b-dirty` using codex `gpt-6.1-sol` (medium effort)
Inputs: astdiff, strings, module sources
