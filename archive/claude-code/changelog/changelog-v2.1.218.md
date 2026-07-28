# Changelog for version 2.1.218

## Summary

This release improves background-work handling, adds asynchronous execution controls for forked skills, and strengthens project-memory safety. It also includes a fully implemented but currently disabled secure Artifact data-reading path for interactive workshops.

## Improvements


### Background execution for forked skills

What: Skill authors can now choose whether a `context: fork` skill runs in the background or blocks until it finishes.

Usage:

```yaml
context: fork
background: false
```

Details:

- Forked skills run as background agents by default and report completion through a task notification.
- Set `background: false` when the calling workflow must wait for the fork’s result inline.
- The skill result explicitly indicates when the work was launched in the background.

Evidence: Forked-skill `background` frontmatter is new (search for `"Only for \`context: fork\`. Forks run as background agents"`).


### Clearer background-conversation navigation and recovery

Backgrounded conversations now show clearer controls in the interface and provide an explicit resume command when Claude exits after moving work to the background.

Usage:

```bash
claude --resume <session-id>
```

Details:

- The background view explains that Enter opens the conversation, Esc returns to it, and Ctrl+C twice quits.
- When appropriate, Claude prints the exact `claude --resume` command needed to resume the session.

Evidence: New messages include `"Your conversation moved to the background"` and `"Your conversation was backgrounded — resume it with: claude --resume"`.


### Observer agents can follow delegated work

Agent authors can control whether an observer also follows subagents spawned by the observed agent.

Usage:

```yaml
observer: reviewer
observeSubagents: false
```

Details:

- Observer inheritance is enabled by default for spawned subagents.
- Set `observeSubagents: false` to restrict the observer to the parent agent.
- This applies only where experimental observer agents are enabled.

Evidence: New `observeSubagents` schema field (search for `"If false, subagents this agent spawns do not inherit its observer. Defaults to true."`).


### Project-memory controls are clearer and safer

The `/config` UI now calls the existing organization-memory controls “Synced project memory,” better describing their scope. Private project selections are identified as read-only, and the UI explains when write settings have no effect.

Details:

- “Org memory” and “Org memory writes” labels are now “Synced project memory” and “Synced project memory writes.”
- A private selected project is labeled `"private project, read-only"`.
- Claude warns when a private project selection means sync-write settings cannot apply.

Evidence: Search for `"Synced project memory writes"` and `"no effect under a private project pick"`.


## Bug Fixes

- Synced project-memory sync now detects unreadable directories and stops rather than treating them as safely verifiable; it tells users to repair permissions and resumes automatically afterward. Evidence: `"A directory inside this memory store's local folder is unreadable (permission denied)"`.

- Background-session exit handling now preserves and displays a resume hint when the conversation transcript has been materialized. Evidence: `"Your conversation was backgrounded — resume it with: claude --resume"`.


## In Development

Features with infrastructure added but not yet enabled. These are shipped “dark” and may become available in future versions.


### Validated Artifact page-data reads [In Development]

What: Interactive Artifact workshops are being prepared to read decision data from published pages through a schema-validated, data-only interface.

Status: Disabled/Stubbed

Details:

- The new `read_page_data` Artifact action is designed to fetch a declared data island, validate it against a registered schema such as `"workshop-decisions"`, and return only validated typed entries rather than page content.
- The workshop workflow instructs Claude to use this action rather than manually extracting decisions from page HTML.
- The action is currently unavailable because its availability gate is hardcoded off (`Fko = !1`), even though the schema, validation, consent, and execution paths are present.

Evidence: Search for `"'read_page_data' reads the declared data island"` and `"workshop-decisions"`; the action list is gated by `Fko = !1`.


Generated with:
- tool: `harness-investigations@3c353ff`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.218.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.218.txt`
