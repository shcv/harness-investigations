# Changelog for version 2.1.195

## Summary

This is a large release centered on three themes: a fully implemented enterprise cloud gateway login UI with TLS certificate pinning and OAuth device flow, WebSocket support in the Monitor tool, and organization-enforced effort level caps. The release also bundles the `claude gateway` server binary with its OIDC SSO and Postgres spend-limit infrastructure.


## New Features


### Gateway Login UI with TLS Certificate Pinning

The enterprise gateway login flow now has a complete interactive UI instead of returning `null` for the `gateway_setup` state. Connecting to a cloud gateway walks through URL validation, private-network DNS checks, OAuth device authorization, a browser-based sign-in step, and TLS certificate pinning — all in the terminal.

First connection to a gateway presents a trust prompt:

```
Trust gateway corp-gateway.example.com?

You haven't connected to this gateway before. Once trusted, it
can push settings to this machine that execute commands and
change your environment. Only continue if this is your
organization's gateway.

Certificate fingerprint (SHA-256): a1b2c3d4e5f6...
[Yes, trust this gateway]  [No, cancel login]
```

On subsequent connections, if the certificate has changed, you see a warning asking you to confirm the rotation with your administrator before proceeding.

Details:
- Gateway URL is normalized: `http://` upgrades to `https://` unless localhost
- The gateway hostname is DNS-resolved and must be on a private network (10.x, 172.16–31.x, 192.168.x, etc.) — public addresses are blocked with an actionable error
- HTTP proxies are also validated to be on private ranges, with instructions for `NO_PROXY` exemptions
- TLS fingerprints are persisted to local storage; a changed fingerprint triggers a second trust confirmation rather than a silent connection
- Credentials (JWT access token + optional refresh token) are stored in secure storage after successful login
- If `CLAUDE_CODE_USE_GATEWAY` is set in a non-interactive context, the error message now reads "Cloud gateway token expired — refresh ANTHROPIC_AUTH_TOKEN and restart" (rather than prompting to run `/login`)

Evidence: Trust prompt UI (search for `"You haven't connected to this gateway before"`), DNS validation (search for `"Gateway hosts must be on your organization's private network"`), TLS pin mismatch (search for `"gateway TLS certificate does not match the pinned fingerprint"`)


### Monitor Tool: WebSocket Support

The Monitor tool now accepts a `ws` parameter to stream events from a WebSocket endpoint directly, without needing a shell command like `websocat`.

Usage:
```
Monitor({
  ws: {url: 'wss://events.example.com/stream', protocols: ['v1']},
  description: 'deploy events',
})
```

Details:
- Each text frame becomes one notification event
- Binary frames are reported as `[binary frame, N bytes]` rather than passed through
- Socket close ends the watch with the close code surfaced
- Errors are surfaced before close
- Same rate-limiting as bash-based monitors — a firehose will be suppressed and eventually stopped
- WebSocket URLs must be valid ASCII `ws://` or `wss://` with no userinfo or whitespace
- The `ws` and `command` parameters are mutually exclusive
- SSRF protection: private/link-local/cloud-metadata addresses are blocked; `sandbox.network.allowManagedDomainsOnly` and `deniedDomains` rules apply
- Compliance taint (organizations with arbitrary URL egress disabled) prevents WebSocket monitors

Evidence: New `MonitorWsTask` task type (search for `"monitor_ws"`), precondition error class (search for `"MonitorWsPreconditionError"`), schema description (search for `"WebSocket to open. Each text frame is an event"`)


### Enterprise Gateway Server (`claude gateway`)

The `claude gateway` command now ships with the CLI binary and provides a full enterprise authentication and telemetry gateway. This is for organizations that want to proxy Claude Code traffic through their own infrastructure.

Details:
- Configured via a YAML file: `claude gateway --config <path>`
- OIDC SSO: supports Google, Azure AD, and any OpenID Connect provider via `oidc.discovery_url`
- Google Workspace groups support via Admin SDK for role-based access control
- Device authorization flow for browser-based login
- Postgres backend: `store.postgres_url` required (the old `dev:` SQLite mode was removed)
- Database schema includes: `spend` (usage metering), `spend_limits` (per-user/group/org caps), `kv` (key-value store), `principal_emails` (identity cache), `admin_audit` (audit log)
- OTEL telemetry forwarding with `telemetry.forward_to` configuration
- WebSocket monitoring endpoint for real-time event streaming
- SSRF protections: blocks cloud metadata endpoints (169.254.169.254), validates proxy hosts
- Requires the native binary install (`https://claude.ai/install.sh`); the npm package does not include it

Evidence: Gateway splash banner (search for `"│ Claude Code Gateway │"`), Postgres URL requirement (search for `"must be postgres:// or postgresql://"`), OIDC config (search for `"oidc.discovery_url"`)


## Improvements


### Organization-Enforced Effort Level Caps

Organizations can now restrict which effort levels users can select for specific models. When you request an effort level above your org's limit, Claude Code automatically falls back to the highest permitted level and notifies you.

```
Effort 'max' exceeds your organization's limit for claude-opus-4-8; using 'high'.
```

The `/effort` help text now reflects only the effort levels available to you. If higher levels are blocked, you see:

```
Higher effort levels are restricted by your organization.
```

Ultracode (xhigh + dynamic workflow) is also subject to org restrictions: "Ultracode runs at xhigh effort, which is restricted by your organization for [model]."

Evidence: Effort cap check (search for `"exceeds your organization's limit for"`), restriction notice (search for `"Higher effort levels are restricted by your organization"`)


### TLS Error Guidance for Private CA and Self-Signed Certificates

When the gateway's TLS certificate cannot be verified, the error message now includes specific remediation steps:

```
Could not verify the gateway's TLS certificate. If your gateway uses a
private CA or self-signed certificate: Claude Code reads your OS trust
store by default on the native binary and Node ≥22.15, so if the CA is
already installed there, upgrade to a current runtime. Otherwise set
NODE_EXTRA_CA_CERTS to the CA certificate PEM file before starting —
e.g. `export NODE_EXTRA_CA_CERTS=/path/to/ca.pem` — or add it under
`env.NODE_EXTRA_CA_CERTS` in your user settings (~/.claude/settings.json).
```

Evidence: TLS helper (search for `"Could not verify the gateway's TLS certificate"`)


### Improved Code Review Workflow

The built-in workflow-backed code review now deduplicates findings by (file, line) location before the verification step, then produces a ranked, capped findings report. The previous version verified every raw candidate independently; now findings that point to the same location are pooled first so the verifier processes each distinct location once.

Before: "One independent verifier per candidate — CONFIRMED / PLAUSIBLE / REFUTED"
After: "One independent verifier per distinct (file, line) location across the pooled candidates, then a ranked, capped findings report"

Evidence: Updated description string (search for `"one independent verifier for every distinct (file, line) location across the pooled candidates"`)


### `claude mcp login --no-browser` for SSH Environments

MCP server authentication now has an SSH-friendly mode. When you cannot open a browser from a remote session, pass `--no-browser` to get a callback URL you can paste manually:

```bash
claude mcp login <name> --no-browser
```

Evidence: New tip string (search for `"add --no-browser to paste the callback URL manually over SSH"`)


### `/config key=value` Inline Settings

A new tip explains that `/config` accepts inline `key=value` pairs to set panel settings without opening the menu:

```
/config key=value sets panel settings (model, theme, verbose, output style, …) inline — no need to open the panel.
```

Evidence: New tip string (search for `"/config key=value sets panel settings"`)


### Permission Rules: Tool Parameter Matching Tip

A new tip explains that deny/ask permission rules can match specific tool input parameters:

```
Deny and ask rules can match a tool input parameter — e.g., deny Agent(model:opus)
or ask Bash(run_in_background:true) — so that specific pattern is auto-handled
without prompting each time.
```

Evidence: New tip string (search for `"deny Agent(model:opus) or ask Bash(run_in_background:true)"`)


### Unicode-Aware Word Counting for Voice Input

Voice input auto-submit (which fires when a dictated phrase reaches 3 words) now uses Unicode-aware word segmentation via `Intl.Segmenter`. This improves accuracy for non-Latin scripts where whitespace-based splitting undercounts words.

Evidence: New word count function (search for `"isWordLike"`)


### Plugin Binary Downloads

Plugin and skill manifests now support a `binaries` field that declares SHA256-pinned native binaries to download into `bin/` at install time. The key is the binary's basename (with target triple encoded in the name); the value is the expected SHA256 hash.

```yaml
binaries:
  my-tool-x86_64-unknown-linux-gnu:
    sha256: "abc123..."
```

Evidence: New schema field description (search for `"sha256-pinned files to fetch into bin/ at install time"`)


### Network Sandbox Domain Enforcement

The sandbox network policy now evaluates `sandbox.network.allowManagedDomainsOnly` and `sandbox.network.deniedDomains` when the Monitor tool opens a WebSocket or when other network checks run. If a domain is denied, you see:

```
X is in sandbox.network.deniedDomains
```

If managed-domains-only mode is active and the domain isn't in the policy allowlist:

```
sandbox.network.allowManagedDomainsOnly is set and X is not in the policy allowlist
```

Evidence: Domain check functions (search for `"is in sandbox.network.deniedDomains"`)


### Structured Model Catalog

Model metadata is now stored in a validated, structured catalog rather than scattered across individual lookup tables. The catalog covers all available models with their provider IDs (Anthropic, Bedrock, Vertex, Foundry, Mantle, Gateway), capabilities (`effort`, `max_effort`, `xhigh_effort`, `adaptive_thinking`, `context_management`, `fast_mode`, `lean_prompt`), context window sizes, knowledge cutoffs, image limits, and default effort levels.

Current family aliases: `opus` → `claude-opus-4-8`, `sonnet` → `claude-sonnet-4-6`, `haiku` → `claude-haiku-4-5`, `fable` → `claude-fable-5`.

Evidence: Catalog initialization (search for `"Generated by \`bun run generate:model-catalog\`"`)


## Bug Fixes

- Gateway session reconnect no longer showed a stale "run /login" prompt when operating in headless `CLAUDE_CODE_USE_GATEWAY` mode; now correctly says "refresh ANTHROPIC_AUTH_TOKEN and restart" (search for `"Cloud gateway token expired"`)

- Writing to `adopt.json` directly is now blocked by the file write permission checker with a clear error. The `adopt.json` file is the background fork handoff carrier managed by the harness, and writing to it would corrupt the adopt mechanism. (search for `"adopt.json is a code-execution surface for the fork"`)

- The `defaultPermissionMode` badge in the subagent/tool defaults UI no longer appeared when `permissionMode` was `"default"` — it only shows now when a non-default mode is set (search for `"r !== \"default\""`)

- Computer use lock acquisition now handles the `rfo()` single-instance case correctly, preventing a stale lock check from blocking (search for `"computeruse_lock_acquire"`)

- MCP server "Re-authenticate" hint now appears correctly: the auth status check for SSE/HTTP MCP servers was refined to use the consolidated `_In()` helper (search for `"lost authentication · open /mcp and select Re-authenticate"`)

- Interrupted response recovery now correctly captures and replays the partial text that was being streamed when the stream was cut (search for `"Continuing an interrupted response. Text before the interruption:"`)

- The todo tip ("A todo list tracks multi-step work so you can see progress…") was removed from the tips system. It was triggering for multi-step tasks even when the todo workflow wasn't applicable.


## Notes

The `dev:` store backend for `claude gateway` has been removed. If you were running a gateway with the SQLite development store, migrate to Postgres: set `store.postgres_url` in the gateway config. Error shown on startup if the old key is used:

```
`dev:` was removed — the gateway is Postgres-only. Set store.postgres_url
```

The `CHANGELOG v2.1.195` is referenced in the source for a deprecation of internal `__.*` identifier patterns used in some gateway/daemon contexts. This affects operators implementing custom gateway or daemon integrations; no user-facing change.


Generated with:
- tool: `harness-investigations@0c752ef-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.195.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.195.txt`
