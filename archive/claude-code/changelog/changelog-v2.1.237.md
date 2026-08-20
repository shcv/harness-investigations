# Changelog for version 2.1.237

## Summary

This release adds a built-in Concise output style for shorter, result-first Claude responses. It also expands Remote Control’s harness-event infrastructure with authenticated provenance handling and a gated event-polling tool for supported remote sessions.

## New Features


### Concise Output Style

What: A built-in response style that makes Claude lead with the result, avoid narration, and keep routine replies brief without reducing task thoroughness.

Usage:

```text
/config
```

Choose `Preferred output style`, then select `Concise`.

Details:

- Answers simple requests tersely and avoids “Let me…”-style preambles.
- Preserves full detail for requested explanations, errors, security warnings, and destructive-action confirmations.
- The selected style is saved as the local `outputStyle` setting.

Evidence: Built-in style named `"Concise"` with the description `"Claude responds tersely, leading with results and skipping preamble and narration"`; the configuration UI labels this choice `"Preferred output style"`.


## Improvements


### Verified Human Messages in Bound Slack Threads

Remote sessions can now distinguish server-verified messages from the bound Slack thread from bot or peer-agent content. This strengthens consent and permission handling when a Claude session is connected through Slack.

Evidence: Uses the marker `"[Verified human message relayed from the bound Slack thread]:"` and explicitly treats bot-authored Slack posts as unable to establish user intent or consent.


### Event Provenance Validation for Remote Control

The existing Remote Control `poll_event` protocol now accepts and carries source provenance, including authority, sender ID, and verified sender text. Invalid provenance is rejected, and sender text is retained only when its escaped form is actually embedded in the event.

Evidence: Validation message includes `"authority, when present, one of human-principal|human-other|peer-agent|world-event"`; rejected sender text logs `"sender_text dropped from provenance"`.


## In Development

Features with infrastructure added but not generally available in ordinary CLI sessions.


### Harness Event Polling [In Development]

What: A read-only tool that lets an enabled remote-session harness wait for and deliver queued events to Claude.

Status: Feature-flagged

Details:

- The tool waits for harness events, returns event envelopes, and reports the number of delivered and remaining wake events.
- It is enabled only when `CLAUDE_CODE_POLL_EVENTS` is true and the session is a qualifying Remote Control session (`CLAUDE_CODE_REMOTE` with no `CLAUDE_CODE_ENVIRONMENT_KIND`).
- It is limited to the main thread and depends on a host harness that provides the event queue, so setting the environment variable alone does not create a usable general CLI feature.

Evidence: Tool description `"Wait for pending harness events"`; gated by `CLAUDE_CODE_POLL_EVENTS`; rejects agent-thread use with `"Poll is available on the main thread only"`.


Generated with:
- tool: `harness-investigations@1a100db-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.237.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.237.txt`
