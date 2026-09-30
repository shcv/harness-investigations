# Changelog for version 2.1.286

## Summary

Compared with 2.1.285, this release enables plugin function hooks by default, adds prompt-composition hooks, and tightens plugin dependency installation. It also improves AWS/GCP sign-in coordination, MCP compatibility, model-fallback diagnostics, and worktree cleanup. New learning suggestions, artifact-sharing integration, and model-upgrade prompts ship behind availability controls.

## New Features


### Prompt Composition Hooks for Plugins

What: Plugin authors can inspect or customize the composition of the system prompt through the new `prompt.compose` interface.

Usage:

```javascript
// Inside a function-hook plugin with access to $:
const { sections } = await $.prompt.compose();
```

Details:

- The interface accepts composition facts such as tools and traits, or no arguments.
- Prompt sections carry an `id`, `text`, and `scope`, distinguishing shared sections from session-specific sections.
- Validation rejects duplicate section IDs, invalid scopes, and shared sections placed after session sections.
- If hook dispatch fails, Claude Code falls back to composing the prompt itself.
- This is a plugin capability, not a new slash command.

Evidence: New hook registration, validation, and runtime dispatch in the original modules; search for `"prompt.compose"`, `"$.prompt.compose takes the facts to compose for"`, and `"prompt.compose: the dispatch failed, the engine composes the prompt itself"`.

## Improvements


### Plugin Function Hooks Default to Enabled

Existing plugin function-hook support now defaults to enabled, instead of requiring an explicit opt-in when no rollout value is available.

Usage:

```bash
# Explicitly disable installed plugins' function hooks:
CLAUDE_CODE_ENABLE_FUNCTION_HOOKS=0 claude
```

Settings, policy, execution mode, and the server-controlled rollout can still prevent hooks from loading. Diagnostics now explain whether hooks were disabled through configuration or the rollout switch.

Evidence: The fallback for `"tengu_plugin_hooks_modules"` changes from false in 2.1.285 to true in 2.1.286. Search for `"CLAUDE_CODE_ENABLE_FUNCTION_HOOKS"` and `"hooks modules are turned off for installed plugins in this process"`.


### Safer Plugin Dependency Installation

Plugin dependency installation now validates package metadata and lockfiles before installing into a separate staging directory. The resulting dependencies replace the plugin’s `node_modules` only after installation succeeds.

Details:

- Registry package names and tarball addresses receive additional validation.
- Checks reject unsupported dependency sources, missing integrity hashes, invalid package paths, and executable links escaping their packages.
- HTTP registry overrides and download addresses are checked to avoid sending saved registry credentials over an unsafe connection.
- Binary `bun.lockb` files are refused; plugin authors need a text `bun.lock`.
- Unsupported `overrides` and `patchedDependencies` produce explicit explanations.
- A plugin-local `bunfig.toml` no longer causes the previous blanket rejection: installation happens in the staging directory.

Evidence: Search for `"Skipped installing this plugin's dependencies:"`, `"its bun.lockb is a binary lockfile that cannot be checked"`, `"has a bin link that points outside its package"`, and `"previous-node_modules"`.


### Stronger Managed Plugin Policy

The existing security-default plugin gains additional controls over user-installed plugins.

Details:

- User-installed plugins cannot lift settings-based deny rules by default.
- Managed configuration can restrict loading to organization-controlled mods through `allowManagedModsOnly`.
- Permission-check failures refuse the affected call when deny-rule enforcement cannot be established.
- These protections apply where the security-default plugin is active; its existing managed-settings and organization eligibility still govern availability.

Evidence: New checks in the original security-default module; search for `"allowModsToOverrideDenyRules"`, `"allowManagedModsOnly"`, and `"the deny rules in your settings could not be checked for this call"`.


### Coordinated AWS and GCP Sign-In Across Sessions

Sessions using `awsAuthRefresh` or `gcpAuthRefresh` now coordinate refresh commands across Claude Code processes, reducing overlapping sign-in attempts.

Details:

- A waiting session can reuse a successful refresh performed elsewhere.
- Messages explain when another process is already running the sign-in command.
- Recovery handles a Claude Code process exiting while its sign-in helper remains alive.
- Cancellation and subsequent requests can participate in handing the sign-in attempt to another session.
- The coordination is enabled by default; `CLAUDE_CODE_DISABLE_AUTH_REFRESH_LOCK` disables it.

Evidence: Both refresh entry points now use the shared coordination path. Search for `"Another Claude Code process is running your"`, `"A Claude Code session closed before its"`, and `"CLAUDE_CODE_DISABLE_AUTH_REFRESH_LOCK"`.


### A More Useful Hooks Browser

`/hooks` now presents configured hooks together, grouped by event, with their source, matcher, and hook type. A separate “All events” view lists available events and indicates which have hooks.

Usage:

```text
/hooks
```

The menu remains read-only. Descriptions explain whether a hook comes from a plugin, built-in behavior, managed settings, or a session-created registration, and where it can be changed.

Evidence: Search for `"All events"`, `"Hook events"`, `"no hooks yet"`, and `"To change or remove this hook, edit"`.


### Read-Only Marketplace Resolution

Programs handling plugin-install links can check whether Claude Code would reuse an existing marketplace without adding one.

Usage:

```bash
claude plugin marketplace add owner/repository --from-link --resolve-only
```

Details:

- Returns one JSON line: `{"existing":"<marketplace>"}` or `{"existing":null}`.
- Requires `--from-link`.
- Cannot be combined with `--sparse` or `--scope`.
- The option is intentionally hidden from ordinary help output.

Evidence: Search for `"--resolve-only"`, `"--resolve-only needs --from-link"`, and `"adds nothing and prints one JSON line"`.


### Simpler Claude Test Browser Startup

Where the existing Claude Test plugin is available, `/claude-test` now connects its browser helper directly instead of starting it through a plugin reload and command rerun.

Usage:

```text
/claude-test
```

Failure messages distinguish disabled helpers, policy refusals, duplicate helper servers, connection failures, and tools that have not appeared yet. Claude Test remains subject to its existing availability gate and requires an interactive terminal session.

Evidence: Compare the old `"Starting the Claude Test browser helper. Claude Test runs the next two commands itself"` message with the new direct `mcp.connect` path. Search for `"Claude Test: $.mcp.connect rejected:"` and `"Claude Test is not ready yet"`.


### Clearer Context Errors After Model Fallback

When repeated compaction follows a switch to a model with a smaller context window, the error can now identify the fallback as the likely cause.

It names the original and fallback models, shows their effective context sizes, explains that the next message tries the original model first, and suggests a compatible fallback or `/clear`.

Evidence: Search for `"The likely cause: while working on this response, Claude Code fell back from"` and `"Your next message tries"`.


### Targeted MCP Startup Waiting for Remote Hosts

Remote-session hosts can request a bounded startup wait for specific MCP servers rather than relying solely on the general startup policy.

Details:

- `CLAUDE_CODE_MCP_PREWAIT_SERVERS` accepts comma-separated server names.
- `CLAUDE_CODE_MCP_PREWAIT_SERVERS_MS` controls the wait budget; zero disables this additional wait.
- Names must correspond to servers present in the startup `--mcp-config`.
- This path applies to remote-hosted sessions, not ordinary standalone terminal launches.

Evidence: Search for `"CLAUDE_CODE_MCP_PREWAIT_SERVERS"`, `"CLAUDE_CODE_MCP_PREWAIT_SERVERS_MS"`, and `"names servers with no --mcp-config row at start-up"`.


### Clearer Ultrareview Cancellation and Delivery Messages

Ultrareview now distinguishes stopping the local wait from stopping the cloud review. Cancellation and failure messages explain whether findings will still arrive and whether a requested pull-request post remains possible.

Messages also clarify that starting another review consumes a new review allowance or usage credits.

Evidence: Search for `"Stopped waiting. The review may still be running in the cloud"`, `"The full review is in this session."`, and `"A new run is a new review"`.

## Bug Fixes

- **Fast-mode fallback recovery:** When a fallback model rejects fast mode, Claude Code remembers that rejection for the session and uses standard speed for that model. Search for `"Fast mode rejected for fallback model"` and `"fast-mode-fallback-model-rejected"`.

- **Older MCP server compatibility:** The compatibility retry for servers rejecting elicitation capabilities now also handles rejection during reconnection after protocol negotiation. Search for `"server rejected elicitation form and url on the reconnect"`.

- **Recovery from stale MCP discovery decisions:** A failed or timed-out listing can invalidate a remembered protocol verdict so the next connection probes the server again. Search for `"got no result in time; forgetting the verdict"` and `"the next dial probes server/discover"`.

- **Broader recovery from rejected API beta headers:** Recognized beta rejections can remove the unsupported header and retry, with rejection state also retained for relevant subsequent requests. Search for `"[betas] the API refused"` and `"retry:beta-rejected:"`.

- **Safer worktree removal at exit:** Cleanup rechecks that the session still owns the selected worktree before removing it. Waiting for removal now handles interruption, timeout, and failure explicitly, including warnings about partial deletion. Search for `"this session had switched away from it before Claude Code exited"` and `"Stopped waiting for the removal of the worktree at"`.

- **Live enforcement of Remote Control policy:** Connected bridges now react when organization policy disables Remote Control or session mirroring, rather than relying only on startup checks. Search for `"Remote Control was turned off by your organization's policy."` and `"Session mirroring was turned off by your organization's policy"`.

- **Task-list recovery during host-managed resume:** When the host supplies a `task_list_restore` request, Claude Code can reconstruct an empty task list from the transcript, advance task IDs, and apply subsequent handoff changes. Existing nonempty lists are preserved. Search for `"task_list_restore"` and `"[Tasks] boot restore:"`.

- **More robust malformed tool-result handling:** Unexpected non-text tool-result values are converted to text where possible, bounded in length, and replaced with a diagnostic placeholder if conversion fails. Search for `"[tool result could not be converted to text]"` and `"of this tool result not shown"`.

- **Better silent-stream failure reporting:** Background-agent retries now distinguish a lost response stream from an agent making no progress. Search for `"agent lost its reply on all"` and `"reply lost — the response stream went silent"`.

## In Development

The following additions are gated, disabled, or incomplete in this build. Their presence does not establish general availability or a future release date.


### You Should Know Learning Suggestions [In Development]

What: A background observer offers short explanations of consequential details the user might otherwise miss while Claude works.

Status: Feature-flagged and disabled by default.

Details:

- Suggestions appear above the prompt as “You should know” or “Heads up.”
- Interaction paths include learning more, acknowledging existing knowledge, dismissing a suggestion, and discussing it in the main session.
- The implementation also contains a path for producing a private explanatory artifact where the host supports it.
- Availability requires `tengu_jolly_dewdrop`, settled compliance information, and an eligible session.
- The plugin declares `defaultEnabled: false`; HIPAA, ZDR, and LDR configurations are excluded.
- Its explanatory text belongs to the plugin itself; no separate always-visible orphaned tip was established.

Evidence: Search for `"cc-plugin-you-should-know"`, `"tengu_jolly_dewdrop"`, `"A side agent is watching your back while Claude works."`, and `"Learning page ready"`.


### Artifact Sharing Through Supported Hosts [In Development]

What: Claude can request sharing an owned artifact with an organization or named organization members, subject to human confirmation.

Status: Host-gated; unavailable in an ordinary standalone terminal session.

Details:

- Requires `CLAUDE_CODE_ARTIFACT_SHARE` and a supported desktop or cloud-host context.
- Supports organization sharing and named-person sharing, with view or comment access where supported.
- Public sharing, outside-organization recipients, and granting edit access are excluded from this action.
- The host resolves people’s identities, and the person confirms or changes the audience on an approval card.
- Ownership checks, plan-mode restrictions, and concurrent-sharing-change checks can refuse the operation.
- Setting the environment variable alone does not provide the required host integration.

Evidence: Search for `"CLAUDE_CODE_ARTIFACT_SHARE"`, `"Artifact shares require a live human confirmation surface"`, `"Only an Artifact's owner can share it from chat"`, and `"This artifact's sharing changed while the approval was open"`.


### Guided Model Upgrades [In Development]

What: Eligible users can receive a prompt to resume an older conversation with a newer model, or a notice offering to update their saved default.

Status: Feature-flagged; disabled without qualifying rollout configuration.

Details:

- Resume suggestions are controlled by `tengu_rosy_pine`.
- Saved-default notices are controlled by `tengu_plum_heron`, whose fallback is off.
- Eligibility checks consider model family, conversation history, account settings, and previous responses to suggestions.
- The saved-default action introduces `chat:defaultToNewerModel`, with `Ctrl+Y` as its fallback shortcut while the relevant notice is available.
- Users can keep their current model and switch later with `/model`.

Evidence: Search for `"You’re resuming {an} {older} session. Continue with {newer}?"`, `"chat:defaultToNewerModel"`, `"tengu_rosy_pine"`, and `"tengu_plum_heron"`.


### Background Local-Memory Import [In Development]

What: Infrastructure supports treating local-memory import as a background task with progress and cancellation.

Status: Incomplete in this build.

Details:

- A new `local_memory_import` task type includes cancellation handling and progress labels.
- Exit messaging anticipates an interrupted import that can continue later.
- The inspected build leaves the task-detail component unset, and no active task-creation path was found.
- This does not establish a usable new memory-import command.

Evidence: Search for `"LocalMemoryImportTask"`, `"local_memory_import"`, and `"still reading local memory notes; running the command again later continues it"`.


### Prompt Cache Lifetime Renewal [In Development]

What: Eligible sessions can periodically renew server-side prompt-cache records while activity continues.

Status: Feature-flagged; no active configuration by default.

Details:

- The implementation sends cache-touch requests and tracks session activity.
- Availability depends on `tengu_sequential_cloud`, account and provider eligibility, and `allow_cache_keepalive`.
- Repeated failures or rejected support stop renewal.
- The source does not establish a guaranteed latency or cost reduction.

Evidence: Search for `"tengu_sequential_cloud"`, `"anthropic-cache-keepalive"`, `"/v1/messages/cache_touch"`, and `"[cache-keepalive]"`.


### Additional Remote-Tool and Project-Hook Safeguards [In Development]

What: Further infrastructure constrains commands and project hooks executed on a computer for a cloud session.

Status: Gated by remote-tool availability and additional rollout controls.

Details:

- New refusal paths distinguish unreadable settings, a sandbox still starting, and a required sandbox that is unavailable.
- Linux project-hook handling adds bubblewrap version checks and a trial sandbox run before execution.
- Additional checks cover unavailable seccomp support and isolation-weakening sandbox settings.
- These additions do not establish that remote project-hook execution is generally available.

Evidence: Search for `"bubblewrap_too_old"`, `"could not read all of its settings when this call arrived"`, `"tengu_violin_heel"`, and `"tengu_violin_neck"`.

## Notes

Plugin authors may need to replace binary `bun.lockb` files with text `bun.lock`, regenerate old npm lockfiles with npm 7 or later, or remove unsupported dependency overrides and patches. Read the specific “Skipped installing this plugin’s dependencies” message before changing the package.

This changelog compares the archived 2.1.285 and 2.1.286 CLI sources and checks substantive additions against the original Bun modules. Rollout labels describe source-level controls; they do not confirm which accounts currently receive a feature.


Generated with:
- tool: `harness-investigations@70e7cd6-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.286.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.286.txt`
- source modules: `archive/claude-code/original/cli-v2.1.286.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
