# Changelog for version 0.142.5

## Official Release Highlights

This is a targeted security/privacy patch. The only user-facing change is the removal of a trace-level log line that was writing the full body of every outgoing Responses WebSocket request — including user prompts and context — to the trace log.

## Bug Fixes

- Prevented full Responses WebSocket request payloads from being written to trace logs. In `send_websocket_request()`, the call `trace!("websocket request: {request_text}")` was removed along with its `use tracing::trace` import. Previously, enabling `RUST_LOG=trace` (or an equivalent tracing filter) would cause the complete JSON body of every outgoing WebSocket request to be recorded, potentially capturing sensitive prompt content. (`send_websocket_request` in `codex-rs/codex-api/src/endpoint/responses_websocket.rs`)


Generated with:
- tool: `harness-investigations@03136fb-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/codex/diff/v0.142.5.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.142.5.md`
