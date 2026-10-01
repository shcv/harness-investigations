# Changelog for version 2.1.287

## Summary

Version 2.1.287 adds an operational Anthropic Directory for plugin discovery, a way to switch supported plugin sources while preserving configuration, and a terminal command for accepting project settings used by cloud sessions. Compared with 2.1.286, it also strengthens restart safeguards, gives MCP configuration more control over tool loading, and improves plugin diagnostics and file-upload handling.


## New Features


### Anthropic Directory for plugins

What: Discover and install plugins from the built-in Anthropic Directory.

Usage:

```text
/plugin directory
/plugin directory code review
```

Details:

- Directory listings appear in the plugin discovery interface, with publisher information and installation details.
- Installs use the commit specified by the listing; updates follow the Directory’s listed commit.
- The implementation defaults on, but access depends on organization policy, service availability, and connection eligibility. It requires a direct Anthropic connection rather than Bedrock, Vertex, or a gateway.
- Administrators can disable it through `disablePluginDirectory`. Marketplace allowlists and blocklists also apply.
- Turning off Directory discovery leaves previously installed plugins installed and updating.

The previous version contained placeholder integration points, but its Directory provider returned `null`. This release supplies the catalog, search, installation, and management implementation.

Evidence: Directory search and pinned installation (search for `"/api/directory/plugins"`, `"Anthropic Directory"`, `"reviewed_commit"`, and `"tengu_encapsulated_pebble"`).


### Switch plugin marketplaces while preserving settings

What: Move a supported plugin between the Anthropic Directory and an official Anthropic marketplace without manually recreating its configuration.

Usage:

```bash
claude plugin install <name>@<marketplace> --replace
```

Alternatively, open `/plugin` → Installed and select the available “Switch to” action.

Details:

- The switch installs the target copy, carries over eligible settings, stored secrets, and plugin data, then uninstalls the previous copy.
- Existing settings at the destination can take precedence; the interface explains what will be retained.
- Switching is limited to supported, matching plugins between the Directory and official Anthropic marketplaces.
- It refuses ambiguous replacements, stale previews, and sessions that ignore settings scopes needed to verify the switch.
- The target may contain newer or older code because its marketplace determines the installed revision.

Evidence: Replacement option and migration checks (search for `"--replace"`, `"Your plugin settings carry over."`, and `"Working out what the switch will do"`).


### Accept project settings for cloud sessions

What: Review and accept changes to the local project settings that this computer uses when serving cloud sessions.

Usage:

```bash
claude apply-project-settings
```

Details:

- Run the command directly in a terminal from the project folder.
- It compares project and local settings with their previously accepted versions.
- Acceptance updates the record used for future serving sessions; an already connected cloud session retains its starting configuration.
- The command requires a reviewable diff and checks for intervening file changes.
- Linked files, unreadable settings, and configurations that prevent an isolated review are refused.
- `ConfigChange` hooks can block acceptance.

This command is hidden from ordinary help, but has a registered CLI handler.

Evidence: Command registration and acceptance workflow (search for `"apply-project-settings"`, `"Accept this version for cloud sessions"`, and `"A ConfigChange hook blocked this change"`).


### GitHub REST access when `gh` is missing

What: Eligible sessions using Claude Code’s GitHub proxy can use a built-in `gh api` substitute when the GitHub CLI is not installed.

Usage:

```bash
gh api repos/{owner}/{repo}/pulls/123
```

Details:

- Claude Code installs the substitute into the session’s command environment when no `gh` executable is found at startup.
- It supports REST requests through the session’s GitHub proxy, including supported GitHub Enterprise hosts.
- It supports request fields and common API options; `--jq` requires a separately installed `jq`.
- Other `gh` commands and GraphQL are unsupported.
- It is not installed when nonessential network traffic is disabled.

Evidence: Session shim and REST handler (search for `"No GitHub CLI was found on this machine when the session started"` and `"Usage: gh api <endpoint> [flags]"`).


## Improvements


### Explicitly defer every tool from an MCP server

Setting a server’s `alwaysLoad` to `false` now overrides individual tools requesting always-loaded status. This gives users control over whether a server’s schemas occupy the prompt before tool search retrieves them.

For example, in an MCP configuration:

```json
{
  "mcpServers": {
    "example": {
      "command": "example-mcp-server",
      "alwaysLoad": false
    }
  }
}
```

Previously, a tool’s own `anthropic/alwaysLoad: true` metadata could still make it load eagerly. The new behavior applies when tool search is enabled.

Evidence: Server-level override passed into tool construction (search for `"serverDefersAllTools"` and the `"alwaysLoad"` schema description).


### Clearer plugin dependency diagnostics and repair

Installed plugins now report when required packages are missing, instead of leaving users to diagnose failures in the plugin’s components.

The diagnostics distinguish missing packages from refused installations, including unsupported lockfiles and missing package managers. Where supported, updating the plugin can install missing dependencies into its existing installation.

Usage:

```bash
claude plugin update <plugin>
```

Dependency installation already existed; the changes here are detection, explanation, and repair of incomplete installations.

Evidence: Dependency checks and repair messages (search for `"dependencies-not-installed"`, `"dependencies-refused"`, and `"Installed the packages that"`).


### Machine-readable marketplace operation results

Marketplace removal and named marketplace updates gain JSON result options for automation.

Usage:

```bash
claude plugin marketplace update <name> --json
claude plugin marketplace remove <name> --json
```

The commands retain their exit-code behavior and print a machine-readable result as the final stdout line. Updating with `--json` requires an explicit marketplace name.

Evidence: CLI option descriptions and validation (search for `"Print one machine-readable result line as the last line on stdout"` and `"--json needs a marketplace name"`).


### Automatic type contracts for plugin and mod authors

Plugin type contracts are now placed automatically under `.claude-plugin/types/<plugin>/index.d.ts` when the engine loads a dependent mod from a user-owned folder. MCP input declarations are refreshed when a mod is saved with servers connected.

The previous hidden `/plugin-types` command is removed. Authors should use the generated type layout rather than depend on that command or its `.claude/types` output.

Evidence: Updated plugin `types` schema and generation code (search for `".claude-plugin/types/<plugin>/index.d.ts"` and `"Written again at a save of the mod with a server connected"`).


### More useful image-upload recovery

File sending can now create a scaled-down image copy when the original exceeds applicable image limits. Results identify when a copy was sent, and errors give more specific recovery instructions.

Failures now distinguish oversized dimensions, unsupported formats, mismatched extensions, damaged images, upload quotas, and stalled transfers. Quota failures explicitly discourage retrying the same upload with a smaller file when size is not the issue.

Evidence: Scaling and upload-error handling (search for `"a scaled-down copy"`, `"tengu_level_wren"`, `"image_format_mismatch"`, and `"a count of files, not a size"`).


### Reuse SVG assets between artifacts

Artifact publishing now permits copying an SVG asset from another artifact when it is stored with the SVG content type and published to a path ending in `.svg`.

HTML and other XML documents still require reading and republishing their contents. The change extends the existing artifact-file reuse mechanism.

Evidence: Revised copy validation (search for `"an SVG image is copied only to a name ending .svg"` and `"a file copied to or from a name ending .svg"`).


### Measured usage explanations in supported hosted sessions

The existing `/explain-usage` command gains a path that supplies recorded conversation usage directly, instead of asking Claude to locate and analyze transcript files.

For supported hosted Cowork sessions, the explanation distinguishes measured request totals from estimated group attribution. It also identifies missing usage records, post-compaction limits, and subagent-only scope. When no usage is recorded, it asks for a plain explanation rather than an invented chart.

Evidence: Hosted usage prompt (search for `"This is the conversation's measured usage, as JSON"` and `"the split between groups is an estimate"`).


### Better “You should know” guidance

The existing observer feature now describes itself as a side agent watching for consequential things the user might miss. Its instructions more clearly attribute decisions to the main agent and discourage uncertain suggestions.

A new conditional tip explains how to enable the plugin when it is available but disabled by default. The tip checks availability and the user’s existing choice.

Evidence: Observer instructions and conditional tip (search for `"you-should-know-plugin"`, `"Want a side agent watching your back"`, and `"Avoid topics you are not confident about"`).


### Clearer feedback and terminal messages

The feedback interface now discloses that a report or bundle can include up to the last 100 error messages, which may contain file paths. If a GitHub issue link cannot hold the full description, the generated text explains that the complete description accompanied the feedback report.

Interactive startup errors also explain piped or redirected input and suggest using `-p` for prompt-and-print workflows.

Evidence: User-facing diagnostics (search for `"up to the last 100 since you launched Claude Code"`, `"GitHub's link length limit"`, and `"stdin is not a terminal"`).


## Bug Fixes

- Restarting through `/update` now checks that the conversation can be preserved, its saved file and working folder exist, and the installed launcher is available. It also refuses restart while Remote Control is connected or the installed version is held back. Evidence: search for `"Couldn't save this session to disk, so nothing was restarted"` and `"Can't restart while Remote Control is connected"`.

- Repeated `asyncRewake` failures caused by an unreadable or missing hook script no longer repeatedly wake Claude as though they were feedback on its work. The initial failure explains the broken hook installation; identical repeats are suppressed. Evidence: search for `"cannot be opened; already reported, not waking the model"`.

- Auto mode can re-evaluate a tool call locally when a hook changed its input after the server’s review. If no valid review is available, the error explains the mismatch rather than treating the old verdict as a review of the rewritten action. Evidence: search for `"after the server reviewed the response a hook rewrote this call's input"`.

- A request rejected with `thinking.display: "updates"` can retry without that setting. After a successful recovery, the conversation stops sending the unsupported setting. Evidence: search for `"retry:thinking-display-updates-unclaimed"`.

- Skill-update proposals now check whether the current `SKILL.md` was actually shown in the conversation. When needed, the tool supplies the existing content and requests a complete replacement that preserves useful material; disabled or unreadable skills receive explicit explanations. Evidence: search for `"current_skill_md"` and `"A saved proposal replaces the whole file"`.

- Directory plugin installations now bind retained data to its repository identity, preventing a later listing under the same name from silently inheriting another repository’s saved state. Uninstallation reports retained settings, secrets, or data when cleanup cannot safely finish. Evidence: search for `"plugin-directory-bindings.json"` and `"Nothing it saved was removed"`.

- The SSE connection path now detects a server that never begins responding and initiates reconnection. Evidence: search for `"SSETransport: No response within"`.

- MCP results containing multiple inline PDFs retain the first and explicitly report omitted additional PDFs. Evidence: search for `"Another PDF in this result was left out: only the first is shown."`.


## In Development

These additions have disabled entry points or require server-controlled enablement. Their presence does not establish availability for every account.


### Background commands on attached computers [In Development]

What: Let cloud sessions start, inspect, and stop background shell commands on an attached computer.

Status: Feature-flagged; `tengu_violin_varnish` defaults to false.

Details:

- The implementation tracks command status and output on the serving computer.
- Daemon status can list these commands.
- A gated stop command is implemented:

```bash
claude daemon remote-control stop-shell <id>
```

- The model receives instructions to use the remote command’s own status mechanism rather than infer its state from unrelated processes or sandboxed commands.
- Related approval and reconnect changes have separate default-off gates.

Evidence: Remote background-command lifecycle (search for `"tengu_violin_varnish"`, `"stop-shell"`, and `"Command running in the background on"`).


### Review interface for staged settings edits [In Development]

What: Review, accept, discard, or postpone settings edits that Claude previously staged for the computer’s owner.

Status: Review UI added, but no registered `/settings-review` slash-command entry was found in this build.

Details:

- Settings staging already existed in 2.1.286.
- This release adds review wording and interface components with conflict checks, diff visibility requirements, and explicit accept/discard actions.
- The separately registered `claude apply-project-settings` command uses the review infrastructure for accepting cloud-session settings.
- That command should not be confused with a confirmed general-purpose entry point for all staged proposals.

Orphaned guidance: Existing messages still direct users to `/settings-review`, including “Staged for your review · not applied until you accept it in /settings-review,” despite the missing command registration.

Evidence: Review components and command-registration comparison (search for `"Accept and apply this change"`, `"Discard this change"`, and `"settings-review"`).


### Offers to move older sessions to newer models [In Development]

What: Offer an eligible newer model when starting or returning to a session using an older model from the same family.

Status: Feature-flagged; the startup configuration defaults off, and resume offers require an enabled server configuration.

Details:

- Startup notices use `tengu_fern_plover`.
- Resume offers use `tengu_hidden_volcano` and can appear as a line or dialog.
- Eligibility includes model-family comparisons, policy checks, dismissal history, and frequency limits.
- This is an offer mechanism, not evidence that every resumed session automatically changes models.

Evidence: Offer configuration and display text (search for `"tengu_fern_plover"`, `"tengu_hidden_volcano"`, and `"You’re resuming {an} {older} session."`).


### Preserve attachment filenames during cloud handoff [In Development]

What: Place attached files into a cloud worker’s home directory under the names that the client showed its model.

Status: Feature-flagged; `tengu_keen_moth` defaults to false and the worker must advertise support.

Details:

- The handoff accepts a bounded list of attachment identities and filenames.
- It prioritizes names referenced by handed-off tool calls.
- Placement does not overwrite existing files; refused names and limits do not by themselves reject the whole handoff.

Evidence: File-placement gate and capability declaration (search for `"tengu_keen_moth"`, `"file_names"`, and `"home_files"`).


### Shell snapshots with fewer external-command dependencies [In Development]

What: Capture shell state using built-in shell operations where supported, reducing dependence on external text-processing commands during snapshot creation.

Status: Feature-flagged; `tengu_lucky_garden` defaults to false.

Details:

- The implementation probes whether required built-ins work.
- It supplies an alternative path for collecting Bash functions, options, aliases, and snapshot text.
- The previous snapshot implementation remains available as a fallback.

Evidence: Alternative snapshot generator (search for `"tengu_lucky_garden"` and `"_cc_builtins"`).


## Notes

- `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` no longer overrides the function-hook rollout decision. The runtime now consults `tengu_plugin_hooks_modules` directly. Existing hook-policy settings still apply; remove reliance on this environment variable to force enablement or disablement.
- The hidden `/plugin-types` command has been removed; plugin authors should adopt the automatically generated type contracts described above.
- This changelog compares the CLI sources for **2.1.286 → 2.1.287**. Bun module wrappers, identifier changes, and rebundling order are excluded.


Generated with:
- tool: `harness-investigations@c9a3ed3-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.287.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.287.txt`
- source modules: `archive/claude-code/original/cli-v2.1.287.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
