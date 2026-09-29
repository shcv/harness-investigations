# Changelog for version 2.1.285

## Summary

Version 2.1.285 adds a desktop launch flag, command-line plugin configuration, and administrator controls over permitted API providers. It also introduces background-command deadlines, improves reopening running background sessions, and strengthens sandbox, plugin, and hook handling. MCP task execution and a per-session memory toggle have new infrastructure, but are not generally enabled.


## New Features


### Launch Claude Desktop from the command line

What: The new `--desktop` flag opens Claude Desktop directly, optionally continuing an existing conversation.

Usage:
```bash
claude --desktop
claude --desktop --continue
claude --desktop --resume <session-uuid>
```

Details:

- Supported on macOS and Windows x64.
- Requires signing in with a Claude account.
- `--continue` selects the latest session in the current directory; `--resume` requires a session UUID.
- Prompts and piped input are not supported: enter your prompt in the app after it opens.
- Incompatible combinations, including noninteractive execution, background execution, worktrees, and restricted modes, produce explicit errors.

The existing `/desktop` command predates this release; the startup flag is new.

Evidence: CLI option registration and desktop launch validation (search for `"--desktop"` and `"Open in the Claude Desktop app instead of the terminal"`).


### Configure installed plugins without opening an interactive session

What: `claude plugin configure` displays a plugin’s declared options and accepts configuration values through standard input.

Usage:
```bash
claude plugin configure my-plugin@marketplace
claude plugin configure my-plugin@marketplace --json
claude plugin configure my-plugin@marketplace --values-stdin < values.json
```

Details:

- Use the plugin’s full installed ID when necessary.
- Input must be a JSON object containing single-line string values.
- Omitted options retain their existing values.
- Values are validated against the plugin’s declared configuration.
- Standard input is limited to 256 KB.
- Restart Claude Code after saving to apply the configuration.

Interactive plugin configuration already existed; this release adds the standalone CLI command.

Evidence: Command registration and configuration handler (search for `"configure <plugin>"`, `"--values-stdin"`, and `"Configuration saved. Restart Claude Code to apply it."`).


### Restrict API providers through managed settings

What: Administrators can use `allowedProviders` to specify which API providers Claude Code may contact.

Usage: For example, in administrator-managed settings:
```json
{
  "allowedProviders": ["bedrock", "vertex"]
}
```

Details:

- Supported entries include `anthropic`, `bedrock`, `vertex`, `foundry`, `anthropicAws`, `mantle`, `customEndpoint`, and `gateway`.
- Disallowed providers are refused at startup, during login, and when contacting the API.
- An omitted list leaves providers unrestricted; an empty list permits none.
- Custom endpoints require an explicitly permitted and pinned endpoint in the appropriate managed configuration.
- A machine-level list cannot be widened by server-managed settings.
- A provider-restricted machine refuses `claude ssh` tunnels whose destination it cannot verify.
- This controls provider destinations, not every aspect of cloud credentials, tenancy, proxies, or TLS configuration.

Evidence: Managed-settings schema and enforcement errors (search for `"allowedProviders"` and `"API provider not allowed by managed settings"`).


### Disable built-in web fetching with an environment variable

What: `CLAUDE_CODE_DISABLE_WEB_FETCH` disables the built-in WebFetch tool and the web-fetch agent route.

Usage:
```bash
CLAUDE_CODE_DISABLE_WEB_FETCH=1 claude
```

Details:

- Both direct WebFetch availability and the agent-based fetching path check this variable.
- This is a tool-level control; it does not establish a general network block for shell commands or other tools.

Evidence: WebFetch and fetch-agent enablement checks (search for `"CLAUDE_CODE_DISABLE_WEB_FETCH"`).


## Improvements


### Background shell commands now have execution deadlines

Background shell tasks can now be stopped automatically when their background timeout expires, with a notification explaining the stop.

Details:

- For `run_in_background`, `timeout` specifies the background execution limit.
- With ordinary defaults, the limit is 30 minutes and the maximum is two hours.
- Existing Bash timeout environment settings can raise these defaults and limits.
- The deadline enforcement gate, `tengu_cosmic_shore`, defaults to enabled.
- The MCP-serving path explicitly disables this background-deadline behavior.

For a command expected to run longer, ask Claude to supply an appropriate timeout when starting it.

Evidence: Background task timer and tool instructions (search for `"tengu_cosmic_shore"`, `"background deadline"`, and `"With it, \`timeout\` limits how long the command may run in the background"`).


### Resume a session that is still running in the background

Interactive resume paths can now attach to an existing background session instead of merely telling you that it is already running.

Usage:
```bash
claude --resume <session-id>
```

Details:

- A supplied ordinary text prompt can be delivered to the background session before opening it.
- Delivery failures distinguish queued, unconfirmed, and failed messages.
- Prompts beginning with `/` or `!` are not forwarded through this route.
- Requires an interactive terminal and a background session that can be attached.
- Controlled by `tengu_resume_open_live_bg`, which defaults to enabled.

Evidence: Resume-to-attach handoff (search for `"Opening the background session"`, `"Sending your prompt to the background session"`, and `"tengu_resume_open_live_bg"`).


### Inspect plugin data usage

The existing plugin listing command can now measure plugins’ saved data directories.

Usage:
```bash
claude plugin list --json --data-size
claude plugin list --json --data-size my-plugin@marketplace
```

The optional plugin argument limits measurement to one installed plugin. This measures saved plugin data, rather than merely reporting the installation location.

Evidence: Plugin listing option and directory measurement (search for `"--data-size [plugin]"` and `"Measure each installed plugin's saved data directory"`).


### Configure bundled MCP servers during plugin installation

The existing installation-time `--config` option now accepts configuration declared by bundled `.mcpb` servers.

Usage:
```bash
claude plugin install my-plugin@marketplace \
  --config server-name.option-name=value
```

A bare option name is accepted when it can be resolved unambiguously. Ambiguous names and options that are not declared produce specific errors.

Evidence: Expanded installation option and bundled-server key validation (search for `"--config <key=value>"`, `"a bundled .mcpb server's own user_config field"`, and `"--config key is ambiguous between bundled servers"`).


### More control over model-access fallback and request retries

New environment controls let users adjust model-access recovery and qualifying nonstreaming timeout retries.

Usage:
```bash
CLAUDE_CODE_DISABLE_MODEL_ACCESS_FALLBACK=1 claude
CLAUDE_CODE_SKIP_MODEL_ACCESS_MEMORY=1 claude
CLAUDE_CODE_NONSTREAMING_TIMEOUT_RETRIES=0 claude
```

Details:

- `CLAUDE_CODE_DISABLE_MODEL_ACCESS_FALLBACK` disables the model-access fallback path.
- `CLAUDE_CODE_SKIP_MODEL_ACCESS_MEMORY` bypasses the new persisted provider-access memory used by Bedrock and Vertex model probing.
- `CLAUDE_CODE_NONSTREAMING_TIMEOUT_RETRIES` supplies a separate retry budget for qualifying nonstreaming timeout failures; it does not replace every retry policy.

Evidence: Fallback selection, provider-access persistence, and request retry handling (search for the three environment-variable names and `"model-access.json"`).


### Stronger precedence for administrator sandbox restrictions

Project settings have less ability to expand access when higher-trust settings impose sandbox restrictions.

Details:

- Under an administrator sandbox mandate, project settings cannot contribute extra writable paths or the relevant network and socket allowances.
- Project-configured proxies cannot replace the filtering proxy when trusted restrictions apply.
- With `network.allowManagedDomainsOnly`, only managed settings may supply replacement proxy settings.
- Read exceptions that resolve through unsafe links into denied locations can be withheld and checked again before commands run.

This can change the behavior of projects that previously relied on repository-local sandbox exceptions.

Evidence: Effective sandbox configuration and grant filtering (search for `"admin sandbox mandate"`, `"a project may not replace the filtering proxy"`, and `"re-linked after the config build"`).


### Hardened cloud uploads replace the legacy fallback on macOS and Linux

Cloud uploads on macOS and Linux no longer honor `CLAUDE_CODE_LEGACY_BUNDLE` as a way to select the older upload implementation.

Unsupported repository layouts now receive more specific explanations, including problematic `.git` links or pointer files and repositories borrowing object storage.

If an upload is refused, the error recommends an ordinary checkout or clone. Where supported, pushing the branch and starting from GitHub avoids the upload requirement.

Evidence: Platform selection and repository validation (search for `"CLAUDE_CODE_LEGACY_BUNDLE is not honoured on macOS and Linux"` and `"An older upload method, which took more layouts, is retired"`).


### Clearer feedback for concurrent artifact edits

When the publishing service reports that a publish was merged over a newer artifact version, Claude now receives a clear explanation of that merge.

The response identifies other changed or removed files when available and directs Claude to refresh stale copies before editing them. This documents the service’s result; it does not mean that every conflicting edit can be merged automatically.

Evidence: Publish-result rendering and stale-file handling (search for `"Merged over a newer version"` and `"read again any file of this artifact"`).


### More actionable GitHub access errors

Cloud-session startup now distinguishes several organization-level GitHub access failures:

- IP allowlist restrictions.
- Missing organization SSO authorization.
- Identity-provider Conditional Access restrictions.

Each case supplies a relevant recovery message instead of treating the problem as an undifferentiated repository-access failure.

Evidence: Cloud-session error mapping (search for `"Your GitHub organization has an IP allowlist"`, `"Your GitHub organization requires single sign-on"`, and `"Conditional Access policy"`).


## Bug Fixes

- Incomplete hook output is no longer accepted as a clean approval or other permissive verdict when standard output closes prematurely or leaves a partial JSON response. Search for `"hook stdio closed before end-of-stream"` and `"refusing to honor the suspect capture"`.

- MCP stdio connections can recover from servers that acknowledge subscription listening but then stall or exit during discovery. Claude retries once with a legacy handshake within the remaining connection budget. Search for `"mark3labs/mcp-go"` and `"restarting it once with the legacy handshake"`.

- Plugin installation detects when another installed plugin already owns a destination folder, avoiding replacement of that plugin’s files. Search for `"plugin not installed: another installed plugin has one of its folders"`.

- Plugin and marketplace cloning now explicitly reads the user’s Git SSH command and variant settings. Failures to read them explain the fallback and, where relevant, recommend a usable `CLAUDE_CODE_TMPDIR`. Search for `"core.sshCommand and ssh.variant"` and `"claude-ssh-config-"`.

- Repeated OAuth callbacks received after a sign-in code has arrived are acknowledged without restarting the exchange. Search for `"Sign-in is already finishing. You can close this window."`.

- Attachment approval rejects changes to the file list that cannot safely be applied to the prepared request, asking for a fresh call with the intended attachments. Search for `"changed the files to attach, which cannot be applied"`.


## In Development


### Server-side MCP task execution [In Development]

What: MCP tools can return a server-side task handle so long-running work can continue asynchronously and deliver its result later.

Status: Feature-flagged; `tengu_mcp_tasks` defaults to false.

Details:

- Adds an execution path for servers advertising task support.
- Tracks task status, retrieves final results, and supports cancellation.
- Includes reconnection handling that refuses to reuse a task against a differently configured server.
- Background results can arrive through task notifications.
- Worker wake-up behavior has an additional gate, `tengu_mcp_task_worker_wake`, also defaulting to false.

MCP task protocol definitions already existed in 2.1.284. The substantive addition is the CLI execution and lifecycle integration, not the protocol names themselves.

Evidence: Task-enabled tool calls and task watcher (search for `"Calling MCP tool (task path)"`, `"tengu_mcp_tasks"`, and `"was reconfigured to a different transport"`).


### Per-session auto-memory control [In Development]

What: New `/memory` interface scaffolding would let users turn auto-memory off for one session separately from the global preference.

Status: Stubbed in this build.

Details:

- Adds a `session-auto-memory` settings row and a session-specific change handler.
- The row’s backing module and state remain null, and its availability check returns false.
- The pre-existing `/pause-memory` command also remains disabled; it should not be advertised as newly usable.
- No new working invocation or launch date is established by this source.

Evidence: Conditional memory settings row and disabled availability check (search for `"session-auto-memory"`, `"AUTO_MEMORY_SESSION_ROW_LABEL"`, and `"pause-memory"`).


## Notes

- Compared **2.1.284 → 2.1.285**, with substantive changes checked against the original split Bun module sources.
- For long-running background commands, review timeout expectations before upgrading.
- On macOS/Linux, scripts relying on `CLAUDE_CODE_LEGACY_BUNDLE` need to use a supported checkout or a GitHub-backed cloud-session source.
- Administrators adopting `allowedProviders` should account for custom endpoint pinning and the restrictions on tunneled sessions.
- No official release notes were supplied. This changelog describes CLI source changes; server rollout status and separate Desktop, VS Code, and SDK releases are not established by this comparison.


Generated with:
- tool: `harness-investigations@829d4f2-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.285.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.285.txt`
- source modules: `archive/claude-code/original/cli-v2.1.285.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
