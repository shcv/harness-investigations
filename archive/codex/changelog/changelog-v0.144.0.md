# Changelog for version 0.144.0

## Official Release Highlights

### Reset Credits: Type, Expiration, and Selection

What: When you hit a usage limit, the credit redemption picker now shows each available reset credit's type label and expiration timestamp, and lets you select a specific credit to redeem rather than always redeeming the first one.

Details:
- Credits are displayed with a human-readable scope label (e.g. the reset credit type) and their expiration time
- You can scroll the picker and choose which credit to apply, giving you control over which entitlement is consumed
- The underlying API call now passes the selected `credit_id` rather than always omitting it

Code references:
- `RateLimitResetScope`, `ResetCreditOption` in `codex-rs/tui/src/chatwidget/reset_credits.rs`
- `consume_rate_limit_reset_credit(credit_id: Option<String>)` in `codex-rs/tui/src/app/background_requests.rs`


### New `writes` App-Approval Mode

What: A new `"writes"` value for `AppToolApproval` allows declared read-only tool calls to proceed automatically while prompting for approval only when a tool attempts a write operation.

Usage:
```toml
[app]
tool_approval = "writes"
```

Or via the JSON-RPC config:
```json
{"tool_approval": "writes"}
```

Details:
- Sits between `"auto"` (approve everything) and `"prompt"` (approve everything): read-classified tools run without interruption, write-classified tools pause for human approval
- Full approval mode order: `"auto" | "prompt" | "writes" | "approve"`
- `AppToolApproval::Writes` is the new Rust enum variant handling this logic

Code references:
- `AppToolApproval::Writes` in `codex-rs/app-server-protocol/src/protocol/v2/config.rs`
- Schema: `codex-rs/app-server-protocol/schema/json/v2/ConfigReadResponse.json`
- TypeScript type: `codex-rs/app-server-protocol/schema/typescript/v2/AppToolApproval.ts`


### MCP Auth Elicitation Enabled by Default

What: MCP tools that require authentication can now trigger interactive auth flows without any experimental opt-in. Previously this required setting an experimental flag; it is now the default behavior.

Details:
- When an MCP server returns an auth-required error, Codex will surface an interactive prompt to the user to complete authentication
- The experimental gate has been removed; the behavior is unconditional
- Test coverage added in `mcp_auth_elicitation.rs` confirms elicitation fires by default

Code references:
- `codex_apps_auth_failure_requests_elicitation_by_default()` in `codex-rs/core/tests/suite/mcp_auth_elicitation.rs`


### Hosted Login: Runtime Auth and Success-Page Redirect

What: App-server hosts (operators embedding Codex in their own product) can now supply Codex authentication at runtime over a new `"headers"` auth mode, and can redirect users to a hosted success page after a successful login.

Details:
- New `AuthMode::Headers` variant: the host provides credentials via HTTP headers rather than the device-code or token flows
- `LoginAccountParams::Chatgpt` gains two new optional fields:
  - `use_hosted_login_success_page` — when `true`, successful login redirects to the operator's hosted page instead of returning to the Codex UI
  - `app_brand` — selects the login UI branding: `"codex"` or `"chatgpt"`
- `ExternalAuthBridge` in `app-server` implements `ExternalAuth` by wrapping a `CodexAuth` value delivered by the host at session start, enabling fully programmatic credential injection

Code references:
- `AuthMode::Headers` in `codex-rs/app-server-protocol/src/protocol/common.rs`
- `LoginAppBrand` enum in `codex-rs/app-server-protocol/src/protocol/v2/account.rs`
- TypeScript: `codex-rs/app-server-protocol/schema/typescript/AuthMode.ts`, `codex-rs/app-server-protocol/schema/typescript/v2/LoginAppBrand.ts`, `codex-rs/app-server-protocol/schema/typescript/v2/LoginAccountParams.ts`
- `ExternalAuthBridge` in `codex-rs/app-server/src/external_auth.rs`


### pnpm Global Install Detection

What: Codex now detects when it was installed via pnpm and uses `pnpm add -g @openai/codex` in diagnostics and update suggestions instead of npm/yarn commands.

Details:
- Detection uses the `CODEX_MANAGED_BY_PNPM` environment variable set by the pnpm install wrapper
- `InstallMethod::Pnpm` is the new variant in the install-method enum
- The `doctor` command and update flow both branch on this variant to emit the correct package manager command

Code references:
- `InstallMethod::Pnpm` in `codex-rs/cli/src/doctor.rs`
- Update command in `codex-rs/cli/src/doctor/updates.rs`


### Ultra Reasoning High-Concurrency Warning

What: When you select an Ultra reasoning model and have configured high multi-agent concurrency (8 or more threads), the TUI now shows a warning that concurrent agents on an Ultra model could increase your usage consumption rapidly.

Details:
- Threshold is 8 concurrent agents
- Warning is displayed inline in the model selection popup before you confirm the choice
- Gives users a chance to reconsider concurrency settings before committing to a potentially expensive run

Code references:
- `ultra_reasoning_concurrency_warning()` in `codex-rs/tui/src/chatwidget/model_popups.rs`


## Bug Fixes

- Compaction retry on retired model: When resuming a ChatGPT thread and the compaction step references a model that is no longer available, Codex now retries compaction with the currently selected model instead of failing. (`codex-rs/core/` compaction request retry path, PR #30319)

- Intel macOS Code Mode crash fixed: Release binaries on Intel macOS were missing a required V8 signing entitlement, causing Code Mode to crash. The entitlement is now included in the signing step. (PR #30953)

- Windows sandbox file deletion in writable roots: The Windows sandbox ACL configuration was preventing deletion of files inside declared writable root directories. The fix removes `FILE_DELETE_CHILD` from the shared write-allow mask and instead grants it per-descendant via ACL inheritance, which is the correct pattern for allowing delete operations. (`codex-rs/windows-sandbox-rs/src/acl.rs`, PRs #31138 and #31574)

- Terminal control sequence sanitization on paste: Pasting text containing ANSI/terminal escape sequences could corrupt TUI rendering or inject control characters into saved conversation history. Pasted text is now sanitized via `sanitize_user_text()` before it is accepted into the composer or stored. (`codex-rs/tui/src/bottom_pane/chat_composer.rs`, PR #31494)

- Auth refresh for long-running `codex_apps` sessions: The hosted `codex_apps` connector now refreshes its authentication token when it expires during a long-running session, preventing silent failures on extended sessions. (PR #31486)

- Responses WebSockets with system proxy: The low-latency Responses WebSocket transport now correctly routes through system proxies and respects custom certificate authorities. Previously, proxy settings were ignored for WebSocket connections. A new `OutboundProxyRoute` resolver maps `ws://`→`http://` and `wss://`→`https://` for proxy lookup before establishing the connection. (`codex-rs/http-client/src/outbound_proxy.rs`, PRs #31441 and #31622)


## Improvements

### Device-Code Login Phishing Warning Clarified

The warning shown during device-code authentication has been rewritten to be more actionable. It now reads: "Continue only if you started this login in Codex. If a website or another person gave you this code, cancel." — replacing the previous generic "Device codes are a common phishing target. Never share this code."

Code references: `codex-rs/login/src/device_code_auth.rs`


### Reviewer Preserved When Resuming Threads

When resuming a thread that had a designated reviewer, the reviewer assignment is now restored correctly rather than being reset to the default.

Code references: `codex-rs/` thread resumption logic (PR #30278)


### Amazon Bedrock GPT-5.6 Display Names

Amazon Bedrock model names now clearly label their GPT-5.6 family and variant in the model picker and diagnostics output.

Code references: PR #31636


### Plugin Namespace Resolution Performance

Plugin skill-loading on remote executors now resolves namespaces once per root instead of once per skill. This reduces redundant work during startup when many skills share a root namespace.

Code references: `codex-rs/core-plugins/` (PR #31348)


### `/review` Branch Picker Speed

The `/review` command's branch list is now populated using `git for-each-ref` instead of the previous approach, making it significantly faster and more reliable in repositories with large numbers of branches.

Code references: `codex-rs/tui/` review branch picker (PR #31464)


### Automatic Review Behavior

The auto-review flow now uses a more focused tool set and clearer prompting instructions, reducing noise and improving the quality of automated reviews.

Code references: PR #31480


### Tool Schema Compaction Threshold Increased

The threshold at which tool schemas are compacted before sending to the model has been raised, reducing unnecessary compaction on typical tool sets.

Code references: PR #31497


### Code Mode Uses Hosted Mode by Default

Code Mode now defaults to hosted mode. This changes the default execution path for code-mode sessions to use the hosted backend rather than the local executor.

Code references: `codex-rs/` code-mode default (PR #31500)


### Image Generation Extension Enabled by Default

The image generation extension is now active by default for all sessions rather than requiring explicit opt-in.

Code references: PR #31596


## In Development

### Extension-Owned Canonical Turn Items [In Development]

What: A new architecture for how agent activity is represented in the protocol — command execution, dynamic tool calls, hook prompts, sub-agent activity, collab tool calls, collab waits, and review mode transitions are now emitted as typed `CanonicalItem` variants owned by the extension layer rather than as ad-hoc legacy event structs.

Status: Infrastructure complete and merged; the migration from legacy event emission is in progress. Some legacy event paths have already been removed (`codex-rs/app-server/src/bespoke_event_handling.rs`); others remain.

Details:
- New item types: canonical command execution items, canonical dynamic tool call items, canonical hook prompt items, canonical sub-agent activity items, canonical collab tool call/wait items, canonical review mode items
- `ThreadItem::WebSearch` and `ThreadItem::ImageGeneration` now wrap shared types from the new `codex-extension-items` crate
- UUIDv7 is now used for generated item IDs, giving items monotonically ordered identifiers

Code references:
- `codex-rs/ext/items/` (new `codex-extension-items` crate)
- `codex-rs/app-server/src/bespoke_event_handling.rs`
- `codex-rs/app-server-protocol/src/protocol/v2/item.rs`


### Proxy-Aware WebSocket Client Crate [In Development]

What: A new `codex-websocket-client` crate provides a shared WebSocket connector that resolves system proxies and custom CAs before establishing connections.

Status: Crate added to the workspace and used for the Responses WebSocket fix. Intended as the standard WebSocket foundation for future connection points.

Details:
- `OutboundProxyRoute` enum: `TransportDefault | Direct | Proxy { url }` — represents the resolved proxy decision
- `HttpClientFactory::resolve_proxy_route()` handles the lookup, including scheme remapping for WebSocket URLs

Code references:
- `codex-rs/websocket-client/` (new crate)
- `OutboundProxyRoute` in `codex-rs/http-client/src/outbound_proxy.rs`


Generated with:
- tool: `harness-investigations@03136fb-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/codex/diff/v0.144.0.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.144.0.md`
