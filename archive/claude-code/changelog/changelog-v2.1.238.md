# Changelog for version 2.1.238

## Summary

This release adds secure dynamic-auth support for plugin archive downloads and new proxy-authentication controls for self-hosted runners. It also introduces substantial dark-launched artifact collaboration and cloud file-sync infrastructure, including runtime diagnostics and live artifact-room events.

## New Features


### Authenticated Plugin Archive Downloads

What: Plugin marketplaces and individual plugin entries can now supply static HTTP headers or a `headersHelper` command to obtain short-lived download credentials.

Usage:

```json
{
  "name": "private-plugin",
  "source": {
    "source": "url",
    "url": "https://plugins.example.com/private-plugin.zip"
  },
  "headersHelper": "./mint-plugin-download-token"
}
```

Details:

- `headersHelper` must print a JSON object of HTTP header names and values.
- The helper runs only during an explicit install or update from the plugin’s own details page; browsing a marketplace never executes it.
- Entries using a helper must set `"strict": false` and inline their manifest, so capabilities can be reviewed before the command runs.
- Managed policy, workspace trust, HTTPS-only sources, command changes, and unpinned helper-based archives are all checked before execution.

Evidence: Plugin schema description `"Command that prints a JSON object of HTTP headers for fetching this plugin's archive"` and validation `"an entry with headersHelper must inline its manifest so its capabilities can be reviewed before the command runs"`.


### Proxy Authorization for Self-Hosted Runners

What: Self-hosted runners can mint a fresh `Proxy-Authorization` value for each connection to an authenticated egress proxy.

Usage:

```bash
claude self-hosted-runner \
  --proxy-authorization-command './mint-proxy-token'
```

Or provide a file containing the header value:

```bash
claude self-hosted-runner \
  --proxy-authorization-file /run/secrets/proxy-authorization
```

Details:

- Requires `HTTPS_PROXY` or `HTTP_PROXY` to identify the upstream HTTP(S) proxy.
- The runner starts a local forwarding proxy, injects the authorization header for outbound CONNECT requests, and rewrites child-session proxy settings.
- The token value is not logged and can rotate because the command runs for each new proxy connection.
- This is currently unavailable on the `orchestrator` subcommand.

Evidence: Self-hosted-runner help for `"--proxy-authorization-command <shell command>"` and guard `"Not supported with the orchestrator subcommand yet."`


## Improvements


### Safer Plugin Installation and Updates

Plugin installs and updates now reject unsafe or stale dynamic-header configurations instead of running unexpected commands. Claude Code detects changed helpers or archive URLs, blocks helpers forbidden by managed settings, and requires explicit review before execution.

Evidence: `"The headersHelper command for ... changed since it was shown"` and `"The plugin was not installed or updated and the command was not run"`.


### More Explicit Cloud-Session File-Sync Eligibility

Cloud-session startup now evaluates whether a checkout can safely carry local changes, with specific explanations for oversized repositories, missing GitHub remotes, detached heads, divergence, and measurement timeouts.

Evidence: `"File sync is not offered for this checkout"` and telemetry gate `tengu_dir_sync_offer_probe`.


## Bug Fixes

- MCP and connector authentication now aborts rather than continuing with stale credentials when the signed-in account changes mid-reauthentication. Evidence: `"MCP tool call aborted: account changed during reauth"`.

- Plugin marketplace refreshes now avoid executing a `headersHelper` from an untrusted `--add-dir` declaration. Evidence: `"--add-dir declaration may not run commands"`.


## In Development

Features with infrastructure added but not generally enabled for ordinary CLI sessions.


### Artifact Runtime Diagnostics [In Development]

What: Artifact publishing gains a `verify` action that can retrieve browser-captured console output, uncaught errors, failed resource loads, and capability-call results for the published artifact version.

Status: Feature-flagged

Details:

- The action targets a supplied artifact URL or the session’s most recent publish.
- Diagnostics are owner-only.
- An empty result only means no viewer has loaded that version; it does not confirm a clean render.
- The feature is disabled by default through `tengu_osier_pylon_trace` unless `CLAUDE_CODE_ARTIFACT_VERIFY` enables it.

Evidence: `"verify" reads the runtime diagnostics` and gate `CLAUDE_CODE_ARTIFACT_VERIFY ?? it("tengu_osier_pylon_trace", !1)`.


### Live Artifact Rooms [In Development]

What: Published artifacts can declare a transient live room so browser viewers can send page events to Claude and Claude can broadcast events back with `room_send`.

Usage:

```text
Publish an artifact with capabilities.room, then use:
action: "room_send"
url: "<artifact URL>"
topic: "status"
data: { "state": "ready" }
```

Status: Dark-launched

Details:

- Messages are at-most-once broadcasts to current viewers and are not stored.
- Sending requires an interactive human approval surface; permission-check failures fail closed.
- The action is exposed only when the runtime’s artifact-room implementation reports itself enabled; builds without it report `"artifact rooms are not compiled into this build"`.

Evidence: `"room_send" broadcasts one live event to everyone currently viewing an artifact` and `"artifact rooms are not compiled into this build"`.


### Cloud Checkout File Sync [In Development]

What: Cloud sessions gain infrastructure to start from a measured local checkout and synchronize eligible working-tree changes rather than relying only on a remote clone.

Status: Feature-flagged

Details:

- Eligibility checks account for repository size, Git remote availability, branch state, remote divergence, and checkout measurement time.
- Bundle seeding is gated by `tengu_ccr_bundle_seed_enabled`.
- When the feature cannot safely carry local changes, Claude Code explains that the cloud session starts without them.

Evidence: `"Could not package your local changes for the cloud session"` and feature gate `tengu_ccr_bundle_seed_enabled`.


Generated with:
- tool: `harness-investigations@9e9bfae-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.238.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.238.txt`
