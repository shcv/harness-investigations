# Changelog for version 2.1.290

## Summary

Version 2.1.290 adds a per-run opt-in for cloud sessions to use local tools, controls for idle compaction, and broader sharing of local instructions and settings with cloud sessions. It also improves background-session lookup, reading long web pages, and recovery from interrupted MCP calls, while tightening worktree cleanup, browser activation, and permission handling.

## New Features


### Per-Run Permission for Cloud Sessions to Use Local Tools [Gradual Rollout]

What: Remote Control gains an explicit option to let cloud sessions use the current folder, including unattended commands when the required sandbox and permission conditions are met.

Usage:

```bash
claude remote-control --allow-unattended-tool-calls
```

Details:

- The permission applies while this Remote Control run remains active.
- Auto-mode commands can run without asking only inside the sandbox; select a sandbox mode with `/sandbox` first.
- Deny rules and hooks continue to apply.
- Start the command yourself in an interactive terminal. Scripts, pipes, and launches from a Claude Code child session are rejected.
- The flag cannot be combined with `--spawn=session`, `--session-id`, or `--continue`.
- Account rollout, organizational policy, platform support, and local settings can still prevent serving. If tool hosting fails, Remote Control can continue without it.

Evidence: The new argument parser, terminal checks, and process-bound grant handling contain `"--allow-unattended-tool-calls"`, `"unattended-serving-runs"`, and `"Cloud sessions cannot use this folder: --allow-unattended-tool-calls could not start"`. Foreground hosting checks `tengu_violin_luthier`.


### Controls for Idle Compaction

What: A new setting lets you disable compaction while a session is idle without disabling ordinary automatic compaction.

Usage: Add this setting to your Claude Code settings file:

```json
{
  "idleCompaction": false
}
```

Details:

- Idle-compaction infrastructure already existed in 2.1.289; the opt-out setting is new.
- Setting `idleCompaction` to `true` does not activate the feature. Actual idle compaction remains controlled by `tengu_sunny_locket`.
- A new environment variable adjusts the minimum conversation size considered by the existing idle-compaction path:

```bash
CLAUDE_CODE_IDLE_COMPACT_MIN_TOKENS=250000 claude
```

- The implementation clamps this threshold to at least 100,000 tokens.
- Automatic compaction must also be enabled, and cache, timing, and usage-limit checks must pass.

Evidence: The new `"idleCompaction"` schema explicitly says `"Setting it to true does not turn idle compaction on"`. Threshold selection reads `"CLAUDE_CODE_IDLE_COMPACT_MIN_TOKENS"` alongside `tengu_sunny_locket`.


### Local Instructions and Settings for Cloud Sessions [Gradual Rollout]

What: Cloud-session launches can now receive a filtered package of user-level instructions, rules, output styles, settings, and portable permission rules from the local machine.

Usage:

```bash
claude --cloud
```

Details:

- This extends the existing cloud workflow; `--cloud` itself is not new.
- The package can include user-level `CLAUDE.md`, rules, output styles, and supported settings.
- Eligible Markdown imports can be folded into the package.
- Credential-like files, read-denied content, unsupported paths, and unsafe links are withheld.
- Hooks and environment configuration are not copied as part of this package.
- Permission allow rules are narrowed where necessary, including when local hooks would otherwise guard an action.
- Launch and resume messages distinguish settings that were sent, applied, withheld, or not confirmed. Settings applied after a reply can take effect on the next turn without `/clear`.
- The path requires the relevant cloud-sharing rollout gates, including `tengu_violin_wood` and `tengu_violin_strad`.

Evidence: Package construction and upload reporting contain `"Sent settings from this machine to the cloud session"`, `"hooks, env and the like are never sent"`, and `"The cloud session still ran with the settings it had for this reply"`. The implementation also reports `tengu_home_seed_upload`.

## Improvements


### Find Background Sessions by Name

`claude attach` and `claude logs` now accept session names or distinctive parts of names, reducing the need to copy short IDs.

Usage:

```bash
claude attach "dependency cleanup"
claude logs "dependency cleanup"
```

Matching considers names and task descriptions, with stronger matches preferred. Ambiguous matches ask you to use more of the name or an ID. Name-based attachment opens a running session; use its ID when reopening a stopped session. Arguments that look like ID prefixes are interpreted as IDs first.

Evidence: Command definitions now advertise `"claude attach <id|name>"`, `"claude logs <id|name>"`, and `"Part of the session name works too"`. Resolution messages include `"Use more of the name, or the id"`.


### Read Long Web Pages in Successive Parts

WebFetch gains an `offset` argument so Claude can continue through a long page instead of repeatedly fetching the same initial portion.

Usage: Ask Claude to continue reading the page from the next offset supplied by WebFetch.

Details:

- The offset is a character position in the extracted page text.
- Partial results identify their position and provide instructions for continuing.
- Results distinguish unread content from content actually processed.
- Existing URL and domain permission checks still apply.

Evidence: The new argument is described as `"Character position in the page text to start reading from"`. Continuation results contain `"to read on, call"` and `"again with the same url and offset"`.


### Replenishing Web Search Budgets

The existing WebSearch limit now supports replenishment over time, configurable through a new environment variable.

Usage:

```bash
CLAUDE_CODE_WEB_SEARCH_REFILLS_PER_HOUR=100 claude
```

Details:

- `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION` remains the capacity control.
- The new variable controls how quickly used capacity becomes available again; `0` disables replenishment.
- Searches share a budget across agents rather than giving each agent an independent allowance.
- Limit messages distinguish a headless turn’s budget from an interactive session’s budget.
- When exhausted, Claude is instructed to continue with gathered information rather than wait for replenishment.
- Without an explicit override, replenishment depends on the calling context; the implementation retains a non-replenishing mode.

Evidence: Budget accounting reads `"CLAUDE_CODE_WEB_SEARCH_REFILLS_PER_HOUR"` and `tengu_memoized_turtle`. Exhaustion messages explain `"per turn, shared by every agent in it"` and `"the budget refills at about"`.


### Review User-Level Settings Changes for Local Cloud Tools

The existing `claude apply-project-settings` review now includes relevant changes to `~/.claude/settings.json`, alongside the current folder’s settings.

Usage:

```bash
claude apply-project-settings
```

Cloud sessions continue using the accepted settings snapshot until you review and accept changes. Removing your user settings file does not silently discard that accepted snapshot.

Evidence: The command description now names `"~/.claude/settings.json"`. Snapshot reporting includes `"Your own settings file is gone; cloud sessions keep using what you accepted"`.


### More Explicit Chrome Activation and Recovery

Chrome integration now draws a clearer distinction between user consent, project configuration, and remote-session startup.

- A project’s `CLAUDE_CODE_ENABLE_CFC` setting cannot activate your signed-in browser.
- Local users can explicitly enable Chrome with `/chrome` or `--chrome`.
- Remote and Cowork sessions ignore the saved “Enabled by default” preference at startup; they require `--chrome` or the environment variable in the launching environment.
- Recovery messages distinguish a disabled MCP server, disconnected browser, incompatible sign-in method, and unavailable reconnect action.

Usage:

```bash
claude --chrome --resume
```

Evidence: Activation checks and recovery paths contain `"a project can't turn on Claude in Chrome"`, `"Ignoring \"Enabled by default\""`, and `"Open /mcp, select claude-in-chrome, and enable it"`.


### Clearer Boundaries for MCP Connector Configuration

Claude Code now explicitly rejects manually configured `claudeai-proxy` servers where that transport is reserved for claude.ai connectors.

Connect the service through claude.ai’s connector settings, or configure an ordinary HTTP MCP server with `type: "http"`. Plugin-declared proxy entries are dropped during loading.

Evidence: Configuration validation contains `"Cannot add MCP server: claudeai-proxy transport type"` and `"type \"claudeai-proxy\" is used only by claude.ai connectors"`.


### Stronger Marketplace Name Validation

Marketplace loading and refresh paths more consistently reject names that resemble Anthropic-owned marketplaces. Diagnostics now explain whether the source must be renamed or the existing registration removed.

For affected registrations, removal also removes installed plugins and their saved data, options, and secrets. Settings-defined marketplaces receive an ordered rename, removal, restart, and reinstall procedure.

Evidence: Validation and remediation messages contain `"its name looks like the name of one of Anthropic's own marketplaces"`, `"the look-alike check refuses the name it is saved under"`, and `"Rename it in its settings file"`.


### Bundled Managed Agents Quickstarts

The existing `/claude-api` skill gains named Managed Agents onboarding templates.

Usage:

```text
/claude-api managed-agents-onboard data-analyst
```

The bundled names are:

- `contract-tracker`
- `data-analyst`
- `deep-researcher`
- `field-monitor`
- `incident-commander`
- `sprint-retro-facilitator`
- `structured-extractor`
- `support-agent`
- `support-to-eng-escalator`

The skill distinguishes a named template from URL-based onboarding. Unknown template names trigger a list and clarification instead of building from a guess. This is a change to CLI-bundled guidance, not a claim about separately packaged SDK APIs.

Evidence: Routing and template registration contain `"shared/managed-agents-quickstarts/"`, `"bundled quickstart"`, and `"The word after the subcommand in the request below is not one of these names"`.


### Better Cloud Upload Diagnostics

Cloud handoff failures now distinguish problems such as unreadable Git configuration, unsupported repository extensions, a Git shim that runs no Git, and unusable session IDs.

The messages explain what stayed local and provide targeted recovery steps. An invalid session ID also warns that a cloud session may already have been created, helping avoid accidental duplicate launches.

Evidence: Diagnostics contain `"The program that runs as git on your PATH started and ran no git"`, `"unknown repository extension"`, and `"A session may have been created"`.

## Bug Fixes

- **Avoid replaying accepted MCP calls after a disconnect.** When the server has already taken a call, Claude Code no longer automatically resends it merely because the connection closed. The error explains that the outcome is unknown and recommends checking what happened before repeating the action. Search for `"MCP call not sent again after connection closed"` and `"Check what it did before you repeat it"`.

- **Detect MCP answer streams that end without an answer.** A mid-call stream closure now produces a specific failure instead of leaving the call waiting indefinitely. Search for `"MCP answer stream ended mid-call"`.

- **Respect connector opt-out for explicitly supplied proxy servers.** `disableClaudeAiConnectors: true` now blocks explicitly supplied `claudeai-proxy` connections as well as automatically fetched connectors. Search for `"a claudeai-proxy server passed explicitly"` in the setting description.

- **Prevent stale MCP connection results from replacing newer state.** Connections and refreshed tool lists are discarded when the server was removed, changed, disabled, or its name is now held elsewhere. Search for `"The connection was not kept"` and `"A re-queried tool list was not applied"`.

- **Refresh malformed plugin-directory caches.** Cached catalogs containing duplicate listing IDs, including files written by 2.1.287, are treated as outdated. Search for `"Claude Code 2.1.287 wrote such files"`.

- **Preserve delayed SessionStart hook context.** Newly loaded plugin hook output can be retained for later delivery, including across worker replacement, instead of being lost with the earlier worker. Search for `"heldContent"` and `"SessionStart hook output an earlier worker set aside"`.

- **Refuse cloud-handoff stashes that could delete replacement folders.** If a tracked file or symlink has become a directory, handoff stops before stashing and asks you to commit or move that directory. Search for `"Nothing was stashed"` and `"stashing could delete what's in it for good"`.

- **Make worktree cleanup verify ownership and registration.** Removal refuses locked worktrees, mismatched `.git` back-links, and unsafe or changing directories. Failures distinguish files left behind from registrations left behind. Search for `"the worktree is locked"`, `"the worktree's .git file is missing"`, and `"files kept appearing in the worktree while it was being deleted"`.

- **Recheck sandbox deny paths and credential masks when links change.** The running sandbox configuration can be rebuilt when those paths resolve elsewhere. If rebuilding fails, affected grants are withheld and credential masks fall back conservatively. Search for `"Sandbox configuration updated: a read-deny or credential-mask path"` and `"credential mask(s) are reduced to a whole-file placeholder"`.

- **Do not approve a shell command merely because its redirect-free form is allowed.** Permission handling now distinguishes the command as written from the version with output redirection removed. Additional heredoc and declaration checks catch shell constructs that cannot be safely analyzed. Search for `"not allowed as written"` and `"Text after the heredoc start on the same line cannot be statically analyzed"`.

- **Recover from certain model refusals involving images and documents.** Claude Code can progressively remove the oldest media from the model request and retry, retaining a successful lower limit for the conversation. Retries are bounded and stop when further removal would not help. Search for `"retry:media-item-limit:"` and `"images and documents; the oldest were removed"`.

- **Retry streaming responses filtered before any answer was shown.** A bounded retry path handles output filtering before visible answer text, rather than immediately ending the request. The control defaults on and can be disabled remotely. Search for `"Output content filter stopped the response before any of the answer was shown"` and `tengu_eager_rain`.

- **Restore plan mode on interactive resume.** A session can recover an unexited plan state from its stored mode or transcript. Explicit startup mode choices and forks are respected. Search for `"[planModeResume] re-entering plan mode on resume"`.

- **Report timers lost to container restart.** Recovery now tells Claude which pending timers cannot fire and instructs it to reschedule still-needed work or perform overdue work. Search for `"Every timer listed here is gone and will not fire"`.

- **Keep account-memory content out of Remote Control forwarding.** Sensitive account-memory context and related results can remain visible in the terminal while forwarded messages receive placeholders. Search for `"[account memory withheld from Remote Control; shown in the terminal session]"`.

- **Honor disabled project settings when loading project skills.** Project skill directories are suppressed when the process does not load the project settings source. Search for `"project skill directories on disk were not loaded"`.

- **Improve WSL drive discovery for local cloud tools.** The serving path uses `/proc/self/mountinfo` and validates drive entries before offering local access. Search for `"Windows drives in /proc/self/mountinfo"`.

- **Do not let hooks preapprove hosted desktop actions.** Desktop tools in the hosted-desktop path remain subject to their required review. Search for `"hooks cannot approve a hosted session's desktop tools"`.

- **Handle unexpected extra tool arguments more tolerantly during permission checking.** Eligible tools can have unrecognized schema keys set aside and the remaining input reparsed; tools declaring a fail-closed posture retain it. Search for `"keysSetAside"` and `tengu_tidy_eclipse`.

## In Development

These additions expose experimental or restricted paths. Their presence in the CLI does not establish availability for every account or client.


### Proactivity Levels [In Development]

What: Let users choose how much initiative Claude takes through `ask`, `default`, and `proactive` levels.

Status: Experimental; hidden terminal option with working opt-in paths and incomplete presentation hooks.

Details:

- The parser now accepts `--proactivity <level>`.
- An explicit level can activate the local path when the gate permits it.
- Compatible hosts can opt in with `proactivity: true` and use `set_proactivity_level`.
- Level changes supply initiative instructions and select among available permission modes.
- Existing permission restrictions and plan-mode rules still matter.
- The terminal option remains hidden from help: its visibility helper returns false.
- Presentation and persistence helpers remain stubbed.
- Cloud-hosted forwarding explicitly rejects `set_proactivity_level`.

Experimental usage:

```bash
claude --proactivity ask
```

Evidence: Search for `"--proactivity <level>"`, `"set_proactivity_level"`, and `tengu_proactivity_selector`. The source also contains `"set_proactivity_level is not available in a cloud-hosted session yet"`.


### In-Task Chrome Setup Offers [In Development]

What: Offer Chrome setup during a task that needs the user’s signed-in browser after a Chrome tool reports that the extension is disconnected.

Status: Feature-flagged and restricted to compatible clients.

Details:

- The new `OfferChromeSetup` tool requests a setup card and waits for the user’s response.
- The host must declare `rendersChromeSetupOffer`.
- `tengu_brass_kite` must be enabled.
- A disconnected-extension result must already have been observed.
- The intended outcomes are `connected` and `not_now`.
- Instructions limit offers to tasks needing the user’s accounts or tabs and discourage repeating an offer after dismissal.
- This does not make Chrome setup universally available in the terminal.

Evidence: Search for `"OfferChromeSetup"`, `"rendersChromeSetupOffer"`, `"Set up Claude in Chrome?"`, and `tengu_brass_kite`.


### Quiet Background Command Check-Ins [In Development]

What: Prompt Claude to investigate a background command that has produced no new output for a configured interval.

Status: Feature-flagged; disabled by the default interval of zero.

Details:

- The implementation monitors output growth and queues check-in messages.
- A check-in asks Claude to distinguish a quiet command from one waiting on input, a lock, or a stalled process.
- It does not declare the command finished or automatically kill it.
- Sleep and suspend gaps are accounted for when measuring silence.
- No public CLI control is added for this experiment.

Evidence: Search for `tengu_silent_heron`, `"shell-checkin"`, and `"This is a check-in, not a completion"`.


### Background Foreground Agents for Human Follow-Ups [In Development]

What: Let an eligible queued human message reach the main session while foreground subagents continue in the background.

Status: Feature-flagged.

Details:

- The implementation identifies eligible waiting messages and moves foreground subagent tasks to background execution.
- This can improve responsiveness during delegation.
- Availability depends on the host path and experiment gate; it is not a universal interruption policy.

Evidence: Search for `tengu_valiant_crescent` and `"foreground subagents to the background for a person's queued message"`.


### PDF References for Smaller Documents [In Development]

What: Extend reference-based handling to eligible PDFs that would otherwise be attached in full, allowing Claude to choose when to read them.

Status: Feature-flagged; defaults off.

Details:

- Large-PDF reference handling already existed.
- The new experiment can also produce references for smaller PDFs when page-count information is available.
- Eligible references can indicate that the document remains readable in full.
- Existing size limits and model compatibility checks remain in place.

Evidence: Search for `tengu_twinkly_beacon`, `"pdf_reference"`, and `"readableWhole"`.


### Subagent Budgets That Exclude Starting Context [In Development]

What: Allow selected subagent budgets to count work after launch without charging the inherited starting context against that budget.

Status: Experimental; inactive under the default `none` variant.

Details:

- The `forks` variant applies this accounting to forked agents.
- The `all` variant applies it more broadly.
- A separate experiment supplies explanatory budget instructions to the parent agent.
- This changes agent budget accounting, not billing for the underlying model requests.
- Optional effort-selection logic can also adjust inherited subagent effort.

Evidence: Search for `tengu_calm_mochi`, `"isBudgetOnTopOfStart"`, `tengu_streamed_bumblebee`, and `"The budget does not count the context the agent starts with"`.

## Notes

This changelog compares **2.1.289 → 2.1.290**. Substantive changes were checked against both version snapshots and the original split-module sources; rebundling wrappers, renamed identifiers, and module ordering are excluded.

For affected integrations:

- Replace manually declared `claudeai-proxy` servers with HTTP configuration or connect them through claude.ai.
- Move Chrome activation out of project settings and enable it explicitly as the user.
- Review user-level settings changes with `claude apply-project-settings` before expecting local cloud-tool sessions to use them.
- Inspect an interrupted MCP action’s effects before repeating it when its outcome is unknown.


Generated with:
- tool: `harness-investigations@24c3378-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.290.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.290.txt`
- source modules: `archive/claude-code/original/cli-v2.1.290.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
