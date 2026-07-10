# Changelog for version 2.1.199

## Summary

This release adds session grouping to fleet view, a guided Cowork setup skill, a suite of plugin/skill/connector discovery tools, new artifact publishing hints, and a powerful credential mask extract-pattern feature for the sandbox. Windows sandbox drops the group-SID requirement in favor of a simpler user-SID model that no longer needs a logout after install.

## New Features


### Session Grouping in Fleet View

Sessions in the fleet view (agent list) can now be tagged with a group name. Press ctrl+e while a session is highlighted to set or change the group; press ctrl+x to ungroup it. Groups provide a third view mode alongside the existing status and folder views.

Details:
- The fleet view now cycles between status view, folder view, and group view
- Sessions not yet assigned a group appear under "(ungrouped)"
- Only local sessions can be grouped (remote/bridge sessions cannot)
- Reserved group names are blocked with a clear error
- The new mode persists as `fleetViewGroupMode` in settings

Evidence: Session tag UI (search for `"ctrl+e to set group"`)


### Cowork Setup Skill

A new guided onboarding skill (`setup-cowork`) walks users through configuring Cowork for the first time: choosing a role, installing a matching plugin, trying a skill, and connecting MCP tools.

Usage:
```
Ask Claude: "set up cowork" or "get started with cowork"
```

Details:
- Triggers on natural language phrases: "setup cowork", "get started with cowork", "cowork onboarding", "configure cowork", "personalize cowork"
- Includes an interactive role-picker UI so Claude can recommend the right plugin
- Guides through four steps in sequence: role → plugin → skill → connectors
- If a skill gets invoked mid-setup, the workflow resumes after it completes

Evidence: Skill registration (search for `"Guided Cowork setup — install a matching plugin, try a skill, connect tools"`)


### Plugin, Skill, and Connector Discovery Tools

Seven new agent tools enable Claude to discover and recommend Cowork plugins, skills, and MCP connectors from within a session.

The tools:
- `ListPlugins` — list the user's enabled claude.ai plugins, with optional keyword filter
- `SearchPlugins` — search the claude.ai plugin catalog by keyword
- `SuggestPluginInstall` — render an inline install card for a specific plugin
- `ListSkills` — list the user's enabled skills, with optional keyword filter
- `SearchSkills` — search skills by keyword
- `SuggestSkills` — render a card of addable skills the user doesn't have yet
- `ListConnectors` — list installed MCP connectors for the org
- `SearchMcpRegistry` — search the MCP connector registry by keyword
- `SuggestConnectors` — suggest connectors based on the current task
- `ResolveConnectors` — resolve full connector payloads from directoryUuid values

Details:
- Plugin install cards are rendered inline; the user enables the plugin out of band and Claude calls `ListPlugins` to confirm what was installed
- All search tools accept keyword filters; omit to list everything
- Connector tools route through `/api/oauth/organizations/:orgUUID/mcp/connectors/*`
- Skill tools route through `/api/oauth/organizations/:orgUUID/skills/search` and `/api/oauth/organizations/:orgUUID/plugins/search`

Evidence: Tool names in source (search for `"ListPlugins"` and `"SearchMcpRegistry"`)


### Diff View File List Keyboard Shortcuts

Two new key bindings let you scroll the file list in the diff panel without reaching for the mouse.

Usage:
- ctrl+up / meta+up — move to the previous file in the diff list (`app:diffFileListUp`)
- ctrl+down / meta+down — move to the next file in the diff list (`app:diffFileListDown`)

Evidence: Key binding registration (search for `"app:diffFileListUp"`)


### Credential Mask: Extract Pattern Support

Credential files in the sandbox can now use a regex `extract` field to mask only the sensitive credential value inside a larger config file, rather than masking the whole file.

Usage (in settings):
```json
{
  "sandbox": {
    "credentials": {
      "files": [
        {
          "path": "~/.config/myapp/config.json",
          "mode": "mask",
          "extract": "\"api_key\":\\s*\"([^\"]+)\"",
          "onExtractNoMatch": "deny",
          "maskDuplicates": true
        }
      ]
    }
  }
}
```

Details:
- `extract` — a regex pattern; capture group 1 must capture the credential value on every match
- `onExtractNoMatch` — controls behavior when the pattern matches nothing: `"warn"` (default, file left unprotected), `"deny"` (degrade to deny mode), or `"error"` (throw and abort)
- `maskDuplicates` — when true, also replaces literal occurrences of the credential value not covered by the regex
- If `extract` is absent, the whole file is masked as before
- Binary files are still skipped with a warning

Evidence: Extract engine (search for `"extract pattern /"` and `"onExtractNoMatch"`)


### `CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS_EXCEPT` Environment Variable

Provides fine-grained control over the `CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS` flag. When set, specific plugins are exempted from the skip and continue to have their MCP servers loaded.

Usage:
```bash
CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS=1 \
CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS_EXCEPT=owner/my-plugin,another@1.0.0 \
claude
```

Details:
- Comma-separated list of plugin names or `owner/repo@version` references
- Entries with `@` match by repository; bare names match by plugin name
- When a plugin is exempted, Claude logs: "Loading MCP servers for ... despite CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS (exempted via CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS_EXCEPT)"

Evidence: Exemption check (search for `"exempted via CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS_EXCEPT"`)


### `requiresUserInteraction` Protocol Field for SDK Hosts

The permission-request protocol now includes a `requires_user_interaction` boolean field. SDK hosts that handle permission prompts programmatically must check this field: if true, they must not offer a one-tap Approve/Deny button — the user must open the session and respond through the approval card itself.

Details:
- Field is populated when the tool's `requiresUserInteraction()` method returns true
- Tools that always require user interaction now force an "ask" decision even when a rule would otherwise allow them silently
- SDK hosts receive this field as part of the `can_use_tool` request alongside `tool_use_id`, `agent_id`, and `description`

Evidence: Schema addition (search for `"True when the tool's approval card IS the user-interaction surface"`)


## Improvements


### Agent API Error Partial Output Recovery

When a subagent terminates early due to a rate-limit, overload, or server error from the API, Claude now recovers and surfaces whatever partial output the agent produced before it was cut off, rather than losing it silently.

Details:
- Introduces `AgentApiErrorTerminationError` class for these cases
- Recovered output is appended with a clear disclaimer: "Everything below is PARTIAL output recovered from the agent before it was cut off. The agent did NOT finish its task — treat these results as incomplete."
- Applies to rate_limit, overloaded, and server_error error kinds

Evidence: Error class definition (search for `"AgentApiErrorTerminationError"`)


### Windows Sandbox: User-SID Model (No Logout Required)

The Windows sandbox network filter now keys on the dedicated `srt-sandbox` user's SID rather than a discriminator group membership. This eliminates the logout-and-back-in requirement that the previous group-SID model imposed.

Details:
- Install message updated: "No logout is needed: the WFP filter keys on the dedicated `srt-sandbox` user's SID, so your network is unaffected."
- `srt-win acl grant` and `srt-win acl restore` now accept `--sandbox-user-sid` instead of `--group-sid` / `--name`
- `srt-win user status` replaces `srt-win group status` for pre-flight checks
- Provisioning check now verifies both `provisioned` and `credPresent` from user status
- WFP status "cannot-read" (non-elevated) is now handled gracefully instead of failing

Evidence: Install message (search for `"No logout is needed: the WFP filter keys on the dedicated"`)


### TLS CA: Extra Certificate Paths Support

The sandbox MITM CA loader now accepts an `extraCaCertPaths` list to incorporate additional trusted CA certificates alongside the configured MITM CA and the system bundle.

Details:
- Each path must contain a valid PEM `CERTIFICATE` block
- Unreadable paths or paths without a valid PEM block are skipped with a warning and their reason logged: `"[mitm-ca] extraCaCertPaths: cannot read ..."` or `"has no PEM CERTIFICATE block; skipping"`
- The certificate from `NODE_EXTRA_CA_CERTS` is still included if set

Evidence: Certificate loader (search for `"[mitm-ca] extraCaCertPaths:"`)


### `tlsTerminate` Inherits from Flag/User Settings

The `tlsTerminate` setting for the sandbox network is now also read from flag settings and user settings (when user settings aren't masked), not only from local or project settings. This means a managed policy or user preference can enable TLS termination without requiring per-project configuration.

Evidence: Settings merge logic (search for `"flagSettings"` near `"tlsTerminate"`)


### New Contextual Hints

Four new in-session hints guide users toward relevant features at the right moment:

- Rewind past /clear: when a user asks for something from before `/clear`, Claude hints "Press Esc twice or type /rewind, then pick the previous-session entry at the top"
- Artifact from PR review: when a PR explanation is the output, Claude suggests "Ask Claude to 'publish an artifact walking through this PR'"
- Artifact from code walkthrough: when explaining how code works, Claude suggests "Ask Claude to 'publish this explanation as an artifact'"
- Artifact from analysis results: when presenting metrics or benchmarks, Claude suggests "Ask Claude to 'publish this as an artifact'"

The `/config` inline syntax hint is also improved to include `(run /config --help to list keys)` so users know how to discover available keys.

Evidence: Hint definitions (search for `"rewind-past-clear"` and `"artifact-pr-explainer"`)


### File Already-in-Context Deduplication

When a file is already loaded in context and its content has not changed on disk, Claude now avoids re-reading it and instead uses the cached version. A `<system-reminder>` indicates when a cached version is being used, and the UI shows "Already in context (…)" to reduce unnecessary re-reads.

Evidence: File read handler (search for `"This file is already in your context"`)


### "Showing Recent Messages" Notice for Truncated Sessions

When a session's message history is being truncated (e.g., in a remote or compact view), the UI now displays "Showing recent messages · full history at [URL]" so users know they can navigate to the complete session history.

Evidence: Notice text (search for `"Showing recent messages"`)


### Low Memory Hint on Agent Crash

When an agent worker crashes before initialization and the system appears to be low on memory, the crash detail now includes "— possibly low memory — free some up and retry" to guide the user.

Evidence: Crash detail message (search for `"possibly low memory"`)


### `CLAUDE_CODE_BRIDGE_SESSION_ID` Cleaned from Child Processes

The `CLAUDE_CODE_BRIDGE_SESSION_ID` environment variable is now removed from the environment of child processes (alongside `CLAUDE_CODE_SESSION_ID` and `CLAUDE_CODE_CHILD_SESSION`). This prevents bridge session context from leaking into subprocesses launched during a session.

Evidence: Environment cleanup (search for `"CLAUDE_CODE_BRIDGE_SESSION_ID"`)


### Plan Artifact Template: `{{TAB_TITLE}}` and Updated CDS Tokens

The plan artifact HTML template now supports a `{{TAB_TITLE}}` placeholder (for the browser `<title>` element), separate from `{{TITLE}}` (the document heading). This lets auto-published plan artifacts use the filename as the tab title while displaying the document heading as the `<h1>`.

The template's CSS design tokens are now sourced from the vendored `@ant/cds` token set (byte-identical copy, drift-tested) rather than hand-maintained literals, keeping artifact styling consistent with the CDS design system.

Evidence: Template comment (search for `"{{TAB_TITLE}}"`)


## Bug Fixes

- Fixed race conditions in settings writes: all config mutations now go through an async write queue, preventing concurrent writes from clobbering each other. This resolves a class of data loss bugs where rapid settings changes (e.g., onboarding completion, MCP server toggles) could race and produce corrupt state (search for `"saveConfigWithLock: merge base is missing auth"`)

- Fixed subagent respawn: if a session was stopped while a respawn was in flight, the respawn now bails cleanly with a log entry instead of proceeding into a dead-end state (search for `"bailed — job was stopped while the respawn was in flight"`)

- Fixed permission write order: when a tool permission is granted via the SDK, the permission list is now saved to disk before the callback fires, ensuring the change is persisted even if the session terminates immediately after approval (search for `"vz(i)"` near permission grant)

- Fixed `--dangerously-skip-permissions` flag placement: the flag can now appear before the `daemon` subcommand (`claude --dangerously-skip-permissions daemon ...`), not only after it (search for `"--allow-dangerously-skip-permissions"`)

- Fixed stacked slash command expansion: messages created by expanding stacked slash commands are now excluded from certain history scans that would previously misidentify them as user input (search for `"stackedExpansion"`)


## In Development

Features with infrastructure added but not yet enabled for all users.


### Request Gzip Compression [In Development]

Infrastructure for compressing API request bodies with gzip is present and can be enabled via environment variable or a server-side feature flag. Default is off.

Status: Feature-flagged (`tengu_gzip_request_bodies`, default false) and also controllable via `CLAUDE_CODE_GZIP_REQUEST_BODIES=1`.

Evidence: Gzip check (returns `false` by default, search for `"CLAUDE_CODE_GZIP_REQUEST_BODIES"`)


Generated with:
- tool: `harness-investigations@03136fb-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.199.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.199.txt`
