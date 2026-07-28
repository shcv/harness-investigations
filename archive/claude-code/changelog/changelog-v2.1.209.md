# Changelog for version 2.1.209

## Summary
This release adds Artifact runtime capabilities: a feature-gated system that lets published Artifact pages call the user's connected claude.ai data sources (MCP connectors) live at view time, rather than baking static data into the page at publish time. Additionally, several long-standing restrictions on background sessions have been lifted — model switching, usage-consent flows, and `/login` prompts are no longer blocked in background sessions, and Trusted Device enrollment is no longer required for Remote Control.

## New Features


### Artifact Runtime Capabilities (MCP) [Gradual Rollout]

What: Published Artifact pages can now declare runtime capabilities — starting with `mcp`, which lets the page invoke the user's claude.ai connectors at page-open time rather than embedding static data at publish time.

Details:
- Pass `capabilities: { mcp: { servers: [...] } }` to the Artifact tool to declare which connectors the published page may call
- The page calls connectors via `window.claude.mcp`; the platform serves typed definitions (`.d.ts`) for the current runtime contract that must be read before writing any `window.claude.mcp` call
- A new `artifact-capabilities` skill is available; Claude must load it before declaring any capability or writing `window.claude.*` code — it delivers the typed call definitions, connector routing guidance, and manifest rules
- Connector tools appear in your tool list as `mcp__<connector>__<toolName>`; set `server` to the `<connector>` segment (everything between `mcp__` and the next `__`)
- Only claude.ai connectors are valid as runtime capability sources — locally-configured MCP servers are not
- Omitting `capabilities` on a redeploy carries the stored declaration forward unchanged; passing `{}` explicitly clears all declared capabilities; passing a non-empty object is a full set declaration (anything stored but not restated is revoked)
- Moving a republished artifact to a different runtime contract version is a deliberate gesture — pass `contract: 'latest'` to upgrade or a specific version to pin
- In hermetic/CI sessions where connectors are not loaded but `$CLAUDE_CODE_OAUTH_TOKEN` is set, the connector list can be fetched via Bash: `curl -H "Authorization: Bearer $CLAUDE_CODE_OAUTH_TOKEN" <BASE_API_URL>/v1/mcp_servers?limit=1000`
- The Artifact tool prompt now appends a "Runtime capabilities" paragraph when the feature is active, and the frontend-design skill gains a "Live data via connected sources" section
- The type definitions cover only the call envelope — they do not encode a connector tool's argument names or result shape; never publish a page that calls a connector tool without having observed a real request/response pair for that tool in the session

Status: Gradual Rollout — gated by `tengu_cloth_snorkel` feature flag or `CLAUDE_CODE_ARTIFACT_MCP` environment variable (both default to disabled)

Evidence: Artifact capabilities skill registration (search for `"Runtime capabilities for published Artifacts"`) — enabled by `n4y()` which returns `sS.CLAUDE_CODE_ARTIFACT_MCP ?? Qe("tengu_cloth_snorkel", !1)`

## Improvements


### Background Sessions: Model Switching Restrictions Lifted

What: Background sessions can now freely switch models, including models that require usage-credits consent, and can open the interactive model picker without hitting a hard block.

Details:
- Previously, opening the model picker in a background session immediately returned: "Can't open the model picker in a background session — use `/model <name>` to switch this session's model." This block is removed
- Background sessions attempting to switch to a model requiring consent no longer see: "Switching to this model needs usage-credits consent. Run /model from an interactive terminal to see and answer the consent prompt." That path now proceeds to the normal consent flow
- The message "You are already on the highest Max subscription plan. For additional usage, run /login from an interactive terminal to switch to an API usage-billed account." is also removed from background session code paths
- The background-session-specific `/login` block ("Can't run /login in a background session — log in from a regular interactive terminal (`claude`), then respawn this job.") is gone
- Plan upgrade prompts that previously instructed users to run `/login` from an interactive terminal ("to upgrade to Max, then run /login from an interactive terminal to use your new plan") are no longer gated on session type

Evidence: Background-session model-picker guard removed (search for `"Can't open the model picker in a background session"` — absent from v2.1.209) — variables `c6_`, functions `l6_` and `m1o`


### Background Sessions: Trusted Device Enrollment No Longer Blocks Remote Control

What: Organizations with a Trusted Devices requirement for Remote Control no longer block unenrolled background sessions; the enrollment check has been removed from the Remote Control entry path.

Details:
- The previous behavior surfaced: "Your organization requires Trusted Devices for Remote Control, but this device is not enrolled. Run `/login` from an interactive terminal to enroll this device, then retry."
- This guard was removed from the Remote Control session entry point (`JDH` gate in function `PNp`); execution proceeds to the next gate (`qpa` check) regardless of device enrollment state

Evidence: Trusted Device guard in Remote Control flow removed (search for `"Trusted Devices"` — absent from v2.1.209) — function `PNp`


### Refusal Fallback: Latch Rearming Across Sessions

What: The refusal fallback latch — which tells the server that a request is being retried after a content refusal — is now rearmed automatically when existing conversation messages contain cyber-category refusals, ensuring retry requests carry the correct tracking header even when the latch was not set in the current session.

Details:
- New function `XNt` scans conversation messages for `model_refusal_fallback` system messages with `apiRefusalCategory === "cyber"` that were not neutralized by a fork; when found, it arms the latch with the original request ID
- `XNt` is invoked at the start of the main agent loop, subagent message handler, and the interactive chat loop — covering all entry points where messages may arrive with pre-existing refusals
- New HTTP headers are now sent on retried requests: `x-cc-fallback-latched-by` (carries the original request ID), alongside companion headers `x-cc-fallback-from-model`, `x-cc-fallback-category`, `x-cc-fallback-trigger`, and `x-cc-original-request-id`
- Header value is validated to printable ASCII (max 255 chars) before transmission
- Latch state (`refusalFallbackHeaderArmed`, `refusalFallbackLatchOriginRequestId`) is properly reset on session clear and when a fork session is entered
- The `latchActive` signal now includes the new armed-header state alongside the existing fallback-occurred flag

Evidence: New refusal fallback headers (search for `"x-cc-fallback-latched-by"`) — function `kgt` arms the latch; `XNt` handles rearming; state reset in `kH` and `b9o`


Generated with:
- tool: `harness-investigations@d5cccf8-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.209.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.209.txt`
