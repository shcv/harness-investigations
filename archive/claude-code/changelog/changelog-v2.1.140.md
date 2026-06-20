# Changelog for version 2.1.140

## Summary
Claude Code 2.1.140 focuses on plugin and sandbox infrastructure. The most visible changes are better plugin diagnostics for directory-loaded skills, clearer plugin manifest behavior, experimental sandbox HTTPS request filtering, `/fast` availability text for Opus 4.7, and improved agent-type matching errors.


### Skills-directory Plugins in Plugin Listing
What: Plugins auto-loaded from `.claude/skills/*` now appear in their own section in plugin listings, including version, scope, path, status, errors, and notes.

Usage:
```bash
claude plugin list
claude plugin list --json
```

Details:
- `claude plugin list` now has a separate `Skills-directory plugins (.claude/skills/*):` section.
- JSON output can include entries for these directory-loaded plugins, including `errors` and `notes`.
- Directory-loaded skill plugins cannot be managed exactly like marketplace plugins; the UI now explains that they are removed by deleting the directory or disabled with `claude plugin disable`.

Evidence: Skills-directory plugin listing (search for `"Skills-directory plugins (.claude/skills/*):"`); directory-loaded plugin explanation (search for `"This is a directory-loaded plugin"`)


### Experimental Sandbox HTTPS Filtering
What: The sandbox runtime can now terminate HTTPS inside the proxy so a request filter can inspect HTTPS request bodies.

Usage:
```json
{
  "network": {
    "filterRequest": "[function]",
    "tlsTerminate": {
      "caCertPath": "/path/to/ca.crt",
      "caKeyPath": "/path/to/ca.key"
    }
  }
}
```

Details:
- `network.filterRequest` receives a web-standard `Request` and returns an allow/deny decision.
- `network.tlsTerminate` can use a provided CA certificate and key, or generate an ephemeral CA for the session.
- `network.tlsTerminate` and `network.mitmProxy` are mutually exclusive.
- This is exposed as experimental sandbox-runtime configuration, so it is most relevant to users or integrations running Claude Code with custom sandbox/network policy.

Evidence: Sandbox request filtering schema (search for `"Per-request filter callback"`); TLS termination schema (search for `"[EXPERIMENTAL] Enable in-process TLS termination"`); mutual-exclusion validation (search for `"network.tlsTerminate and network.mitmProxy are mutually exclusive"`)


### Plugin Manifest Fields Now Clearly Override Default Folders
Plugin authors now get clearer behavior and diagnostics when `plugin.json` lists explicit component paths. For `commands`, `agents`, `outputStyles`, and `themes`, setting the manifest field means the default folder is not auto-loaded unless its files are also listed.

Usage:
```json
{
  "commands": ["commands/my-command.md"]
}
```

Details:
- The schema descriptions now say that listing files in `plugin.json` prevents automatic loading of the matching default folder.
- Claude Code now emits plugin notes when a folder exists but is shadowed by a manifest field.
- This helps plugin authors understand why a file under `commands/`, `agents/`, `output-styles/`, or `themes/` did not load.

Evidence: Manifest schema wording (search for `"When set, the commands/ directory is not auto-loaded"`); plugin note text (search for `"folder exists but is not auto-loaded because plugin.json sets"`)


### Plugin Notes Are Now Surfaced Separately from Plugin Errors
Plugin diagnostics now distinguish load-blocking errors from authoring notes. Notes appear in plugin UI and list output without demoting the plugin.

Usage:
```bash
claude plugin list
```

Details:
- New `plugin_warnings` metadata is described as authoring feedback where the plugin still loaded.
- UI output now has a `Plugin notes` section and per-plugin `Note:` lines.
- JSON plugin listing can include a `notes` field.

Evidence: Plugin warnings schema (search for `"Plugin authoring feedback"`); UI label (search for `"Plugin notes"`); count label (search for `"plugin note(s):"`)


### Fast Mode Help Now Includes Opus 4.7
The `/fast` explanatory text now says Fast mode is available on both Opus 4.6 and Opus 4.7.

Usage:
```bash
/fast
```

Details:
- The old text said Fast mode was only available on Opus 4.6.
- The new text keeps the same explanation that Fast mode uses Claude Opus with faster output and does not downgrade to a smaller model.

Evidence: Fast mode description (search for `"Fast mode for Claude Code uses Claude Opus with faster output"`)


### Agent Type Matching Is More Forgiving and More Precise
Agent spawning now normalizes requested agent type names before failing, and it reports ambiguity when multiple agent definitions normalize to the same requested name.

Usage:
```text
Use the Task tool with subagent_type=<agent-name>
```

Details:
- Agent type matching now normalizes whitespace, dash-like punctuation, underscores, and case.
- If exactly one normalized match exists and is available, Claude Code can use it.
- If multiple matches exist, the error names the ambiguous matches and tells the user which exact name to use.

Evidence: Agent type normalization helper (search for `"normalize(\"NFKC\")"`); ambiguity error (search for `"Use the exact name:"`)


### `/goal` Policy Error Mentions Managed-hooks-only Mode
The `/goal` command now gives a more accurate policy error when hooks are restricted by either `disableAllHooks` or `allowManagedHooksOnly`.

Usage:
```bash
/goal
```

Details:
- This is not a new `/goal` capability.
- It improves the error users see when organization policy prevents `/goal` from running.

Evidence: Updated `/goal` error (search for `"/goal can't run while hooks are disabled"`)


### Claude FM Uses the Short Radio URL
The Claude FM browser opener now points at `https://clau.de/radio` instead of the previous YouTube live URL.

Usage:
```bash
/fm
```

Details:
- If opening the browser fails, the fallback message now tells users to listen at the new short URL.

Evidence: Claude FM fallback URL (search for `"https://clau.de/radio"`)


## Bug Fixes

- Plugin authors now get a visible note when a default component folder is ignored because the manifest field overrides it, reducing silent plugin-load confusion. Evidence: folder shadowing note (search for `"Remove \""` and `"from plugin.json to auto-load the folder"`)

- Agent spawning now reports ambiguous normalized agent names instead of only saying the requested type was not found. Evidence: ambiguous agent error (search for `"Agent type '"` and `"is ambiguous"`)

- `/goal` now reports both hook-disabling policy modes instead of only `disableAllHooks`. Evidence: updated policy text (search for `"allowManagedHooksOnly is set in settings or by policy"`)


## In Development

Features with infrastructure added but not yet enabled. These are shipped "dark" and may become available in future versions.


### Skill Health in Plugin Views [In Development]
What: Claude Code has new infrastructure for fetching skill health data and showing it alongside plugin entries.

Status: Feature-flagged

Details:
- The health fetch is gated by `tengu_skills_dashboard_enabled`, defaulting off in the local code path.
- When enabled, Claude Code calls `/api/claude_code/skills` and maps returned skill health states such as `good`, `warn`, and `poor`.
- If the fetch fails, it logs `Skill health fetch skipped` and continues.

Evidence: Feature flag gate (search for `"tengu_skills_dashboard_enabled"`); health endpoint (search for `"/api/claude_code/skills"`); skip logging (search for `"Skill health fetch skipped"`)


### Web-session Permission Dialog Plumbing [In Development]
What: Claude Code now has more generalized plumbing for external/web session permission dialogs, including a WebFetch-specific permission dialog payload.

Status: Dark-launched / host-dependent

Details:
- The new code path only runs when `requestDialog` is supplied by the host environment.
- WebFetch gets a dedicated dialog kind that includes the target hostname.
- Terminal permission prompts still have the existing local flow; this infrastructure appears aimed at web or bridge-based sessions.

Evidence: Host dialog hook (search for `"requestDialog"`); WebFetch dialog kind (search for `"permission_webfetch"`); rendered tool-use payload (search for `"renderedToolUseMessage"`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.140.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.140.txt`
