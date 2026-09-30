# Changelog for version 0.159.3

## Release Status

> **Not yet released:** `rust-v0.159.3` is present in Git, but no published GitHub Release was found at sync time. This may be an intermediate development snapshot or a release prepared ahead of publication.


## Summary

Compared with 0.159.2, this snapshot adds an optional account-security reminder to the interactive terminal UI. Eligible ChatGPT users can open security setup from the reminder, dismiss it, or continue working; the server controls whether it appears and what it says.

## Release Status

The source tag `rust-v0.159.3` exists, but no published GitHub Release was found when the sync ran. This changelog describes an intermediate development snapshot and does not establish availability of published binaries or release assets.

## New Features


### Account-security setup reminder

What: The terminal UI can display an account-specific security reminder with an action that opens setup in the browser.

Usage:

```bash
codex
```

When a reminder appears, press `1` to open its setup link, press `Esc` to dismiss it, or type to continue working.

Details:

- The reminder is new in this snapshot: the security-setup implementation and endpoint reference are absent from the `rust-v0.159.2` source.
- The client integration is active without a new experimental flag. Actual visibility depends on the server returning an eligible notice from `/wham/security-setup`; there is no new CLI command or configuration switch to force it.
- It applies to local workspaces using the `openai` provider and saved ChatGPT authentication. Remote workspaces, API-key authentication, externally supplied ChatGPT-token authentication, and FedRAMP accounts are excluded. The saved token must match the connected app-server’s ChatGPT authentication.
- Notice retrieval runs in the background with a three-second timeout. Unavailable, unsuccessful, absent, or invalid responses produce no reminder and do not block a turn.
- Dismissal survives thread navigation, reconnects, and repeated account notifications for the same account/user identity during the running CLI session. A fresh CLI session can show the reminder again; a verified identity change resets dismissal.
- Applicable account-usage banners take priority. The security reminder keeps its dismissal state separate from those banners.
- Account changes invalidate pending results, preventing an old account’s reminder from appearing after a switch.
- Setup links must use HTTPS on `chatgpt.com`, without embedded credentials or a non-default port. Notice text is length-limited and rejects control characters; the fetch does not follow redirects.
- The server supplies the title, description, action label, and destination. Daybreak, hardware-key, Persona, and deadline wording in test fixtures does not establish a published requirement or rollout date.

Code references:

- `security_setup::prefetch`, `Identity::from_auth`, and `Notice::valid` in `codex-rs/tui/src/security_setup.rs`.
- `ChatWidget::show_security_setup`, `ChatWidget::inherit_security_setup`, and `ChatWidget::invalidate_security_setup` in `codex-rs/tui/src/chatwidget/security_setup.rs`.
- Startup and reconnect integration in `codex-rs/tui/src/app/startup.rs` and `codex-rs/tui/src/app/reconnect.rs`.
- Account-change handling and `AppEvent::SecuritySetupLoaded` dispatch in `codex-rs/tui/src/app/app_server_events.rs` and `codex-rs/tui/src/app/event_dispatch.rs`.
- `ChatWidget::observe_backend_banner_view` and `ChatWidget::refresh_backend_banner_visibility` in `codex-rs/tui/src/chatwidget/backend_banners.rs`.


Generated with:
- tool: `harness-investigations@0de2653-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/codex/diff/v0.159.3.diff` (raw diff)
- release status: `unreleased Git tag; no published GitHub Release found at sync time`
