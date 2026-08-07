# Changelog for version 2.1.225

## Summary

This release improves Artifact comment handling and strengthens Remote Control reliability. It also adds a server-gated device bridge for discovering and messaging Remote Control sessions on other machines, while making auto-mode safety refusals clearer and less prone to misleading retry behavior.

## Improvements

### Navigate long Artifact comment lists

What: Claude can now read a specific Artifact comment thread directly and continue a truncated comment listing with a cursor.

Usage:

```text
Ask Claude to read comments on an Artifact URL. If the result says more threads were omitted, ask it to continue using the provided cursor; it can also read one thread by its thread_id.
```

Details:

- `comments` now accepts `thread_id` to fetch one thread.
- When a listing reaches its size limit, Claude can continue from the returned `cursor`.
- This avoids repeatedly re-reading the first page of a large discussion.

Evidence: Artifact tool documentation adds `"read just this one thread"` and `"comments only: continue a listing"`.


### Clearer cross-session message policy explanations

What: When incoming messages are held, Claude now explains whether an organization policy or repository setting caused it.

Details:

- Managed `crossSessionInbound: "hold"` policies explicitly direct users to their administrator.
- Repository settings are identified as stricter local policy and explain that user-level `accept` cannot override them.
- Invalid `crossSessionInbound` values are tolerated as unset rather than breaking settings parsing.

Evidence: policy messages reference `"Your organization's managed settings set \"crossSessionInbound\" to \"hold\""` and `"This repository's settings set \"crossSessionInbound\" to \"hold\""`.


### More resilient Remote Control authentication and recovery

What: Remote Control now handles expired, rejected, or changed credentials more deliberately, with actionable recovery guidance.

Details:

- Login failures direct users to `/login` before reconnecting Remote Control.
- A saved credential will not silently replace a user-supplied `CLAUDE_CODE_OAUTH_TOKEN` after an OAuth 401.
- Remote Control retries transient server-unreachable failures and can re-enable itself after a fresh credential for the same account is detected.
- Unarchive failures caused by stale elevated authentication are distinguished from ordinary failures.

Evidence: search for `"OAuth 401: keeping the user-supplied CLAUDE_CODE_OAUTH_TOKEN"`, `"Remote Control server unreachable — retrying"`, and `"run /login to restore Remote Control"`.


### Safer Artifact auto-replies

What: Experimental Artifact comment auto-replies now avoid posting a duplicate response when another Claude session has already answered the same summon.

Details:

- The existing auto-reply flow recognizes a `"summon_answered_elsewhere"` result.
- When an Artifact was automatically edited but a second session already replied, Claude reports that the Artifact may have changed and directs review to the existing thread response.

Evidence: search for `"Reply not posted: this summon was already answered in another session"` and `"The artifact WAS changed — review the change"`.

## Bug Fixes

- Auto mode now treats a safety-filter refusal as a distinct no-verdict result instead of feeding it into the normal denial-counter path. It fails closed, provides retry guidance, and does not encourage rewriting an action to evade the refusal. Evidence: `"Auto mode classifier request refused by the safety safeguard"` and `"exempt from the denial counter"`.

- Remote Control messages are now described accurately as cross-session messages from another Claude session rather than as user prompts on the receiving session. Evidence: `"marked as from another Claude session, not from its user"`.

## In Development

Features with infrastructure added but not yet enabled. These are shipped dark and may become available in future versions.


### Remote Control device bridge [In Development]

What: Claude Code includes a device bridge that can expose a connected device’s runtime details and make Remote Control sessions on other machines discoverable and addressable by name.

Status: Feature-flagged

Details:

- The bridge registers a `get_device_info` tool that reports platform, architecture, Claude Code version, and device name.
- When connected, agent discovery can include Remote Control sessions on other machines; messages are explicitly labelled as cross-session messages.
- The bridge requires first-party OAuth, remote-session policy permission, organization and account identifiers, and the server-controlled `tengu_violin_wood` gate. The gate returns false if unavailable, so this is not generally enabled by default.

Evidence: device registration calls `tengu_violin_wood` (search for `"tengu_violin_wood"`); the new agent-list description names `"your Remote Control sessions on other machines"`; the device tool says `"Returns runtime environment details for this device"`.


Generated with:
- tool: `harness-investigations@ab2803c-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.225.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.225.txt`
