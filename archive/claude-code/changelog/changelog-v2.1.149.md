# Changelog for version 2.1.149

## Summary
Claude Code 2.1.149 adds opt-in infrastructure for syncing organization skills into the local skill system, improves usage analysis so MCP servers are included alongside skills, subagents, and plugins, and hardens several edge cases around Bash execution, image/PDF reads, gitignore writes, and telemetry configuration. It also ships disabled wellbeing UI/settings scaffolding for future break reminders and quiet-hours nudges.

### Opt-in Organization Skill Sync
What: Claude Code can now sync skills from an authenticated organization endpoint into the local skills directory when the new sync path is enabled.

Usage:
```bash
CLAUDE_CODE_SYNC_SKILLS=1 claude
```

Details:
- Fetches enabled organization skills from the skills list endpoint.
- Downloads skill zip files, extracts them into the local skills directory, and keeps a local `manifest.json`.
- Removes local synced skills that are no longer present remotely.
- Uses `CLAUDE_CODE_SYNC_SKILLS_WAIT_TIMEOUT_MS` to bound how long startup waits before continuing.

Evidence: Organization skill sync endpoint and downloader (search for `"list-skills?include_wiggle_skills=true"`, `"claude-skill-"`, and `"CLAUDE_CODE_SYNC_SKILLS_WAIT_TIMEOUT_MS"`)


### MCP Server Attribution in Usage Breakdown
What: Usage analysis now attributes cost/token usage to MCP servers, not just skills, subagents, and plugins.

Details:
- Session usage parsing now records `attributionMcpServer`.
- The usage breakdown UI adds an "MCP servers" section.
- If an MCP server dominates usage, Claude Code now explains that MCP tool results remain in context until `/compact` or server disablement.

Evidence: Usage breakdown now includes MCP servers (search for `"MCP tool results stay in context for the rest of the session"` and `"attributionMcpServer"`)


### More Complete Diff View Keyboard Navigation
What: Diff review gained more familiar navigation bindings.

Usage:
```text
j / k       next or previous file
Space / b   page down or page up
g / G       top or bottom
Home / End  top or bottom
```

Details:
- The diff view already supported arrow navigation.
- 2.1.149 adds Vim-style and pager-style bindings to the diff context.

Evidence: Diff keymap additions (search for `j: "diff:nextFile"` and `"shift+g": "scroll:bottom"`)


### Managed MCP Policy Can Allow Claude.ai Cloud Connectors
What: Managed settings can now opt into loading claude.ai cloud MCP connectors alongside `managed-mcp.json`.

Details:
- The new managed setting is `allowAllClaudeAiMcps`.
- Default behavior stays locked down: cloud connectors remain suppressed when managed MCP has exclusive control unless this managed setting is true.
- This is mainly relevant for enterprise/admin-managed configurations.

Evidence: Managed MCP setting schema (search for `"allowAllClaudeAiMcps"` and `"claude.ai cloud MCP connectors load alongside managed-mcp.json"`)


### Cloud Gateway Environment Variable Is Recognized in Managed Environments
What: `CLAUDE_CODE_USE_GATEWAY` is now part of the recognized provider environment set.

Usage:
```bash
CLAUDE_CODE_USE_GATEWAY=1 claude
```

Details:
- Cloud gateway support existed before this release.
- The change is that this specific env var is now included in the CLI’s recognized provider/environment allowlists, improving hosted or managed launch paths that pass provider selection through environment configuration.

Evidence: Environment allowlist addition (search for `"CLAUDE_CODE_USE_GATEWAY"`)


### Better OpenTelemetry Resource Attribute Handling
What: `OTEL_RESOURCE_ATTRIBUTES` parsing now validates entries more carefully and reports malformed values with actionable debug messages.

Usage:
```bash
OTEL_RESOURCE_ATTRIBUTES='service.name=claude-code,deployment.environment=prod' claude
```

Details:
- Validates `key=value` structure.
- Rejects empty keys.
- Percent-decodes keys and values.
- Enforces maximum key/value lengths.
- Explains that literal `,` and `=` must be percent-encoded inside keys or values.

Evidence: OpenTelemetry resource parser (search for `"Invalid format for OTEL_RESOURCE_ATTRIBUTES"` and `"Failed to percent-decode OTEL_RESOURCE_ATTRIBUTES entry"`)


### Clearer OpenTelemetry Header Helper Failures
What: When `otelHeadersHelper` fails, Claude Code now records the failure and can print a direct stderr message explaining why telemetry headers are unavailable.

Details:
- The failure is cached as the last helper error.
- The error text changed from a generic helper failure to a clearer "OpenTelemetry export headers unavailable" message.

Evidence: Header helper error handling (search for `"otelHeadersHelper failed (OpenTelemetry export headers unavailable)"`)


### Remote Control Attestation Rejection Is Visible
What: Remote Control now surfaces a clear notification when an unsigned message or permission response is rejected under attestation enforcement.

Details:
- The attestation enforcement flag existed in the previous version.
- 2.1.149 adds user-visible rejection text for unsigned Remote Control traffic.
- This helps explain why a remote action did not execute.

Evidence: Remote Control rejection notice (search for `"Remote Control: unsigned"` and `"without a valid device signature"`)


## Bug Fixes

- Bash commands containing null bytes now produce a redacted, typed error instead of echoing the raw failing argv path through the normal pre-spawn error. Evidence: Bash pre-spawn handling (search for `"Bash: command contained null bytes (argv echo redacted)"`)

- Image reads now distinguish empty files and invalid image magic bytes with typed error summaries, making tool failures easier to classify and present. Evidence: image validation errors (search for `"Image file is empty"` and `"Image extension but invalid magic bytes"`)

- PDF reads now preserve structured extraction failures and provide a typed unsupported-model error when full-PDF reading is unavailable on the current model. Evidence: PDF read handling (search for `"PDF unsupported on current model"`)

- Global gitignore updates now respect `core.excludesfile`, verify that the written rule actually takes effect, and warn when the path is already tracked or Git is reading a different excludes file. Evidence: gitignore verification (search for `"core.excludesfile"` and `"but git check-ignore still reports not-ignored"`)

- Orphaned permission handling now treats missing or empty `updatedInput` as a fallback case, not only `undefined`, reducing failures when a permission response lacks usable updated tool input. Evidence: permission fallback message (search for `"updatedInput is missing or empty, falling back to original tool input"`)

- Team memory sync now skips pushes when the server has been marked unavailable instead of repeatedly attempting a doomed upload. Evidence: team memory server guard (search for `"Team memory server marked not-available"`)


## In Development

Features with infrastructure added but not yet enabled. These are shipped "dark" and may become available in future versions.


### Wellbeing Break Reminders and Quiet Hours [In Development]
What: A future `/wellbeing` command is being prepared to configure break reminders and quiet-hours nudges.

Usage:
```text
/wellbeing
/breaks
/break-reminder
/downtime
```

Status: Disabled/stubbed.

Details:
- New settings schema exists for `breakReminder` and `quietHours`.
- Break reminders include enablement, interval minutes, break threshold minutes, and custom message.
- Quiet hours include enablement plus local-time `start` and `end` values.
- The command metadata exists with aliases, but `isEnabled` returns false.
- The command handler currently reports that wellbeing settings are not available in this build.

Evidence: Disabled wellbeing command and settings schema (search for `"Configure optional break reminders and quiet-hours nudges"`, `"Wellbeing settings are not available in this build"`, and `"Show a friendly nudge after sustained continuous use"`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.149.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.149.txt`
