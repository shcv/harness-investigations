# Changelog for version 2.1.271

## Summary

Compared with 2.1.270, this release adds command-specific approval for plugin installation, a gated plugin test runner, and disk-backed configuration snapshots for self-hosted runners. It extends custom-agent configuration, improves workflow recovery at usage limits, and strengthens artifact overwrite protection. Several additional capabilities remain gated, including artifact quickstart and expanded recovery of interrupted thinking.


## New Features


### Command-Specific Approval for Plugin Installation

What: Plugin installation and updates can accept a previously displayed marketplace command by its SHA-256 identifier.

Usage:
```bash
claude plugin install example@marketplace --json
claude plugin install example@marketplace --accept-command <shownCommand.sha256>
```

Details:

- The new `--accept-command` option applies to both `plugin install` and `plugin update`.
- Approval is bound to the command, plugin, and marketplace catalog. Changes invalidate the approval.
- It covers command-source installations and archive downloads that use a `headersHelper`.
- Like `--yes`, it cannot provide unattended approval from inside a Claude Code session.

Evidence: Install/update option definitions and command-matching checks — search for `"--accept-command <sha256>"` and `"shownCommand.sha256"`. Neither appears in 2.1.270.


### Function-Hooks Plugin Test Runner [Gradual Rollout]

What: Plugin authors can run tests against an environment resembling the one their function hooks use.

Usage:
```bash
claude plugin test ./my-plugin
```

Details:

- Discovers `*.test.ts` and `*.test.tsx` beneath the supplied directory, defaulting to the current directory.
- Test files import the testing utilities from `claude-code/testing`.
- Each file runs in a child process; test failures produce exit status 1.
- Requires the existing function-hooks rollout or its explicit environment override. Managed hook restrictions still apply.

Evidence: New CLI dispatch and test-runner help — search for `"Usage: claude plugin test [dir]"`, `"claude-code/testing"`, and `"tengu_plugin_hooks_modules"`. The test command is absent from 2.1.270.


### Disk-Backed Runner Configuration Snapshots

What: Self-hosted runners can keep their startup configuration snapshot on disk instead of retaining the entire snapshot in memory.

Usage: Add this option to the existing runner invocation:
```text
--host-config-snapshot disk
```

Details:

- `disk` is the new default; `memory` remains available through the same option.
- Disk snapshots live beneath `--base-dir` and are checked against an in-memory manifest before seeding sessions.
- A modified snapshot causes session startup to fail and requires restarting the runner.
- Memory mode retains the 64 MiB total limit.
- Sessions now receive explicit warnings when host configuration could not be applied or was only partially applied.

Evidence: Runner parser, snapshot implementation, and help — search for `"--host-config-snapshot"`, `"SELF_HOSTED_RUNNER_HOST_CONFIG_SNAPSHOT"`, and `"Host config snapshot was modified after runner startup"`.


## Improvements


### Custom Agents Can Omit Ordinary CLAUDE.md Instructions

Custom-agent definitions now accept `omitClaudeMd: true`. This extends behavior previously used by built-in agents to user-defined and plugin agents.

Usage: Add this field to an agent’s frontmatter:
```yaml
omitClaudeMd: true
```

The agent receives its delegation prompt without the usual user, project, and local CLAUDE.md instructions. Managed instructions remain protected; the implementation preserves the original context if it cannot safely resolve the managed-only replacement. This setting does not change the main session’s instructions.

Evidence: Agent schemas, frontmatter loaders, and subagent context construction — search for `"omitClaudeMd"` and `"Run this agent without the user, project and local CLAUDE.md instruction files"`.


### Grant-Based Usage Resets [Gradual Rollout]

The existing `/limit-reset` command gains a second reset mechanism based on account-provided grants.

Usage:
```text
/limit-reset
```

The new flow shows remaining resets, expiry dates, and the limits a grant covers. It asks for confirmation, supports grants permitting use before exhaustion, and distinguishes successful, expired, already-used, and uncertain outcomes. Confirmation text explains that the weekly reset day stays unchanged.

This does not make resets universally available: the new path requires an enabled rollout and an eligible account grant.

Evidence: Existing command extended with grant selection and confirmation — search for `"tengu_cedar_ember"`, `"Use your reset?"`, and `"Your reset doesn't cover this limit"`.


### Smaller Workflow Guidelines

The `medium` workflow guideline now targets fewer than 10 agents, down from fewer than 15. Pro plans default to `small`; other plans retain the `medium` default.

Users can choose a size through “Dynamic workflow size” in `/config`, or set `workflowSizeGuideline` in settings. These remain advisory instructions, not enforced agent-count limits.

Evidence: Updated settings description and size mapping — search for `"workflowSizeGuideline"` and `"Unset defaults to \"medium\", or \"small\" on Pro plans"`.


### Workflows Can Wait Through Usage Limits

Workflow agents that qualify for automatic continuation can now wait for the usage-limit reset and rerun afterward. The workflow reports how many agents are waiting and announces their restart.

The behavior respects the existing `autoContinueAtUsageLimit` choice. Turning waiting off prevents the parked agents from running again.

Evidence: New workflow waiting and restart paths — search for `"Workflow paused; waiting agents re-run shortly after the reset"`, `"Usage limit reset. Re-running"`, and `"tengu_linked_clover"`.


### Plugin Configuration Pickers

Plugins can declare a fixed `options` list for a string configuration field. `/config` presents the field as a picker, and stored values outside the declared choices count as unset.

Options cannot be empty or duplicated ignoring case. The field must be a non-sensitive, single-value string, with either a valid default or `required: true`.

Evidence: Plugin configuration schema and validation — search for `"For string type: the only values the field takes"` and `"options cannot repeat a value"`.


### Shared Type Contracts for Plugins

The existing `/plugin-types` command now includes enabled plugins’ own TypeScript contracts.

Usage:
```text
/plugin-types
```

A plugin can declare a relative `.d.ts` path in its manifest’s `types` field. Claude Code validates the contract, copies accepted declarations into its generated types directory, and indexes them in `claude-code-plugins.d.ts`. Dependent plugins can then type-check the capabilities another plugin adds.

Contracts must remain inside the plugin directory and contain self-contained declarations rather than executable code or external imports.

Evidence: Manifest validation and declaration generation — search for `"claude-code-plugins.d.ts"` and `"types must name a TypeScript declaration file ending in '.d.ts'"`.


### More Controls for Plugin Terminal Interfaces

Function-hook interfaces gain additional rendering and interaction capabilities, including raster elements, autofocus on input controls, and actions for cycling between plugin panes.

The new pane actions are `pane:next` and `pane:previous`. These additions apply where the existing plugin UI infrastructure is enabled; they do not establish that function hooks are available to every account.

Evidence: Element validation and active keybinding handlers — search for `"Raster props must be"`, `"autoFocus"`, `"pane:next"`, and `"pane:previous"`.


### Read Multiple Artifact Files Together

Where multi-file artifacts are available, Claude can now request several published files in one read using `paths` instead of a single `path`.

The result identifies where each file was saved or why it could not be read. Small text files are included inline while they fit. Existing read permissions, destination checks, and per-call limits still apply.

Evidence: Artifact read schemas and batch handling — search for `"read_file: several published paths"` and `"Reads several published files from an artifact"`.


### Stronger Protection Against Artifact Overwrites

Updates to existing multi-file artifacts now track what Claude has read, listed, or published during the session.

A publish can refuse to replace or remove files that Claude has not inspected, or files that changed after inspection. The refusal identifies affected paths so Claude can reread and reconcile them before retrying.

An explicit `overwrite_unread` list supports user-requested replacement without inspection where permitted. It does not override changes made after a file was read.

Evidence: Default-enabled path tracking and publish checks — search for `"CLAUDE_CODE_ARTIFACT_PATH_PIN"`, `"overwrite_unread"`, and `"Nothing was published or removed: this publish touches files"`.


### Updated Artifact Watch Behavior

Artifact watch handling now recognizes background main-loop sessions as capable of holding live watches. Cloud sessions describe their watches as durable wake subscriptions rather than live local connections.

Subagents, teammates, and print sessions still have restrictions, and tool responses explain when automatic notifications or replies are unavailable.

Evidence: Updated watch eligibility and tool guidance — search for `"only a main-loop session"` and `"a watch is a durable wake subscription"` in both versions.


### Pricing Multipliers Can Include Markups

`modelPricing.multiplier` now accepts values greater than zero through 10. Previously, values above 1 were rejected.

For example:
```json
{
  "modelPricing": {
    "multiplier": 1.2
  }
}
```

This permits accounting for provider or gateway markups. The accompanying guidance notes that spend caps using multiplied prices are reached sooner.

Evidence: Updated numeric validation and configuration warnings — search for `"modelPricing.multiplier"` and `"greater than 0 and at most 10"`.


### Server Classification Fallback for Third-Party Providers

Eligible third-party-provider Auto mode sessions gain a server-classification path with local fallback. When the deployment rejects the relevant beta, Claude Code retries without it and uses local classification for the remainder of the session.

`CLAUDE_CODE_AUTO_MODE_SERVER` controls the new third-party path, alongside the existing provider and Auto mode eligibility checks.

Evidence: Provider-specific classifier selection and retry handling — search for `"CLAUDE_CODE_AUTO_MODE_SERVER"` and `"auto mode decides with the local classifier"`.


### Better Handling of Inline Skill Commands in Auto Mode

When an inline skill command needs approval or is deferred by automatic classification, eligible Auto mode skill loads can hand that command to the model as an explicit first step instead of immediately failing skill expansion.

The command then runs through the normal tool path. This does not bypass a permission denial.

Evidence: Inline-command permission handling and handoff instructions — search for `"tengu_iterative_falcon"`, `"promptShellHandOff"`, and `"run this first, exactly as written, and use its output"`.


### Host-Drain Reporting for Runner Operators

The new `--drain-marker-file <path>` option lets operators identify shutdowns caused by their hosting system. A regular marker file can also supply the host’s force-delete deadline on its first line as Unix seconds.

This option changes shutdown reporting only; it does not change draining behavior.

Evidence: Runner option parser and explicit help text — search for `"--drain-marker-file"` and `"Telemetry only — the drain itself behaves exactly as without the flag"`.


## Bug Fixes

- Settings reloads now fall back to polling when native file watching fails to deliver events, including watcher resource-limit failures. Search for `"native file watching is not delivering events"` and `"fs_watch_refused_late_"`.

- Tip selection now checks whether an advertised command is enabled and available in the current surface before showing the tip. This reduces suggestions for unusable commands, including in remote sessions. Search for `"tip advertisedCommand check threw"` and `"advertisedCommand"`.

- Enterprise MCP configuration more consistently retains exclusive control over servers, including dynamically supplied servers. Unreadable or malformed managed configuration produces clearer restrictions and recovery guidance. Search for `"managed-mcp.json) keeps exclusive control over MCP servers"`.

- Permission-answer validation rejects unapproved changes to the requested tool input and checks tool-specific card answers against the fields originally shown. Search for `"The permission answer changed the tool call"` and `"card-answer admitter changed a field the card showed"`.

- Artifact actions can no longer reuse a server-classifier approval after relevant sharing, ownership, or watch facts change. Search for `"Classifier verdict out of date - blocking for a retry"` and `"changed since the request was built; the server's allow is void"`.

- Shell permission analysis now accounts for zsh assignment flags that truncate, pad, or change case, rather than treating their values as unchanged literals. Read restrictions also reject additional subshell and multiple-directory-change cases that cannot be checked safely. Search for `"width-truncates"`, `"case-converts"`, and `"a subshell cannot be checked against the read block"`.

- Worktree cleanup adds checks for malformed Git metadata, links, unexpected ownership, and paths resolving to the main worktree before pruning or removal. Search for `"Refused git worktree prune entry"` and `"resolves to the main worktree"`.

- Truncated side-question answers now receive an explicit retry notice and are omitted from subsequent side-question history instead of being treated as complete answers. Search for `"This answer was cut off before it finished"` and `"That answer was cut off before it finished, so it is omitted here"`.

- Compliance-aware credential handling now withholds the CLI’s Anthropic credentials from child processes and configuration-variable expansion when the HIPAA policy applies. Search for `"HIPAA: withholding this CLI's Anthropic credentials"`.


## In Development

These additions have gated or host-dependent execution paths. Their presence in the CLI does not establish account availability or a release date.


### Artifact Quickstart [In Development]

What: A read-only first step helps Claude choose an artifact type and discover an appropriate design system before creating content.

Status: Feature-flagged; defaults off.

Details:

- Accepts an intent of `document`, `slides`, `design`, or `other`.
- Can list design systems and attach the default system’s README.
- Supports `design_systems: false` when discovery is unnecessary.
- Does not itself create or publish an artifact.
- Availability also depends on the session’s artifact capabilities.

Evidence: Quickstart schema, handlers, and gate — search for `"tengu_cobalt_plinth_woad"`, `"CLAUDE_CODE_ARTIFACT_QUICKSTART"`, and `"quickstart only (required)"`.


### Immediate Handling of Rapid Follow-Up Messages [In Development]

What: A supported host can let a quick follow-up supersede a running turn that has not shown output yet.

Status: Feature-flagged and requires explicit host capability negotiation.

Details:

- The CLI emits a `turn_preempted` event and runs the follow-up next.
- Running shell commands are backgrounded rather than killed.
- The host must declare `rapidFollowupPreempt`.
- Remote Control bridge messages do not trigger this behavior.
- Without the capability and rollout flag, messages retain their previous queuing behavior.

Evidence: Follow-up preemption controller and event contract — search for `"tengu_zippy_spindle"`, `"rapidFollowupPreempt"`, and `"turn_preempted"`.


### Expanded Thinking Resumption [In Development]

What: The existing experimental thinking-recovery mechanism gains server-supported resumption of eligible truncated responses.

Status: Feature-flagged.

Details:

- Adds the `thinking-resumption-2026-07-17` beta.
- Requires the server to identify the response as resumable and checks remaining context capacity.
- Displays “picking the thought back up” during recovery.
- Falls back when the server rejects resumption; beta-header rejection disables that path for the process.

Evidence: Compare the existing recovery gate with the new header and response checks — search for `"tengu_thinking_block_resumption"`, `"thinking-resumption-2026-07-17"`, and `"picking the thought back up"`.


### Large-PDF Protection When Page Counting Fails [In Development]

What: Claude Code can request explicit page ranges for a large PDF whose page count could not be determined.

Status: Feature-flagged; the size threshold defaults to zero, disabling this additional guard.

Details:

- Distinguishes missing, timed-out, unsuccessful, and incomplete `pdfinfo` results.
- Applies the additional guard only when its configured size threshold is exceeded and page extraction is available.
- Directs Claude to use a range such as `pages: "1-5"`.

Evidence: PDF metadata handling and gated size check — search for `"tengu_immutable_tide"` and `"This PDF's page count is unknown"`.


### Managed-Cloud Turn Handoff Infrastructure [In Development]

What: A compatible client can transfer an already-started turn to a managed cloud worker, including pending tool calls.

Status: Host-dependent infrastructure; admitted for qualifying managed cloud workers, not exposed as a general terminal command.

Details:

- Validates message identities, conversation order, pending calls, and duplicate delivery before execution.
- Supports recording a stopped turn without running its pending calls.
- Requires a client that uses the new handoff protocol.
- Workers can disable it with `CLAUDE_CODE_DISABLE_TURN_HANDOFF`.

Evidence: Worker admission, handoff validation, and dispatch — search for `"turn_handoff"`, `"turn_handoff_available"`, and `"CLAUDE_CODE_DISABLE_TURN_HANDOFF"`.


## Notes

Artifact automation may now need to reread published files before replacing them. Older clients may also reject or misreport pricing multipliers above 1; the new configuration guidance specifically warns about clients older than 2.1.270.

This changelog compares the 2.1.270 and 2.1.271 analysis snapshots, with substantive additions checked against the original split-module sources. Availability labels describe source gates, not a verified live account rollout.


Generated with:
- tool: `harness-investigations@bcd9fc0-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.271.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.271.txt`
- source modules: `archive/claude-code/original/cli-v2.1.271.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
