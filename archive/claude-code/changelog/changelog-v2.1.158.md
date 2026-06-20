# Changelog for version 2.1.158

## Summary
Claude Code 2.1.158 is a small patch release focused on Auto Mode compatibility outside Anthropic first-party backends. The main diff-backed user-facing change is a new `CLAUDE_CODE_ENABLE_AUTO_MODE` environment gate that lets non-first-party providers participate in Auto Mode paths, with special beta-header handling for Bedrock and other third-party transports.


### Experimental Auto Mode Enablement for Third-Party Providers

What: Auto Mode can now be enabled for non-first-party providers through a new environment variable.

Usage:
```bash
CLAUDE_CODE_ENABLE_AUTO_MODE=1 claude
```

Details:
- Previous builds only treated Auto Mode as available for `"firstParty"` and `"anthropicAws"` provider modes.
- 2.1.158 adds `CLAUDE_CODE_ENABLE_AUTO_MODE` as an override for other providers.
- The override does not make every model eligible: for non-first-party providers, Auto Mode still rejects `claude-opus-4-6` and models whose normalized names include `sonnet` or `haiku`.
- The environment variable is also added to Claude Code's known environment-variable allowlist, so it is recognized by the CLI rather than appearing only as an incidental `process.env` read.

Evidence: Third-party Auto Mode gate (search for `"CLAUDE_CODE_ENABLE_AUTO_MODE"`); model eligibility now checks `!cH8(q)` instead of only allowing `"firstParty"` / `"anthropicAws"`.


### Auto Mode Beta Routing for Bedrock and Other Third-Party Transports

What: When third-party Auto Mode is enabled, Claude Code now routes the Auto Mode beta marker through the request shape expected by the active transport.

Details:
- For Bedrock, the Auto Mode AFK beta can be sent through `body.anthropic_beta`.
- For other supported third-party providers, the same beta can be sent through the normal betas header path.
- This appears tied to the new `CLAUDE_CODE_ENABLE_AUTO_MODE` gate, so users should treat it as experimental provider compatibility rather than a broad public Auto Mode launch.

Evidence: Bedrock-specific routing (search for `"auto-mode 3P: sending afk-mode beta '"` and `"to bedrock via body.anthropic_beta"`); generic third-party routing (search for `"via betas header"`).


### Auto Mode Availability Notifications Use the Notification API

What: Auto Mode gate notifications now have a direct `addNotification` path instead of only mutating the notification queue through app-state updates.

Details:
- The hook that revalidates Auto Mode availability now obtains `addNotification` and passes it into the gate-update helper.
- When a gate message is produced, the helper can call the notification API directly using the existing `auto-mode-gate-notification` key.
- This should make Auto Mode availability warnings more reliable when model/provider changes invalidate Auto Mode.

Evidence: Auto Mode gate notification delivery (search for `"auto-mode-gate-notification"`); unavailable-mode warning path (search for `"auto-mode-unavailable"`).


## Notes
No new slash commands, CLI flags, settings-schema descriptions, or user-facing release-note text were found in the filtered diff or string literal diff. Most remaining changes are version/build metadata updates from `2.1.157` to `2.1.158`, internal minified-name churn, or non-user-facing refactors.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.158.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.158.txt`
