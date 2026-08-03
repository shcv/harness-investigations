# Changelog for version 2.1.221

## Summary

This release adds sandbox credential masking and opt-in MCP protocol negotiation, while making some plugin installs immediately usable. It also ships substantial—but currently gated or disabled—Artifact collaboration, workshop, and prototyping infrastructure.

## New Features

### Sandbox credential masking

What: Sandboxed commands can receive a sentinel-substituted credential file while Claude Code’s proxy restores the real credential only for configured outbound hosts.

Usage:

```json
{
  "sandbox": {
    "credentials": {
      "files": [
        {
          "path": "~/.netrc",
          "mode": "mask",
          "injectHosts": ["api.example.com"]
        }
      ]
    }
  }
}
```

Details:

- `mode: "mask"` supports whole-file masking or targeted replacement with an `extract` regular expression.
- Structured files such as `.netrc`, JSON, and YAML can retain their non-secret content when `extract` captures only credential values.
- Masking requires appropriate sandbox/proxy configuration; without TLS termination, the proxy cannot restore credentials on HTTPS egress.
- On macOS and Windows, file masking currently degrades to `deny`; it is most useful on Linux and WSL.

Evidence: Credential-file schema adds `"Access mode for this path. \`deny\` blocks reads inside the sandbox; \`mask\` shows sandboxed commands a sentinel-substituted copy"` and the `injectHosts` proxy behavior.


### Opt-in MCP protocol negotiation

What: Claude Code can negotiate a modern MCP protocol revision instead of always using legacy behavior.

Usage:

```bash
MCP_PROTOCOL_NEGOTIATION=auto claude
```

Details:

- Set the variable to `auto` to enable negotiation on supported transports.
- Set it to `legacy` to retain the previous behavior.
- Unsupported transports remain on legacy mode, and invalid values are ignored with a warning.
- The default path is still guarded by transport-specific rollout flags, so explicit opt-in is the reliable way to request negotiation.

Evidence: New `MCP_PROTOCOL_NEGOTIATION` handling accepts `"legacy"` or `"auto"` and emits `"MCP_PROTOCOL_NEGOTIATION=<value> is invalid; expected 'legacy' or 'auto' — ignoring"`.


### Immediate plugin activation

What: Plugin installation can now activate newly installed plugins in the current session when runtime loading succeeds.

Usage:

```text
/plugin
```

Details:

- Install a plugin through the `/plugin` interface.
- If it can be loaded immediately, Claude Code reports that it is active without requiring a restart.
- If immediate activation is unavailable, Claude Code still tells you to use `/reload-plugins`.
- Plugins disabled by default or by settings remain disabled until explicitly enabled.

Evidence: Installation results now include `"Plugin is now active."` alongside the existing `"Run /reload-plugins to apply."` fallback.

## In Development

Features with infrastructure added but not yet enabled. These are shipped dark and may become available in future versions.


### Artifact comment collaboration and live editing [In Development]

What: Published Artifacts gain infrastructure for reading comment threads, posting replies, applying live edits, and automatically responding to human-activated threads.

Status: Feature-flagged.

Details:

- The Artifact tool has new `comments`, `reply`, `live-edit`, `watch`, and `unwatch` actions.
- Automatic handling is deliberately constrained: a human must activate the comment thread, automatic edits are restricted to artifact writers, and replies are subject to rate limits and permission checks.
- Live edits take effect immediately and are separately approval-gated because they can affect artifact viewers.
- The Artifact surface itself is gated by `tengu_cobalt_plinth`; automatic-comment behavior also depends on the Artifact runtime being enabled.

Evidence: New action descriptions include `"Read the comment threads on a published artifact"`, `"Post a reply comment on a thread of a published artifact"`, `"Apply live edits to an already-published artifact page"`, and `"Automatic replies or edits on artifact"`.


### Interactive Artifact workshops [In Development]

What: A `/workshop` skill is prepared to publish an evolving design document where readers choose decisions on the Artifact page and Claude Code incorporates them into subsequent revisions.

Status: Feature-flagged.

Details:

- The workflow presents decision blocks, republishes the updated document, and offers a “Start building” transition when decisions are complete.
- It requires multiple gated conditions, including `tengu_gable_onyx_sluice` and Artifact availability, so it is not generally available yet.

Evidence: The built-in skill is named `"workshop"` and describes `"Build a design together with the user, one decision at a time"`.


### Working Artifact prototypes [In Development]

What: A `/prototype` skill is included for turning an idea into a self-contained, interactive Artifact proof of concept.

Status: Disabled/stubbed.

Details:

- The skill is user-invocable in its registration and includes instructions to build and publish an interactive prototype.
- Its enablement function, however, currently returns `!1`, so the command is not available to users.
- Related plan-mode prompt text exists, but no active user-facing prototype workflow is enabled by this build.

Evidence: Search for `"Prototype an idea as a working Artifact"`; its registration uses `isEnabled: Lgo`, while `function Lgo() { return !1; }`.


Generated with:
- tool: `harness-investigations@3c40d58-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.221.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.221.txt`
