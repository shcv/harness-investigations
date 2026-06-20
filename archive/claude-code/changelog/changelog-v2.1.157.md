# Changelog for version 2.1.157

## Summary
Claude Code 2.1.157 adds a new `claude plugin init` scaffolding command, exposes a user setting to disable the natural-language Workflow keyword trigger, and improves agent/worktree/session recovery behavior. It also adds several reliability and safety improvements around auth-token handling, MCP auth failures, background-agent resume warnings, permission review, fast-mode availability, and Windows/WSL image clipboard handling.

### Plugin Scaffolding Command

What: Plugin authors can now scaffold a new local plugin directly from the CLI.

Usage:
```bash
claude plugin init my-plugin --description "My plugin" --with skills
claude plugin new my-plugin --author "Your Name" --author-email you@example.com
```

Details:
- Adds `plugin init <name>` with `new` as an alias.
- Creates the plugin under `~/.claude/skills/<name>/`.
- Supports manifest metadata flags for description, author, and author email.
- Supports `--with <components...>` for optional scaffolding and `--force` to overwrite an existing target.

Evidence: Plugin init CLI registration (search for `"Scaffold a new plugin at ~/.claude/skills/<name>/"`, `"--author <name>"`, and `"--with <components...>"`)


### Workflow Keyword Trigger Toggle [Gradual Rollout]

What: Users can turn off the automatic `workflow` / `workflows` keyword trigger while keeping workflows otherwise available.

Usage:
```json
{
  "workflowKeywordTriggerEnabled": false
}
```

Details:
- Adds a new `workflowKeywordTriggerEnabled` user setting.
- Adds a Config UI entry labeled `Workflow keyword trigger`.
- Defaults to enabled, so existing workflow behavior is unchanged unless the user disables it.
- The setting only matters where the Workflows feature itself is available.

Evidence: Workflow trigger setting schema and config toggle (search for `"workflowKeywordTriggerEnabled"` and `"Workflow keyword trigger"`)


### Feature-of-the-Week Credit Prompts

What: Claude Code can now surface a “feature of the week” prompt that grants usage credits when eligible users run the featured command.

Usage:
```bash
claude
# Run the displayed /command when Claude Code shows a Feature of the week prompt
```

Details:
- Adds an in-product prompt showing the featured slash command and the usage-credit amount.
- Shows promotion terms and optional redeem-by text.
- Adds notifications for pending, successful, and failed credit grants.
- Eligibility and claiming depend on the server-side campaign response for the user’s organization.

Evidence: Feature-of-the-week tip and credit claim UI (search for `"Feature of the week:"`, `"Try it for"`, and `"Thanks for trying the feature of the week"`)


### Agent View Can Default to a Specific Agent

Usage:
```bash
claude agents --agent code-reviewer
```

Claude Code’s agent view now accepts an `--agent <agent>` default for sessions dispatched from the agent view. This is not the first appearance of the global `--agent` concept, but it is a new agent-view dispatch default that overrides the saved `agent` setting.

Evidence: Agent-view option text (search for `"Default agent for sessions dispatched from agent view. Overrides the 'agent' setting."`)


### Worktree Switching Is More Flexible

`EnterWorktree` can now switch an already-isolated or pinned agent into an existing managed worktree by path, rather than simply rejecting the call. The new result message also makes clear that the agent’s writable working directory changed and the prior directory was left untouched.

Evidence: Existing-worktree switch path handling (search for `"This agent's working directory and write access now point at the worktree"`)


### Background Agent Resume Warnings

When Claude Code resumes after a previous process exited while background agents were still running, it now warns that those agents were orphaned and that in-process state was lost. This helps users avoid assuming unfinished background work actually landed.

Evidence: Resume warning for orphaned agents (search for `"background agent(s) orphaned by previous process exit"` and `"was running when the previous Claude Code process exited"`)


### Auth Token Handling and Validation

Claude Code now recognizes `ANTHROPIC_AUTH_TOKEN` in more auth paths and validates OAuth-style tokens through `/api/oauth/validate`. Error messages also name `ANTHROPIC_AUTH_TOKEN` alongside API keys, Claude Code OAuth tokens, and WIF credentials.

Usage:
```bash
ANTHROPIC_AUTH_TOKEN="$TOKEN" claude
```

Evidence: Auth-token support and validation (search for `"ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, CLAUDE_CODE_OAUTH_TOKEN"` and `"Failed to validate OAuth token:"`)


### Clearer MCP Authorization Header Failures

If an MCP endpoint rejects a configured `headers.Authorization` value, Claude Code now reports that OAuth fallback is disabled when an explicit Authorization header is set. This should make misconfigured MCP auth easier to diagnose.

Evidence: MCP auth-header rejection message (search for `"Server rejected the configured Authorization header"`)


### Fast Mode Availability Status

Fast mode now reports a distinct pending-organization-status message instead of treating the still-loading state like a generic unavailability case.

Evidence: Fast mode pending status (search for `"Checking fast mode availability"`)


### Stronger Permission Review Rules

Claude Code’s permission review guidance now treats persistent configuration changes, outbound submissions, novel destinations, and agent narration around low-information actions more explicitly. This should reduce accidental approval of sends, shares, webhooks, forwarding rules, and similar hard-to-retract actions.

Evidence: Permission policy additions (search for `"PERSISTENT CONFIGURATION"`, `"OUTBOUND SUBMISSIONS"`, `"DESTINATION NOVELTY"`, and `"AGENT NARRATION"`)


## Bug Fixes

- Fixed the Windows/WSL image clipboard fallback to run PowerShell in STA mode and use `System.Windows.Forms.Clipboard`, improving image paste detection and extraction from the Windows clipboard. Evidence: Clipboard fallback command (search for `"-NoProfile -NonInteractive -Sta -Command 'Add-Type"`)

- Tightened shell assignment safety analysis so `declare` / `typeset` / `local` with `-E` or `-F` are treated like other flags that change assignment evaluation semantics. Evidence: Bash safety reason (search for `"with -n/-i/-a/-A/-E/-F flag"`)

- Improved handling for a literal single dash in command option parsing so `-` is not treated as an option flag. Evidence: Option parser guard (search for `Y === "-"`)

## In Development

Features with infrastructure added but not yet enabled. These are shipped "dark" and may become available in future versions.


### Organization Plugin Sync [In Development]

What: Claude Code now contains infrastructure for syncing organization-enabled plugins into a local `plugins/synced` directory.

Status: Environment-gated / dark-launched

Details:
- Sync is controlled by `CLAUDE_CODE_SYNC_PLUGINS`.
- The sync path fetches enabled org plugins from `/api/oauth/organizations/:orgUUID/plugins/list-plugins?enabled_only=true`.
- It downloads plugin ZIPs, validates extraction against symlinks/path escapes/oversize contents, stages updates, removes disabled plugins, and records sync errors.
- Timeout controls exist for plugin installation and MCP sync wait behavior.
- There is no normal user-facing command surfaced in this diff; this appears intended for managed or server-controlled environments.

Evidence: Plugin sync gate and endpoint (search for `"CLAUDE_CODE_SYNC_PLUGINS"` and `"list-plugins?enabled_only=true"`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.157.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.157.txt`
