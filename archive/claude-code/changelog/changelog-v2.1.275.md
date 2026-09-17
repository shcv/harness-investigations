# Changelog for version 2.1.275

## Summary

Version 2.1.275 adds a “send now” keyboard action, a hidden option for loading project configuration from another directory, and image rendering for plugin interfaces in compatible terminals. It also expands artifact workflows and improves memory-sync recovery, gateway authentication, and handling of oversized search output. Direct npm plugin installation, plugin-install links, and resumable background-agent interruption ship behind rollout gates; REPL state retention across compaction remains stubbed out.

## New Features


### Send messages immediately while Claude is working

What: A new keyboard action interrupts the current turn so queued input can be handled immediately.

Usage: Press **Ctrl+Enter**, or **Ctrl+X followed by Ctrl+S**, in the chat input.

Details:

- With text or pasted attachments in the input, the action submits them and requests immediate processing.
- With an empty input, it can send already-queued input.
- Immediate interruption applies to the main prompt session when a turn is active and there is queued input.
- The action is named `chat:sendNow` for custom keybindings. The existing queue-only action remains separate.

Evidence: New keyboard bindings and submission handler, followed by a check that interrupts the active turn when input is queued (search for `"chat:sendNow"`, `"ctrl+x ctrl+s"`, and `"queued_send_now"`).


### Load project configuration from a separate directory

What: The new `--project-config-root` option lets a session use project configuration from an explicitly selected directory.

Usage:

```bash
claude --project-config-root /absolute/path/to/project
```

Details:

- Redirects project settings, `.mcp.json`, and the `.claude` configuration trees for commands, agents, skills, workflows, routines, and output styles.
- Intended for sessions that a host starts in a worktree while retaining configuration from the original project.
- The path must resolve to an existing, readable, local directory.
- The flag is implemented but hidden from normal CLI help.
- Background sessions, durable scheduled tasks, and `--routine` are unavailable with this option. Project-scoped MCP changes and workflow saves are also refused.
- An agent-view update that would relaunch without the flag requires quitting and restarting instead.

Evidence: CLI option registration, path validation, configuration readers, and explicit restrictions (search for `"--project-config-root <dir>"`, `"Background sessions are unavailable with --project-config-root"`, and `"Project-scope MCP server changes are unavailable"`).


### Images in terminal plugin interfaces

What: Plugin UI components can render PNG or raw RGBA images directly in supported terminals.

Usage: Plugin authors can supply an `Image` element with `source`, `columns`, `rows`, and `alt` properties.

Details:

- Sources accept base64 PNG data or base64 RGBA data with explicit pixel dimensions.
- Terminal detection probes for graphics support and recognizes compatible Kitty and Ghostty terminals.
- Unsupported rendering falls back to the supplied alternative text.
- Automatic graphics support is disabled for background workers and inside tmux or screen.
- `CLAUDE_CODE_FORCE_TERMINAL_IMAGES=1` overrides automatic capability detection; it does not add graphics support to an incompatible terminal.
- This is a plugin-interface capability, not a new command for previewing arbitrary files.

Evidence: New image validation, renderer, terminal probe, and environment override (search for `"Image props must be { source, columns, rows, alt }"`, `"kittyGraphics"`, and `"CLAUDE_CODE_FORCE_TERMINAL_IMAGES"`).

## Improvements


### Install a plugin while adding its marketplace

The interactive `/plugin install` command now accepts a marketplace source directly:

```text
/plugin install my-plugin --marketplace owner/repository
```

Claude Code checks the source, asks before adding the marketplace, and then takes you to the plugin review and installation flow. The option accepts a single plugin name; it cannot be combined with the existing `plugin@marketplace` naming form.

Evidence: New slash-command parser and marketplace confirmation flow (search for `"Usage: /plugin install <plugin> --marketplace <source>"` and `"Only add marketplaces you trust. You'll review the plugin and choose where to install it next."`).


### Batch artifact asset uploads [Gradual Rollout]

Where artifact assets are enabled, Claude can upload several files to one artifact under a single approval.

Details:

- The asset-upload input accepts `file_paths` with up to **25 files**, instead of one `file_path`.
- Supported batches include images, videos, PDFs, fonts, stylesheets, and scripts.
- Results distinguish successfully stored files from failed or uncertain uploads, so retries can target only the remaining files.
- Text files, symbolic or hard links, and files outside the working directory require individual calls.
- Script-based calls must continue using one `file_path` per call.

Example tool input:

```json
{
  "action": "upload_asset",
  "url": "<artifact URL>",
  "file_paths": ["./cover.png", "./demo.mp4"]
}
```

Evidence: New batch schema, validation, approval handling, and per-file results (search for `"file_paths"`, `"Assets uploaded:"`, and ``"`file_paths` cannot be used from a script"``).


### Expanded shared-artifact access [Gradual Rollout]

Artifact handling now recognizes shared artifacts that the user has permission to edit, including artifacts shared from another organization.

Details:

- An artifact read identifies edit access as `"writer"`; viewing or commenting access does not authorize updates.
- Cross-organization artifacts may be absent from listings, so their direct link may be needed.
- Copying assets or published files from another organization has an explicit approval path and requires server support.
- Asset copies must target an artifact in the user’s own organization.
- Cross-organization comment replies remain unavailable from Claude Code.
- Publish responses provide clearer information about who can open the artifact. Sharing itself still changes through the page’s Share menu.

Evidence: Shared-writer handling, cross-organization copy requests, and access messages (search for `"A shared artifact can be updated only"`, `"cross_org_ok"`, and `"Artifacts shared from another organization are not listed here yet"`).


### Artifact publishing prefers named icons

Artifact publishing now directs Claude to use a short generic `icon`, such as `"chart"` or `"calendar"`, and deprecates the emoji-based `favicon` field.

The `icon` field already existed in v2.1.274; this release changes the publishing guidance and removes the first-publish requirement for an emoji favicon. Legacy favicon input remains recognized, with guidance to use `icon` next time.

Publishing also gives clearer recovery instructions when a previously published source file is missing, helping Claude update the existing artifact instead of accidentally creating another one.

Evidence: Updated schema and publishing recovery messages (search for `"Deprecated; omit it. Use `icon`."`, `"Icon: the legacy `favicon` emoji was sent"`, and `"Recreate the file at this path, then publish again with that url"`).


### Confirm the account before saving a Cloud gateway login

When a gateway returns an email address, sign-in now shows that account and asks for confirmation before saving the login and applying its organization’s settings.

Signing out also attempts to revoke the gateway session and refresh token when a suitable revocation endpoint is available. If none is available, sign-out remains local to the machine.

Evidence: Account-confirmation state before credential persistence, plus gateway revocation on logout (search for `"Signed in to Cloud gateway as"`, `"Continue only if this is your account"`, and `"[gateway-logout]"`).


### Visible warnings for telemetry-header failures

A failure in the user-configured `otelHeadersHelper` now produces a visible warning explaining that telemetry is not being exported and pointing to `/status`.

The helper also distinguishes invalid JSON, invalid output shape, and non-string header values, making configuration problems easier to diagnose.

Evidence: Interactive warning and helper-output validation (search for `"otelHeadersHelper failed; telemetry is not being exported. See /status:"` and `"otelHeadersHelper did not return valid JSON"`).


### Clearer advisor-setting behavior

Advisor messages now explain when a conversation retains its already-declared advisor model until `/clear` or `/compact`, and when a changed setting applies to a new conversation. Where the current tool declaration supports it, turning the advisor on or off can still take effect immediately.

Evidence: Conversation-specific advisor status text (search for `"The current conversation keeps"` and `"turning the advisor on or off applies right away"`).


### Queued notifications reach additional hosted sessions

The existing `ReadNotifications` tool gains support for sessions using the REPL bridge, with buffering and delivery paths for incoming notifications. Notifications identify origins such as scheduled triggers and messages from another Claude session, and the CLI adds dedicated result rendering.

This extends an existing tool; `ReadNotifications` was already present in v2.1.274.

Evidence: Bridge eligibility, notification buffering, and result rendering (search for `"tengu_saffron_kite"`, `"[bridge:repl] Ingress queued_notification"`, and `"message from another session"`).


### Stricter file naming for plugin hook modules

Function-hook modules, their imported plugin files, and client UI modules must now use a recognized code-file extension. Accepted extensions include `.js`, `.mjs`, `.cjs`, `.ts`, `.tsx`, `.jsx`, `.mts`, and `.cts`.

Plugin authors should rename executable modules with unconventional suffixes and update their references. These modules are interpreted as ES modules regardless of suffix.

Evidence: Module-path validation and updated hooks schema (search for `"is not named like code and was not loaded"` and `"The module, and every file it imports from the plugin, is named like code"`).

## Bug Fixes

- **Memory sync recovers more cautiously from missing or unusable sync metadata.** Sync can pause while rebuilding its record of shared memory, preserve local files, and notify the session when synchronization resumes. Older local files absent from shared memory are held back from automatic upload until edited, reducing accidental restoration of memories deleted elsewhere. Evidence: search for `"memory store is off for now"`, `"They may be copies of memories another session deleted"`, and `"tengu_typed_koala"`.

- **Oversized search output is no longer liable to look like an empty successful search.** Ripgrep output collection handles truncation and allocation failures explicitly. When the output limit is reached before a complete result line, the error explains the problem and suggests a narrower search. Evidence: search for `"Ripgrep output passed the"`, `"RipgrepOutputTooLargeError"`, and `"Failed to collect ripgrep output:"`.

- **File-history migration avoids accepting incomplete backup copies.** When hard-linking a checkpoint fails, the fallback copies to a temporary file, checks its size, and then moves it into place, with retries for transient rename failures. Evidence: search for `"FileHistory: backup copy is incomplete"` and `"FileHistory: could not move the copied backup"`.

- **Advisor rejection can recover without failing the whole turn.** Recognized API errors saying the advisor is unavailable or invalid trigger a retry without it. The conversation records the refusal and explains that it continues without an advisor until `/clear` or `/compact`. Evidence: search for `"retry:advisor-entry-refused"` and `"The API refused the advisor for the current conversation"`.

- **Message Threads can fall back after an unrecognized HTTP 400.** A request carrying the message-threads header can be retried without that header, with a notice that Message Threads remains off for the session. Evidence: search for `"retry:tether-unrecognised-400"` and `"resending this turn stateless without the header"`.

- **Resumed permission requests can remain answerable after a timeout.** When enough information remains to present the pending request, the session holds it for an answer instead of rerunning the interrupted turn or retiring the request. This no longer depends on the previous hold/retire environment switches. Evidence: search for `"holding it answerable; not re-running, not retiring"` and compare the removed `"CLAUDE_CODE_HOLD_UNANSWERED_PARKED_PERMISSION"` and `"CLAUDE_CODE_RETIRE_UNANSWERED_PARKED_PERMISSION"` checks.

- **Cloud-to-local hook checks recognize more indirect execution paths.** The trust analysis now examines additional shell constructs, interpreter import paths, command wrappers, and Git environment changes that could execute files from a cloud-writable checkout. Commands the analysis cannot establish as safe follow the existing approval path. Evidence: search for `"it runs python in a mode that imports from the working directory first"` and `"it runs git with the repository's own hooks switched back on"`.

- **Plugin dependency installation avoids a Bun configuration execution path.** A Bun-based dependency install is skipped when a neighboring `bunfig.toml` could load an install-time security scanner. The diagnostic suggests removing that file or providing a `package-lock.json`. Evidence: search for `"Skipped: a bunfig.toml beside the bun lockfile can load code at install time"`.

## In Development

These changes are present in the source but are gated or incomplete. Their presence does not establish availability for every account.


### Direct npm plugin installation [In Development]

What: Install plugins directly from npm without first locating them in a separately configured marketplace.

Status: Feature-flagged; `tengu_plugins_npm_marketplace` defaults to false.

Usage when enabled:

```bash
claude plugin install '@scope/plugin@npm'
claude plugin install 'my-plugin@1.2.3@npm' --registry https://registry.npmjs.org
```

Details:

- Parses package names, versions, semver ranges, and distribution tags.
- Resolves registry metadata and verifies downloaded package integrity and identity.
- Records the resolved tarball and integrity for subsequent loading and updates.
- Applies managed plugin-source restrictions.
- Provides guarded archive extraction and avoids install scripts in the package-fetch path.
- Accounts without the rollout receive an explicit “not enabled” message.

Evidence: New install/load paths and default-off gate (search for `"tengu_plugins_npm_marketplace"`, `"Installing plugins straight from an npm registry"`, and `"--registry <url>"`).


### Plugin-install links [In Development]

What: A `claude-cli://install-plugin` link can open the marketplace-and-plugin installation flow.

Status: Feature-flagged; the link-origin installation path checks `tengu_amber_tollgate`, defaulting to false.

Example link shape:

```text
claude-cli://install-plugin?plugin=my-plugin&marketplace=owner/repository
```

Details:

- Validates plugin names, marketplace sources, and optional Git references.
- Presents confirmation before proceeding.
- When disabled, the CLI tells the user to type `/plugin install` themselves.
- The manually typed `--marketplace` workflow is available independently of this link gate.

Evidence: Deep-link parser and guarded confirmation flow (search for `"install-plugin"`, `"tengu_amber_tollgate"`, and `"Plugin install links are turned off"`).


### Resume interrupted background agents by messaging them [In Development]

What: Interrupting supported background agents can park them with progress preserved, allowing a later message to resume them.

Status: Feature-flagged; `tengu_zinc_harbor` defaults to false.

Details:

- Distinguishes agents that can be parked from tasks that must be stopped.
- Adds notifications telling users how to resume parked agents.
- Extends message-recipient guidance to background-agent names and IDs.

Evidence: Gated interruption branch and resume messaging (search for `"tengu_zinc_harbor"`, `"Progress is preserved; resume an agent by sending it a message"`, and `"Recipient: a background agent's name or agentId"`).


### AGENTS.md plugin refinements [In Development]

What: The existing experimental `agents-md` plugin gains more precise instruction loading.

Status: Feature-flagged; availability still requires `tengu_agents_md_mod`, whose default is false.

Details:

- `agents-fallback` now considers whether the project has its own CLAUDE.md.
- `both` avoids loading AGENTS.md content already imported or linked by CLAUDE.md.
- `none` removes project, local, and user instruction files while retaining managed instructions and memory.
- Instruction-file tracking follows session roots and forked agents more closely.

These are changes to infrastructure already present in v2.1.274, not the introduction of AGENTS.md support.

Evidence: Updated instruction-file processing and mode descriptions (search for `"tengu_agents_md_mod"`, `"projectInstructions"`, and `"the organization's managed CLAUDE.md and memory stay"`).


### Promotional offers and claim command [In Development]

What: Eligible accounts can receive promotional offers at startup or at a usage-limit screen, with a command to open the offer page.

Status: Feature-flagged and eligibility-dependent.

Details:

- Adds a hidden `/claim-credit` command.
- Offer content comes from `tengu_swift_lynx`; exposure also depends on `tengu_smooth_forest`, which defaults to false.
- Checks eligibility, whether the offer was already claimed, and organization policy.
- No particular credit amount or broadly available promotion is established by this code.

Evidence: Offer configuration, eligibility checks, and command registration (search for `"claim-credit"`, `"tengu_swift_lynx"`, `"tengu_smooth_forest"`, and `"Open the page of the offer shown at start-up"`).


### REPL variables surviving compaction [In Development]

What: Compaction summaries can describe retained REPL state and list variables still available afterward.

Status: Stubbed in this build.

Details:

- Adds summary formatting for preserved VM bindings.
- The controlling predicate returns false.
- The binding-list provider returns no value.
- The shipped CLI therefore does not establish usable REPL state retention across compaction.

Evidence: Summary text and its disabled call path (search for `"Your REPL VM state was kept across this compaction"` and `"replBindingsKept"`; the associated predicate returns `false`).

## Notes

This changelog compares **v2.1.274 → v2.1.275**, with substantive changes checked against the original split Bun modules. The bundled release-note text still begins with v2.1.274, so it is not presented as official highlights for this version.

For artifact integrations, prefer `icon` over the deprecated `favicon`. Plugin authors using function hooks should also check module filenames against the newly enforced code extensions.


Generated with:
- tool: `harness-investigations@3de596c-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.275.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.275.txt`
- source modules: `archive/claude-code/original/cli-v2.1.275.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
