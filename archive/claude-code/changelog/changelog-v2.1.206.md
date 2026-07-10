# Changelog for version 2.1.206

## Summary

This release introduces the Claude in Chrome browser tool integration with a full interactive setup flow, adds three new artifact template skills (dashboard, data-table, explainer) with Chart.js chart rendering, and ships an `EndConversation` tool gated to certain models. Several internal improvements land for plugin binary provisioning, code review skill effort levels, command lifecycle events, and OAuth error handling.


## New Features


### Claude in Chrome Browser Tools Setup

What: A new interactive setup flow lets Claude offer to use your Chrome browser during tasks, installing the Claude in Chrome extension and establishing a live browser connection without leaving the terminal.

Details:
- When Claude needs browser automation and the extension isn't installed, an upsell prompt appears (gated by `tengu_chrome_install_upsell`). Options: install now, skip for now, or "don't ask again."
- The install wizard walks through two steps—"Install the extension" and "Connect to Chrome"—with a live status that updates as each completes.
- If the connection stalls, Claude displays a check message and offers "Keep waiting" or "Continue without browser tools."
- Once connected, the browser tools stay enabled for future sessions. Run `/chrome` anytime to manage the connection or reconnect.
- Seven Chromium-family browsers are detected: Chrome, Brave, Arc, Edge, Chromium, Vivaldi, and Opera.
- Enterprise/managed sessions with a `deniedMcpServers` policy skip the upsell automatically; bypass-permission mode also suppresses it.

Evidence: Setup UI strings (search for `"Setting up Claude in Chrome"`, `"Claude wants to use your browser"`, `"Finish setup in Chrome"`). Browser profile detection (search for `"google-chrome"` in the browser catalog). Auto-enable flag: `tengu_chrome_auto_enable`. Upsell gate: `tengu_chrome_install_upsell`.


### EndConversation Tool [Gradual Rollout]

What: A new built-in tool that allows Claude to end the current conversation. It is strictly reserved for sustained, repeated abusive behavior directed at the assistant, or when the user explicitly asks for a demonstration.

Details:
- Only available on select models: `claude-opus-4-8`, `claude-sonnet-5`, `claude-fable-5`, `claude-mythos-5`.
- Not enabled by default—gated by a server-side feature flag.
- The tool requires that a prior warning was issued in the same conversation before it will actually end the session. If called without a prior warning already on record, Claude is instructed to re-read the guidance and try again.
- Calling the tool in a background fork (e.g. memory consolidation tasks) does nothing; the fork is told to return and state its welfare concern in its output instead.
- Self-harm, mental health crises, and harm-to-others situations explicitly prohibit any use of this tool.
- When triggered in a non-interactive (`-p`) session, the process exits with `gracefulShutdown`.

Evidence: Tool description (search for `"end the conversation — only for sustained user abuse"`). Confirmation message (search for `"Claude has ended this chat."`). Background fork guidance (search for `"this tool does nothing here: it can end neither the main conversation"`). Model list: `xXh` array (search for `"claude-opus-4-8"` near the `"mythos"` entry in the EndConversation initializer).


### Artifact Template Skills — Dashboard, Data Table, Explainer

What: Three new built-in skill templates for publishing polished HTML artifacts directly from Claude Code.

Details:

**artifact-dashboard** — creates a dashboard with KPI tile cards, a primary chart (line, bar, or donut), and a breakdown table. The template uses Claude Design System token values for light and dark mode. A Chart.js runtime is injected at publish time for bar/donut charts; a built-in SVG fallback handles the standard time-series case without any external dependency.

**artifact-data-table** — creates a sortable, filterable table for exploring tabular datasets (CSVs, query results, record lists). Data is embedded as JSON; the renderer handles sort direction, numeric formatting, missing-value rules, and a live row count. Up to ~several thousand rows supported.

**artifact-explainer** — creates a step-by-step concept walkthrough or PR/architecture tour. Two flavors: "numbered steps" (default, for concept explainers—each step pairs prose with an SVG diagram) and "sections" (for codebase tours where code blocks carry more weight). Includes slot guidance for title, lede, steps/sections, and a recap.

Evidence: Dashboard skill description (search for `"Create a dashboard artifact — KPI tiles, a primary time-series chart"`). Data table skill (search for `"Create an interactive data-table artifact"`). Explainer skill (search for `"Create an explainer artifact — a step-by-step conceptual walkthrough"`). Template publish instruction (search for `"Publish a dashboard Artifact from a template"`).


### Chart.js Runtime for Dashboard Artifacts

What: Published dashboard artifacts now support Chart.js-rendered bar and donut charts in addition to the existing SVG line-chart fallback.

Details:
- At publish time, a Chart.js bundle is injected between `<!-- chart-runtime -->` and `<!-- /chart-runtime -->` sentinel comments in the HTML.
- The runtime reads a JSON spec embedded in a `<script type="application/json" data-chart-runtime>` element and renders into `#primary-chart`.
- Dark mode is handled natively: colors are resolved from CSS custom properties at render time and the chart re-renders on OS theme changes and explicit `data-theme` attribute flips.
- Safety checks refuse to inject a bundle that contains `</script` or the sentinel strings themselves.
- The `tengu_pewter_canteen` feature flag disables this injection; without the flag the Chart.js runtime loads from the bundled asset path.

Evidence: Sentinel strings (search for `"<!-- chart-runtime -->"` and `"<!-- /chart-runtime -->"`). Bundle path constant (search for `"/$bunfs/root/chart.umd.min.js"`). Safety check (search for `"bundle contains the chart-runtime sentinel"`).


## Improvements


### Code Review Skill — New Effort Levels and Context-Aware Effort

A new `xhigh` effort level was added to the code review skill: 10 inline finder angles, a sweep pass, and up to 15 findings. A `low` effort level was added as well (single diff pass, no verify, ≤8 findings, 2 turns total).

The `getEffort` callback for skill commands now receives the tool-use context as a second parameter, allowing the review skill to factor in session state when selecting the effort tier for a given invocation.

Evidence: Effort labels (search for `"xhigh effort → 10 inline angles → dedup (no verify) → sweep → ≤15 findings"` and `"low effort → 1 diff pass → no verify → ≤8 findings"`). Context parameter addition in `getEffort` call.


### Command Lifecycle Events — Extended States

SDK clients and remote transports now receive three additional `command_lifecycle` event states:

- `queued` — emitted when an inbound message enters the command queue.
- `cancelled` — emitted when a command is removed by `cancel_async_message`, caught by a pending cancel before dispatch, or consumed into a turn that was subsequently aborted or hit a hard failure.
- `discarded` — emitted when the session ends with the command still in the queue.

The event description was also updated to clarify that commands enqueued without a uuid (e.g. the one-shot `-p "prompt"` path) emit no lifecycle events.

Evidence: New state enum (search for `"queued"` near `"started"`, `"completed"`, `"cancelled"`, `"discarded"` in the `command_lifecycle` schema). Updated event description (search for `"Fate of a queued command"`).


### Git Push Permissions — Smarter Remote Detection

When Claude Code auto-generates `git push` permission rules, it now reads `remote.pushDefault` from the repo's git config. If a configured push remote exists and has a valid name, it's included alongside `origin`. This prevents permission prompts on repos that push to a non-`origin` remote by default.

Evidence: New helper (search for `"remote.pushDefault"` in the added `Kfm`/`Yfm` functions). Permission rule builder (search for `"git push -u"` near the `rwn` function).


### Plugin Binary Provisioning — Validation and Bare Name Placement

Two improvements to how plugin binaries are handled:

**MCP server config validation**: When loading a plugin, Claude Code now reads `.mcp.json` and `plugin.json` and validates that any MCP server `command` referencing `${CLAUDE_PLUGIN_ROOT}/bin/<name>` maps to a binary that is either declared in the plugin's `binaries` map or derivable from a declared entry. A warning is emitted for mismatches to help plugin authors catch typos before distribution.

**Bare name placement**: After downloading platform-specific binaries (e.g. `mytool-x86_64-apple-darwin`), the provisioner now creates a hard link with the architecture suffix stripped (e.g. `mytool`) so the binary is accessible under its bare name. This is skipped on Windows and when multiple declared entries would collide on the same bare name.

**Mismatch removal**: If a file already in `bin/` doesn't match the expected SHA-256 from the manifest, it is now removed and re-downloaded rather than left in place.

Evidence: Config validator (search for `"is not a shipped file, a declared binaries entry, or"` and `"fail to start. Check for a typo against the \"binaries\" map in plugin.json"`). Bare placement (search for `"bare placement bin/"` and `"multiple declared entries derive bin/"`). Mismatch removal (search for `"removed bin/"` and `"it is not the artifact pinned by the manifest"`).


### OAuth Expired Session — Specific Error Type

Expired OAuth refresh tokens now raise a named `OAuthRefreshDeadError` (message: "OAuth refresh token is no longer valid; run /login to re-authenticate") rather than failing with a generic network or auth error. This error is classified as `auth_error` in the turn error classification path, producing more accurate telemetry and better user-facing guidance.

Evidence: Error class (search for `"OAuthRefreshDeadError"`). Classification (search for `"if (e instanceof u5t) return "auth_error"`). Auth path check (search for `"if (!A && !m && !qbt(p).value && OGt()) throw new u5t()"`).


### Refusal Fallback — Per-Category Routing and Catch-All Override

The model refusal fallback system now supports per-category routing. When a refusal carries an API category, a route table is consulted:

- For the default model set: `cyber` → `claude-opus-4-8`.
- For an extended model set: `bio` and `cyber` → `claude-opus-4-8`.

The category must resolve to an available armed fallback model, or routing is declined (with a new `tengu_refusal_fallback_route_declined` telemetry event).

A new env var `CLAUDE_CODE_REFUSAL_FALLBACK_CATCH_ALL` overrides this routing logic: when set to a truthy value, any refusal routes to the catch-all armed fallback model regardless of category.

The `model_refusal` event description was updated to clarify it fires only when no retry runs (no fallback model configured, or per-category routing declined the retry).

Evidence: Route table (search for `"cyber"` near `"bio"` and `"claude-opus-4-8"` in the `g_t` initializer). Env var (search for `"CLAUDE_CODE_REFUSAL_FALLBACK_CATCH_ALL"`). Updated event description (search for `"per-category routing declined the retry"`).


### Bridge Session Grouping

Bridge sessions now carry a `bridgeSessionGroupingId` field that is propagated through session handshakes and resume operations. This allows the remote transport to correlate sessions that belong to the same logical group. The session env var `CLAUDE_BRIDGE_REATTACH_GROUPING` is cleaned up on subprocess spawn.

Evidence: Field addition (search for `"bridgeSessionGroupingId"`). Env var cleanup (search for `"CLAUDE_BRIDGE_REATTACH_GROUPING"`).


### Observer Agent Reattach

When a task that had an observer agent is resumed, the system now checks for a prior observer sidecar and reattaches to it if the observer type matches and the sidecar is still live. If the prior sidecar reports `observerStopped`, the reattach is blocked rather than starting a fresh observer. An unreadable sidecar falls back to a fresh observer under a new ID.

Stopping a task that is an observer now correctly cleans up the observer entry rather than attempting a generic task kill.

Evidence: Reattach logic (search for `"[agentObserver] reattach: observer sidecar unreadable — fresh under a new id"`). Observer stop check (search for `"[agentObserver] resume re-arm failed for '"`). Observer tombstone (search for `"observer tombstone"`).


### Health Check — Bloated Memory File Detection

The `/doctor` health check description was updated to include "bloated memory files" as a detectable issue alongside unused extensions, slow hooks, and permission problems.

Evidence: Updated description (search for `"duplicated or bloated memory files"`).


### Screen Reader Mode — Activation Source Reporting

The screen reader mode status string now includes how the mode was activated when the source is known (e.g. `[Screen Reader Mode: on via <source>]`). Previously it always reported `[Accessible screen reader mode: on]`.

Evidence: New function (search for `"[Screen Reader Mode: on via"` near `"[Screen Reader Mode: on]"`).


### Model Catalog — Tiered Pricing Resolution

Model pricing entries can now reference a named pricing tier from a central catalog rather than embedding all cost values directly. If a model's `pricing` field is a string, it is resolved against the catalog's `pricing_tiers` map. This makes it possible to update pricing for a group of models in one place.

Validation is stricter: a catalog entry that references a tier but is missing `cache_write_5m`, `cache_read`, or `web_search` cost fields now throws a named error rather than silently producing wrong costs.

Evidence: Tier resolver (search for `"model catalog entry has incomplete pricing"`). Validation (search for `"baked entries need the full ModelCosts shape"`). Catalog ID check (search for `"regenerate with 'bun run generate:model-catalog'"`).


## Bug Fixes

- Synced file directory creation now retries on ENOENT with a small delay rather than giving up immediately. This fixes a race where the parent directory hadn't been created yet by a concurrent process. (Search for `"working_sync_parent_absent"` in the mkdir retry logic.)

- Observer tasks are now excluded from the normal task-started notification path, preventing spurious "task started" events from firing for internal observer sidecars. (Search for `"if (BL(e)) return"` in the task-started notification guard.)

- The `observer-ref` entry type is now included in the `route-by-agent` routing branch in session entries, ensuring observer context is properly routed to the correct agent. (Search for `"observer-ref"` in the fork context routing switch.)

- Promotional list price strikethrough in model descriptions is now gated on subscription level in addition to the promo flag, preventing the strikethrough from appearing for users to whom it wouldn't apply. (Search for `"fLt.promoListPrice && MDr() && ht.level > 0"` in the model description formatter.)


## In Development


### /artifacts Command [In Development]

What: A built-in `/artifacts` command to browse, open, copy URLs for, and delete your published and shared artifacts — all from within the terminal.

Status: Disabled — `isEnabled: () => !1`. Full UI and API implementation is present.

Details:
- Lists up to 200 artifacts fetched from `GET /api/frame/frames?limit=200`.
- Shows title, shared/owned label, last-updated time, and view count.
- Arrow keys navigate the list; `enter`/`o` opens in browser, `c` copies the URL, `d` prompts to delete (yours only), `r` refreshes.
- Delete calls `DELETE /api/frame/<slug>` and removes the entry from the list on success.
- Empty state: "No artifacts yet. Publish one with the Artifact tool."

Evidence: Command definition (search for `"Browse your published and shared artifacts"` near `isEnabled: () => !1`). Delete API call (search for `"Artifact deleted"` and `"Couldn't delete artifact (HTTP"`). Gallery fetch (search for `"/api/frame/frames?limit=200"`).


## Notes

The Claude Design MCP server (`claude_design`) was removed from the set of built-in first-party MCP servers. The `CLAUDE_CODE_ENABLE_DESIGN_MCP` env var and `tengu_omelette_whisk` feature flag that controlled it are also removed. The `/design` skill and command remain; they now rely solely on externally configured MCP connections rather than an auto-provisioned built-in server.

Evidence: Removed constants (search for `"https://api.anthropic.com/v1/design/mcp"` — present only in the REMOVED section of the diff).


Generated with:
- tool: `harness-investigations@03136fb-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.206.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.206.txt`
