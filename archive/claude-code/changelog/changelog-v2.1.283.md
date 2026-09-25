# Changelog for version 2.1.283

## Summary

Version 2.1.283 adds managed model denylists, stricter model allowlist matching, and a signed configuration URL option. Compared with 2.1.282, it also improves plugin recovery, MCP compatibility, prompt customization, and cloud-session safeguards, while adding gated work on idle compaction and live mod development.

## New Features


### Exact model allowlists and model denylists

What: Administrators can prevent automatic access to later model versions and explicitly block models across their supported spellings.

Usage:

In managed settings:

```json
{
  "availableModels": ["claude-sonnet-4-6"],
  "availableModelsMatch": "exact",
  "deniedModels": ["opus"]
}
```

Details:

- `availableModelsMatch: "exact"` prevents a listed model version from implicitly permitting later versions. Recognized dated and fast variants remain covered; `-latest` requires a corresponding entry.
- Family aliases such as `opus` still match the whole family, even with exact matching.
- `deniedModels` takes precedence over the allowlist. It recognizes provider prefixes, dates, and fast variants rather than blocking only one literal spelling.
- Both new settings are read from managed settings only.
- The default model must satisfy applicable restrictions. Claude Code chooses an allowed alternative where possible and refuses startup when none is available.
- Exact allowlists do not restrict every independently selected helper model; the denylist also covers helper requests.

Evidence: New schema definitions and model-selection checks, absent from 2.1.282; search for `"availableModelsMatch"`, `"deniedModels"`, and `"default model blocked by managed settings"`.


### Signed client configuration URLs

What: Claude Code can load an Anthropic-signed configuration document supplied through a URL.

Usage:

```bash
claude --client-data-url "$ANTHROPIC_PROVIDED_URL"
```

Alternatively:

```bash
export CLAUDE_CODE_CLIENT_DATA_URL="$ANTHROPIC_PROVIDED_URL"
claude
```

Details:

- The URL must be an accepted HTTPS address on `downloads.claude.ai`, supplied by Anthropic.
- Claude Code verifies the document and its signature, rejects older document versions than previously accepted, and checks that the selected model is covered.
- Startup stops if the requested configuration cannot be loaded or applied.
- Supported only for local sessions talking directly to the Anthropic API. Cloud, remote-environment, SSH, and third-party-provider sessions are rejected.
- Organization policy can prohibit this configuration source.

Evidence: New CLI registration, startup loader, and signature-validation path; search for `"--client-data-url <url>"`, `"claude-code-client-data-v1"`, and `"CLAUDE_CODE_CLIENT_DATA_URL"`.

## Improvements


### Combine prompt files with inline instructions

System prompt files can now be combined with inline text instead of causing a mutually exclusive options error. The file contents come first, followed by the inline instructions separated by a blank line.

Usage:

```bash
claude \
  --append-system-prompt-file ./team-instructions.txt \
  --append-system-prompt "Focus on backward compatibility."
```

The same composition applies to `--system-prompt-file` with `--system-prompt`. Remote Control sessions still reject combining the two append options.

Evidence: The previous mutual-exclusion checks are replaced with prompt concatenation; search for `"--system-prompt-file"` and `"Error: --append-system-prompt cannot be given with --append-system-prompt-file in a Remote Control session"`.


### Fewer suggestions when you consistently ignore them

Claude Code reduces prompt-suggestion frequency after 20 consecutive unused suggestions, once the installation is at least two weeks old. In the reduced-frequency path, it generates suggestions on one in ten eligible turns.

Using a suggestion resets the suppression. Explicitly enabling suggestions with `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=true` bypasses it.

Evidence: New usage tracking, generation checks, and notification; search for `"promptSuggestionUnusedStreak"` and `"Showing fewer prompt suggestions"`.


### Explicit consent for local MCP servers in cloud sessions

The existing cloud-to-local tool workflow gains a consent dialog for offering this machine’s MCP servers to cloud sessions. Servers continue running locally with their saved logins.

Details:

- Consent choices are saved per machine.
- Local allow, deny, and ask rules continue to apply.
- New or changed tool descriptions can cause a server to be withheld pending renewed approval.
- Project-defined and administrator-deployed servers are excluded from the advertised offer described by this dialog.
- This is conditional on the cloud attachment and remote-tool-serving paths being available; it is not a guarantee that every cloud session can access local servers.

Usage: In a supported attached session, start `claude --cloud` from a project directory and respond to the MCP-server consent prompt.

Evidence: New consent and reconsent UI connected to cloud startup; search for `"Let cloud sessions use this machine's MCP servers?"`, `"Yes, offer this machine's MCP servers"`, and `"MCP passthrough server withheld: snapshot changed"`.


### Clearer remote-call outcomes and stronger local protections

Remote-tool responses more clearly distinguish calls that never ran, calls still awaiting approval, completed commands whose output was withheld, and interrupted calls that may have had effects. Unreachable-machine guidance tells Claude to continue independent work rather than repeatedly retrying.

The serving path also adds explicit protections around credential stores, sensitive login files, and shell commands that could change Claude Code’s settings. Ambiguous or destructive operations can require approval in the session.

Evidence: Search for `"This command is flagged as destructive."`, `"remote_call_host_settings_shell_write"`, `"Do not retry non-idempotent commands blindly."`, and `"does not let a cloud session query its credential store"`.


### Safer plugin installation-record recovery

Plugin management now distinguishes damaged installation records from records written in a format this build cannot understand.

Details:

- Unreadable JSON can be preserved beside the original before rebuilding the installation list.
- Invalid plugin-ID records are copied aside before removal.
- Unknown-format records under valid IDs prevent destructive rewriting and produce guidance to update Claude Code or use the version that wrote them.
- If the required backup cannot be written, the original list is left unchanged.

Evidence: Search for `"installed_plugins.unreadable."`, `"installed_plugins.set-aside."`, and `"installed_plugins.json was not replaced: it holds what this build cannot read"`.


### Better plugin failure and removal messages

Skill lookup now distinguishes a plugin that failed to load from a skill that is simply not installed. Where applicable, messages direct users to `/reload-plugins` or explain that a restart is required.

Marketplace removal also explicitly lists plugins uninstalled by the operation and explains that their saved options, secrets, and data are removed where possible. The underlying removal behavior already existed; the clearer reporting is the change.

Evidence: Search for `"tell the user the plugin could not be loaded here, not that the skill is not installed"`, `"Also uninstalled"`, and `"The removal also deletes their saved options, secrets and data where it can."`.


### Better keyboard-binding diagnostics and guidance

Invalid modifier names now produce an error explaining what shortcut the parser actually interpreted, with a suggested correction where possible.

The bundled keybinding guidance also corrects the documented chord timeout to three seconds and clarifies that `cmd`/`super` differs from terminal `meta`/`alt`. Those modifier distinctions already existed in the parser.

Evidence: Search for `"is not a modifier"`, `"Did you mean"`, and `"3-second timeout between keystrokes"`.


### Dynamic connector declarations for artifacts

The existing artifact capability parser now accepts a dynamic MCP declaration. It allows a page to request connectors by name at runtime, with each viewer approving access at first use.

Example capability declaration:

```json
{
  "mcp": {
    "dynamic": true,
    "servers": []
  }
}
```

This is an extension to the existing Artifact workflow, whose availability still depends on the session. It does not grant connector access automatically.

Evidence: New validation and explanatory text; search for `"dynamic_not_boolean"` and `"under this dynamic declaration each viewer is asked to approve them at first use"`.


### Clearer artifact publishing and query limits

Artifact guidance now distinguishes limits on a single publish from limits on an entire version, explaining how to upload additional files in subsequent publishes without removing omitted files.

Database-query guidance also makes explicit that ordered queries return a single page without a continuation cursor. Users can request a larger `query.limit`, up to 1,000, or omit ordering to page through a collection.

Evidence: Search for `"files left out of a later publish are kept"` and `"A query with `order_by` is a single page"`.


### Cloud file-sync policy and recovery feedback

File sync now explicitly checks organization data-retention restrictions and explains when synchronization is unavailable or has stopped. Storage-exhaustion messages distinguish work remaining in the cloud from files successfully delivered to the local machine.

Sync diagnostics also better explain unsupported Git attribute configurations, unsafe file-placement conditions, and partial restoration after a cloud environment is recreated.

Evidence: Search for `"File sync is not available for your organization: its data retention policy does not allow it."`, `"this session's file store is full"`, and `"a git setting on the user's machine can change which attribute rules git applies"`.

## Bug Fixes

- **Older Java MCP servers:** Adds a one-time reconnect without elicitation `form` and `url` fields when a server rejects those capabilities during initialization. The existing `bareElicitationCapability` setting remains available as a workaround. Search for `"server rejected elicitation form and url at initialize"`.

- **MCP configuration persistence:** Adding or removing a server now reports when the global configuration write failed or could not be confirmed, rather than implying success. Search for `"MCP server config write did not reach the global config file"`.

- **MCP shutdown cleanup:** Prevents new stdio MCP processes from starting during shutdown and adds cleanup for processes that never established a connection. Search for `"Claude Code is shutting down; not starting this MCP server process"` and `"has no established connection at exit"`.

- **Dangerous Windows deletion commands:** Extends PowerShell permission checks to recognize destructive `cmd` deletion commands, including directory changes and variable-expanded targets, and block protected paths such as drive roots and the home directory. Search for `"tengu_curious_lake"` and `"no command may remove that path"`.

- **Plugin evaluation with old Git:** Refuses `claude plugin eval` when Git is older than 2.31 or its version cannot be established, because the evaluation depends on environment-scoped configuration to disable repository hooks and helpers. Search for `"eval: git too old for env-scoped config"`.

- **Account-memory writes from spawned work:** Ordinary subagents, teammates, forks, and backgrounded queries cannot write account memory through the protected memory-server path; they must pass proposed changes back to the main agent. Hook rewrites of protected memory calls or answers are also rejected. Search for `"Only the session's main agent can change the user's account memory"` and `"a hook may allow or deny such a call but not change it"`.

- **Memory maintenance with unreadable records:** Automatic memory consolidation skips unreadable or newer-format item records instead of proceeding as though they were usable. Search for `"[autoDream] skipped: the memory items could not be read"` and `"[autoDream] skip — newer item record"`.

## In Development

These additions have implementation behind rollout gates or conditional activation. Their presence does not establish general availability.


### Idle compaction before prompt-cache expiry [In Development]

What: Compact a large, idle conversation before its one-hour prompt cache expires.

Status: Feature-flagged; off by default.

Details:

- Controlled by `tengu_sunny_locket`, with separate logging and compaction modes.
- Checks that automatic compaction is enabled, the cached prefix is still valid, the conversation is large enough, and the session is not busy.
- Successful compaction adds a visible notice.

Evidence: Search for `"tengu_sunny_locket"` and `"Compacted while idle, before the prompt cache expired"`.


### Session-local mod hot reloading [In Development]

What: Develop live panes, status lines, toasts, and behavior changes inside Claude Code using function-hook plugins that reload during the session.

Status: Behind the existing function-hooks rollout gate, with new session-specific approval.

Details:

- `/plugin-authoring` gains a mod-oriented workflow and supporting development files.
- Claude asks whether to enable hot reloading before activating newly written mods.
- Changes can be applied at a turn boundary; declined or unanswered activation is explicitly reported as not loaded.
- Trusted-workspace, hook, local-plugin, safe-mode, and managed-policy restrictions still apply.
- The function-hooks gate defaults to off, though the existing `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS` override can enable that subsystem.

Evidence: Search for `"Write a mod: a live pane, view or behaviour change in Claude Code"`, `"Enable hot reloading for this session?"`, and `"tengu_plugin_hooks_modules"`.


### Background shell-task status tool [In Development]

What: Let Claude query a background shell command by task ID and receive its state or completed output.

Status: Feature-flagged behind `tengu_violin_rosin`, defaulting to false, with additional session restrictions.

Details:

- The new shell-task implementation exposes `GetTask` for running and recently completed commands.
- Results distinguish working, completed, and cancelled tasks.
- Completion can be delivered automatically; repeated identical status queries within one response are curtailed.
- This concerns background execution, not the task-planning list.

Evidence: Search for `"Get the current state of a background task"`, `"Repeated GetTask call; not answered again."`, and `"tengu_violin_rosin"`.


### Rechecking connector registration availability [In Development]

What: Revisit a saved finding that an eligible connector does not support terminal OAuth registration, allowing discovery to recover when the server’s capabilities change.

Status: Feature-flagged; relevant gates default to false.

Details:

- Adds states distinguishing an unavailable registration path from one due for rechecking.
- Applies only to eligible connector configurations; it is not an unconditional retry for every MCP server.

Evidence: Search for `"tengu_starry_locket"`, `"tengu_twinkly_prism"`, and `"redialToRelearnRegistration"`.

## Notes

- Administrators adopting exact model matching should list concrete model IDs. Release-dependent aliases such as `best`, `opusplan`, and `default` are ignored in that mode.
- Scripts using `claude plugin eval` need Git 2.31 or newer.
- Keyboard documentation changes do not introduce new modifier semantics or establish a newly increased timeout.
- This comparison covers the CLI sources in 2.1.282 and 2.1.283, with substantive additions checked against the original Bun modules. Rebundling changes and separate VSCode, SDK-package, and Windows-installer features are excluded.


Generated with:
- tool: `harness-investigations@1f569b5-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.283.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.283.txt`
- source modules: `archive/claude-code/original/cli-v2.1.283.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
