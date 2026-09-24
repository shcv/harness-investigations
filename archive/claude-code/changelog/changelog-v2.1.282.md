# Changelog for version 2.1.282

## Summary

Version 2.1.282 adds configurable response wrapping and gateway load testing, strengthens managed-settings enforcement, and improves plugin removal and connection recovery. It also ships gated infrastructure for resume-cost warnings, selectable web-search modes, and clearer namespaces for synced skills.

Changes below compare 2.1.281 with 2.1.282, with substantive additions checked against the original Bun module sources.

## New Features


### Claude Apps Gateway Load Testing

What: Gateway administrators can exercise the gateway with simulated model responses.

Usage:

Add this block to an otherwise complete gateway YAML configuration:

```yaml
load_test_mode:
  enabled: true
  reply_tokens: 750
  reply_seconds: 9.5
```

Start the gateway with:

```bash
claude gateway --config gateway.yaml
```

Details:

- Response size and duration are configurable.
- Model requests receive canned replies; credential operations such as AWS STS calls can still reach external services.
- Startup refuses a database containing positive recorded spend. Use a separate test database.
- The optional `x-load-test-user` request header simulates distinct developer identities using a number of up to seven digits.
- Replies explicitly identify load-test mode.

Evidence: Gateway configuration, startup checks, and response substitution—search for `"load_test_mode"`, `"reply_tokens"`, and `"x-load-test-user"`.

## Improvements


### Configurable Response Width

Set `maxProseWidth` to make responses easier to read in wide terminals.

Usage:

Add to `~/.claude/settings.json`:

```json
{
  "maxProseWidth": 100
}
```

Paragraphs, headings, lists, and blockquotes wrap at the configured width. Tables and code blocks retain the full available width, and the underlying response text is unchanged. The minimum is 40 columns; leaving the setting unset preserves full-width rendering.

Evidence: Settings validation and Markdown rendering both consume `"maxProseWidth"`; search for `"Maximum width, in terminal columns"`.


### Administrator-Controlled Chrome Access Alongside Managed MCP

Administrators can now permit the built-in Claude in Chrome integration while retaining a `managed-mcp.json` configuration.

Usage:

Add to device-managed settings:

```json
{
  "allowClaudeInChromeWithManagedMcp": true
}
```

Then launch normally with:

```bash
claude --chrome
```

The option defaults off and is honored from device policy, including MDM, the managed-settings file, or its configured policy helper. It does not override `deniedMcpServers` or the organization’s Chrome restriction.

Evidence: The new setting is checked by Chrome’s managed-MCP admission path—search for `"allowClaudeInChromeWithManagedMcp"`.


### Managed Permission Rules Also Cover Skill Frontmatter

The existing `allowManagedPermissionRulesOnly` policy now ignores `allowed-tools` grants from user, project, and `--add-dir` skills and custom commands. This also covers plugins adopted from `.claude-plugin` manifests inside those skill directories.

Managed and bundled skills, and other plugins, retain their grants. Deny rules—including skill `disallowed-tools`—continue to apply. Affected users receive an explanation that administrators must supply the required managed permission rules.

Evidence: The expanded policy description and grant filtering—search for `"allowManagedPermissionRulesOnly"` and `"allowed-tools ignored this session"`.


### More Defensive Handling of Invalid Managed Settings

Invalid managed policy now receives more explicit, setting-specific treatment instead of silently losing its intended restriction.

Examples include:

- An invalid `strictPluginOnlyCustomization` value locks all four customization surfaces.
- Invalid `strictKnownMarketplaces` or `allowedMcpServers` values enforce empty allowlists.
- Invalid `enabledPlugins` entries are reported individually, while valid entries can still apply.
- Unreadable WSL inheritance policy receives explicit restrictive handling.
- A remote payload containing no applicable settings preserves previously accepted policy when available.

These are changes to existing policy handling, not newly introduced policy settings.

Evidence: Search for `"strictPluginOnlyCustomization"`, `"enforcing an empty allowlist"`, `"wslInheritsWindowsSettings"`, and `"ruled_empty_kept_previous"`.


### Repository Telemetry Settings Are Restricted and Explained

Project settings can no longer freely configure telemetry destinations or enable content collection. Recognized opt-out values remain supported, subject to higher-priority configuration—for example, setting an exporter to `none` or a content-collection variable to `0`.

Run `/status` to see which repository variables were ignored and which disabled telemetry. Intentional telemetry configuration should live in the shell, user settings, managed settings, or an appropriate `--settings` file.

Evidence: Environment filtering and status diagnostics—search for `"Claude Code ignores these telemetry variables"` and `"turns telemetry off with these variables"`.


### Sandbox Exclusions Respect Restrictive Policy

When managed settings or `--settings` prohibit unsandboxed commands, or managed policy restricts network domains, repository-level `sandbox.excludedCommands` entries no longer supply exclusions. Only trusted settings tiers contribute them.

The exclusion workflow also explains when no writable, permitted settings source is available.

Evidence: Search for `"excludedCommands restricted to trusted settings tiers"` and `"When managed settings or a --settings file set allowUnsandboxedCommands: false"`.


### Safer Plugin Removal

Plugin uninstall now checks that the relevant settings actually stopped enabling the plugin before reporting success.

If a settings file is unreadable, unsuitable for local editing, or still enables the plugin after a failed save, removal stops with a specific explanation. Messages also distinguish settings in other folders or managed sources, and explain when saved options or credentials remain because the plugin may still be installed elsewhere.

Evidence: Search for `"was not uninstalled:"`, `"It is still installed"`, and `"What"` alongside `"saved was kept"` in the plugin-removal implementation.


### Clearer Marketplace and Permission-Rule Diagnostics

Marketplace loading provides explicit refusal messages for names resembling official Anthropic marketplaces, including guidance that reloading will not resolve the naming conflict.

Bash permission validation now explains the actual interpretation of mixed wildcard syntax. In particular, a non-trailing `:*` is described as wildcard matching with a literal colon; moving it can change which commands match.

Evidence: Search for `"Marketplace name refused by the look-alike check"`, `"It already matches as a * wildcard"`, and `"matches only commands containing a literal *"`.


### GitHub App Setup Can Stop Between Steps

The `/install-github-app` wizard now supports cancellation during setup. It finishes the step already in progress, stops subsequent work, and reports what was already completed.

It also explicitly checks for an existing `ANTHROPIC_API_KEY` secret.

Evidence: Search for `"Stopping after the step in progress…"`, `"Installation cancelled by user. Already done in"`, and `"Checking for an existing ANTHROPIC_API_KEY secret"`.


### Gateway Readiness Grace Period

Gateway administrators can prevent brief PostgreSQL interruptions from immediately marking a replica unready.

Usage:

Add to the existing `store` block:

```yaml
store:
  readiness_grace_seconds: 30
```

The setting accepts 0–3600 seconds and defaults to 0. After the grace period expires, `/readyz` returns an unavailable response. This controls readiness reporting; it does not restore database-backed operations or change the configured spend-enforcement policy.

Evidence: Search for `"readiness_grace_seconds"` and `"Postgres is answering again"`.


### Additional Request Controls

Two environment variables extend existing request behavior:

```bash
CLAUDE_CODE_DISABLE_REFUSAL_RETRY=1 claude
```

Disables the existing refusal-retry path.

```bash
CLAUDE_CODE_GZIP_REQUEST_BODY_LEVEL=1 claude
```

Selects compression level 1–9 when request-body compression is otherwise enabled and applicable. This setting alone does not enable compression.

Evidence: Search for `"CLAUDE_CODE_DISABLE_REFUSAL_RETRY"` and `"CLAUDE_CODE_GZIP_REQUEST_BODY_LEVEL"`.


### More Useful Transcript and Disk-Space Errors

Transcript loading now reports skipped malformed JSON lines and supplies a targeted explanation for Windows `EBADF` failures after a transcript file opened successfully.

Command-output diagnostics additionally distinguish disk-quota exhaustion from filesystem exhaustion. They explain that output was lost and suggest restarting with `CLAUDE_CODE_TMPDIR` on another filesystem.

Evidence: Search for `"transcript load: skipped"`, `"loadTranscriptFile: transcript read failed with EBADF"`, and `"Your disk quota is full"`.

## Bug Fixes

- **Recover from unreadable web-search history.** When the API cannot decrypt earlier web-search content, Claude Code removes the affected search blocks and citations from the outgoing history and retries once. Later requests retain that repair. Search for `"retry:web-search-strip"` and `"The API could not decrypt web search content"`.

- **Reconnect slow-starting MCP servers after negotiation races.** If an initial discovery probe times out and legacy initialization subsequently receives an unsupported-version response, the client can try discovery again on the same process using a mutually supported modern version. Search for `"second server/discover"` and `"without restarting it"`.

- **Recover OAuth locks left by terminated processes.** Refresh-lock ownership records allow takeover when the recorded process is demonstrably gone and the lock still matches. Ambiguous ownership does not permit takeover. The recovery gate defaults on. Search for `".oauth_refresh.lock.owner"` and `"tengu_quiet_marten"`.

- **Protect hard-linked settings during proposal acceptance.** The settings-review write fallback now refuses an in-place rewrite of a hard-linked file, preventing that fallback from changing its other filesystem names. This is a targeted settings-write protection, not a universal prohibition on editing hard links. Search for `"refuseHardLinkedInPlace"` and `"HardLinkWriteRefusedError"`.

- **Keep MCP resource metadata out of the CLI’s reserved namespace.** Returned content metadata now excludes keys under `com.anthropic/`, while retaining ordinary server metadata such as MCP Apps CSP and permissions. Search for `"minus keys under the CLI-reserved"`.

## In Development

These additions have implementation in the package but depend on rollout configuration or execution surfaces unavailable in this external CLI build.


### Resume Usage-Cost Warning [In Development]

What: Warn before resuming a conversation whose context is estimated to consume a meaningful share of the five-hour usage allowance.

Status: Feature-flagged — **[Gradual Rollout]**.

Details:

- The dialog offers “Resume” or “Start a new conversation.”
- It estimates usage from context size, model, and account rate-limit tier.
- The default threshold is 5%, but the feature requires server-provided credit tables.
- It checks whether context is cold or the model changed; this is not an unconditional warning on every resume.
- Choosing a new conversation invokes `/clear`.

Evidence: Search for `"Resume this conversation?"`, `"percentOfFiveHourLimit"`, and `"tengu_amber_tally"`. Without valid rollout configuration, the warning is not shown.


### Standard and Extended Web Search [In Development]

What: Let Claude choose a quicker standard search or a more extensive search.

Status: Feature-flagged — **[Gradual Rollout]**.

Details:

- The gated WebSearch schema adds `mode: "standard" | "extended"`.
- Instructions recommend standard searches for straightforward questions and extended searches when results are inadequate or the task calls for more investigation.
- The schema preserves `extended` when the argument is omitted.
- Availability is restricted to supported first-party routing, with an additional condition for the cloud proxy.
- This is a tool argument, not a new slash command.

Evidence: Search for `"tengu_sleepy_shore"`, `"CLAUDE_CODE_WEB_SEARCH_FAST_ARG"`, and `"Use \"standard\" by default"`.


### Separate Namespaces for Account and Anthropic Skills [In Development]

What: Distinguish skills synced from a user’s claude.ai account from skills published by Anthropic.

Status: Feature-flagged — **[Gradual Rollout]**.

Details:

- Account skills can receive the `claude-ai:<name>` namespace.
- Anthropic-published skills retain `anthropic-skills:<name>`.
- Collision checks, former-name suggestions, and forked-skill resume handling account for the distinction.
- Synced skills already existed in 2.1.281; this changes their naming and resolution.

Evidence: Search for `"claude-ai:"`, `"syncedSkillClass"`, and `"tengu_copper_heron"`. The namespace switch defaults off.


### Attached-Folder Sync and Expanded Worktree Handling [In Development]

What: Extend cloud file-sync infrastructure to prepare an attached local checkout for synchronization with an existing cloud session.

Status: Dark-launched / feature-flagged.

Details:

- A new consent flow explains two-way synchronization and remembers the folder’s choice.
- Eligibility checks diagnose mismatched repositories, branches, detached HEAD, incompatible history, and sessions already syncing elsewhere.
- Worktree handling gains private Git-directory preparation and additional checks for replaced directories, mounts, links, and invalid stored objects.
- Windows and WSL linked-worktree layouts remain explicitly unsupported.
- The attachment-sync gate defaults off, and the remote-tool-serving eligibility function in this external build returns `"external_build"`.

Evidence: Search for `"Keep this folder in sync with the cloud session?"`, `"tengu_violin_soundpost"`, `"File sync's private git directory"`, and `"external_build"`.


### Expanded Shared-Artifact Reads [In Development]

What: Allow eligible shared artifacts to return fuller content rather than only a summary.

Status: Feature-flagged — **[Gradual Rollout]**.

Details:

- A new gate enables an additional shared-content read path for eligible non-owner access.
- Ownership, organization boundaries, and consent still constrain access.
- Notification-triggered page-data reads gain explicit one-read confirmation handling outside automatically allowed channels.
- Artifact content containing raw terminal control bytes is withheld from inline output; the implementation attempts to preserve the complete content in a file instead.

Evidence: Search for `"tengu_cobalt_plinth_mallow"`, `"Notification-triggered page-data read requires confirmation"`, and `"contains raw terminal control bytes"`. The expanded shared-read gate defaults off.

## Notes

- Review repository telemetry settings after upgrading: configuration that is now ignored should move to an appropriate trusted source.
- Organizations using `allowManagedPermissionRulesOnly` may need to add managed grants for workflows that previously relied on skill `allowed-tools`.
- Correct malformed managed policy rather than relying on it being ignored; several invalid restrictions now receive restrictive fallback values.
- No official 2.1.282 release notes were supplied. The embedded changelog starts at 2.1.281, so its entries are not presented as highlights of this release.


Generated with:
- tool: `harness-investigations@4b208e0-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.282.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.282.txt`
- source modules: `archive/claude-code/original/cli-v2.1.282.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
