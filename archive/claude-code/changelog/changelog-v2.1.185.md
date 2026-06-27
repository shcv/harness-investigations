# Changelog for version 2.1.185

## Summary

This release improves the messaging shown when the API stops responding during a
session and enables thinking token count reporting for all Claude.ai users who
have extended thinking active.

## Improvements

### Clearer API stall messaging

When Claude Code is waiting on a stalled API call it now shows "Waiting for API
response" instead of "No response from API". The retry countdown text also
changed from "· Retrying in" to "· will retry in", matching a lowercase,
conversational style consistent with the rest of the status line.

The old phrasing implied the API had given up entirely. The new phrasing makes
clear the request is still in flight and a retry is coming.

Evidence: stall status component (search for `"Waiting for API response"`)


### Thinking token count available to all Claude.ai users

The `thinking-token-count-2026-05-13` API beta is now sent for every first-party
(Claude.ai) session with a model that supports extended thinking. Previously this
beta header was only sent when the server-side `tengu_chert_bezel` feature flag
was active, so most users did not receive thinking token counts in API responses.

With this change, any Claude.ai user who has extended thinking enabled will
automatically receive thinking token count data in responses — no feature flag
opt-in required.

This has no effect on users connecting via API key directly, Bedrock, or Vertex;
those authentication modes are unchanged.

Evidence: beta header enablement changed from `ct("tengu_chert_bezel", !1)` to
`Ir() === "firstParty"` (search for `"thinking-token-count-2026-05-13"`)


Generated with:
- tool: `harness-investigations@0c752ef-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.185.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.185.txt`
