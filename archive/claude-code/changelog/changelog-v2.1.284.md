# Changelog for version 2.1.284

## Summary

Compared with 2.1.283, this release adds Sonnet 5.5 to the bundled model catalog and certificate-based authentication for enterprise gateways. It separates Ultracode from reasoning effort, adds one-time approval for reads outside working directories, fixes terminal-wide MCP reconnection, and strengthens sandbox and workspace-trust checks.


## New Features


### Sonnet 5.5 model support

What: The CLI now recognizes Sonnet 5.5, including provider-specific identifiers and model capabilities.

Usage:

```bash
claude --model claude-sonnet-5-5
```

Details:

- The bundled catalog changes the default first-party `sonnet` alias from Sonnet 5 to Sonnet 5.5.
- Adds provider mappings and the Vertex region override `VERTEX_REGION_CLAUDE_5_5_SONNET`.
- Existing provider-specific alias overrides remain; `sonnet` does not necessarily resolve to the same model on every provider.
- This establishes CLI support. Actual access depends on the account, provider, and effective model configuration.

Evidence: Model catalog, alias defaults, and provider mappings contain `"claude-sonnet-5-5"` and `"VERTEX_REGION_CLAUDE_5_5_SONNET"`, both absent from 2.1.283.


### Certificate-based enterprise gateway authentication

What: Enterprise gateways can authenticate to an OIDC identity provider using a signed client assertion instead of a client secret.

Usage:

```bash
claude gateway --config gateway.yaml
```

Details:

- In the gateway’s existing `oidc` configuration, set `token_endpoint_auth_method` to `private_key_jwt`.
- Supply `client_assertion.private_key_pem` and `client_assertion.certificate_pem`, and remove `client_secret`.
- The implementation signs short-lived RS256 assertions and includes certificate thumbprints.
- Validation checks that the certificate matches the key. The key must be unencrypted RSA with at least 2048 bits.

Evidence: Gateway configuration validation and token authentication use `"oidc.client_assertion is required when token_endpoint_auth_method is private_key_jwt"` and `"oidc.client_assertion.certificate_pem does not match private_key_pem"`. Earlier bundled authentication dependencies mentioned client assertions, but the gateway configuration and implementation are new.


### Structured marketplace installation from links

What: Programs invoking the CLI can add a plugin marketplace using install-link handling and receive a structured result.

Usage:

```bash
claude plugin marketplace add https://example.com/marketplace.git --from-link
```

Details:

- The hidden `--from-link` option is intended for installation integrations.
- Success prints a JSON line containing the marketplace name and whether it was added.
- Refusals can report a structured reason and affected folder.
- It cannot be combined with `--claudeai`.

Evidence: Marketplace command registration documents `"--from-link"` and the JSON fields `"added"` and `"refused"`; the handler rejects `"--claudeai can't be combined with --from-link"`.


## Improvements


### Ultracode works independently of effort level

Ultracode no longer forces xhigh effort. Its standing dynamic-workflow orchestration can remain enabled while you choose another supported effort level.

Usage:

```text
/effort medium
/effort ultracode on
/effort ultracode off
```

The effort picker also gains a separate Ultracode toggle, bound to Tab by default. Turning Ultracode off preserves the effort level. Ultracode remains session-scoped and requires enabled workflows and a compatible model.

Evidence: Updated help says `"Ultracode (any effort level, this session only)"`; command responses include `"Ultracode off. Effort stays"`. The picker registers `"effortSlider:toggleUltracode"`.


### Approve an outside-directory read once

The outside-working-directory permission dialog now offers “Yes, but ask again next time.” This allows the current read without granting standing permission for later outside reads.

The other choices distinguish persistent approval, persistent blocking, and declining only the current request.

Evidence: The new `"allow_once"` result maps to an allowed read with `askAgainOutsideReads: true`; search for `"Yes, but ask again next time"`.


### More informative Remote Control trust prompts

When `claude rc` needs workspace trust, its prompt now describes consequential project configuration, including command hooks, credential helpers, environment variables, MCP servers, pre-approved permissions, additional directories, and memory-directory overrides.

It also explains when trusting a folder trusts its containing repository. Trust granted for the home directory lasts only for the current run. Terminals too small to display the required warning receive instructions to enlarge the window and retry.

Evidence: Search for `"This folder configures hooks that run commands"`, `"This folder runs credential helper commands"`, and `"This is your home directory, so trust lasts for this run only and is not saved."`


### Stronger checks on sandbox network destinations

The sandbox now checks resolved IP addresses as well as hostname rules. An allowed hostname can be refused when it resolves to a protected destination, such as a loopback, link-local, cloud-metadata, multicast, or local-host address.

Explicit IP permissions are considered by the check. Connections routed through an upstream or MITM proxy have different coverage because that proxy resolves the destination.

Evidence: The sandbox initializes a resolved-address checker and reports `"ERR_SRT_RESOLVED_ADDRESS_DENIED"`. Its protected-address categories include `"a cloud metadata address"` and `"one of this host's addresses"`.


### Clearer cloud file-sync state and recovery

For sessions with cloud file sync enabled, this release adds device-bound signing for upload requests and more specific explanations when the local computer cannot provide the required device identity.

Sync messages also distinguish a recreated cloud container from a rollback to an earlier snapshot. They explain whether earlier work was restored and which tools, caches, or background processes need rebuilding. When Anthropic pauses sync, the messages explain whether conversation messages can proceed or must wait for the initial files.

Evidence: Search for `"anthropic.ccr.session_synced_file_put.v1"`, `"This computer could not be set up to sign synced files"`, and `"This cloud environment was rolled back to an earlier snapshot"`. Cloud-sync availability remains subject to its existing rollout and session requirements.


### Safer skill replacement proposals

The existing requirement to read a skill before proposing its replacement now also covers proposals presented as “new” when their names would replace an existing skill. The implementation rechecks relevant files when the proposal tool executes, catching unread or stale content before presenting a replacement.

Evidence: Search for `"would be saved under the name of the listed skill"` and `"propose_skills: the read check refused the proposal"`. Full-file read checks already existed in 2.1.283; the expanded collision and execution-time checks are the change.


### More actionable authentication messages

`/auto-mode-setup` now checks login state before scanning the environment and distinguishes an unsigned-in session from an expired login that could not be renewed.

Organization-login policy errors also identify the conflicting credential source and suggest a more specific recovery action.

Evidence: Search for `"Auto-mode setup needs a signed-in account to scan your environment"`, `"remove apiKeyHelper from"`, and `"run claude without --bare and sign in"`.


### Corrected explanation of organization-bound thinking

The organization-change warning now explains that earlier thinking is unavailable under the current organization but is not deleted. It tells users they can resume under the original organization to use it again.

This corrects the previous warning’s claim that the thinking would be removed.

Evidence: Search for `"Claude can't use thinking from another organization"` and `"It isn't deleted: resume this session signed in to that organization to use it again."`


## Bug Fixes

- Fixed `/mcp reconnect all` in the terminal command handler. Previously, that handler treated `all` as a server name even though another command path already supported bulk reconnection. It now retries eligible failed or unauthenticated servers and reports the result. Search for `"No MCP servers need reconnecting"` and `"mcp reconnect all:"`.

- Added a bounded wait when a requested MCP tool belongs to a server still connecting, allowing the call to proceed if the tool becomes available. Search for `"tengu_mcp_pending_tool_wait"` and `"Not waiting for MCP tool"`.

- Fixed Linux sandbox startup failures caused by very large mount-argument lists by passing mount arguments through an unnamed file when needed. Oversized commands that still cannot fit receive a specific error. Search for `"bwrap mounts moved to an unnamed file"` and `"Sandboxed command is too long for one shell argument"`.

- Improved handling of oversized remote-tool responses. The CLI can return a compact failure explaining that the command completed but its output could not be delivered, helping prevent accidental repetition of commands with side effects. Search for `"is too large for the session service to carry back"` and `"Its effects stand"`.

- Rejects manual MCP-server additions when managed policy permits only plugin-provided servers, with an explanation of how to obtain an approved server. Search for `"Cannot add MCP server: your organization's managed settings allow only MCP servers that plugins provide."`

- Restricts `/recap` to requests from the user through supported interactive surfaces. Requests relayed from messaging channels or generated by routines cannot trigger it under the default-enabled check. Search for `"/recap only runs when you ask for it yourself"` and `"tengu_playful_hare"`.


## In Development

These additions are controlled by flags that default off or require an explicit rollout state. Their presence in the package does not establish availability for every account.


### PR Steward coordination [In Development]

What: Claude can recognize pull requests already being handled by PR Steward and avoid competing pushes or monitoring loops.

Status: Feature-flagged; `tengu_federated_flask` defaults to false.

Details:

- Recognizes `claude-pr-steward-watching` and `claude-pr-steward-is-working` labels.
- Adds guidance for leaving the PR with Steward, making one coordinated change, or taking over.
- Extends `/loop` and `/autofix-pr` coordination to account for Steward ownership.
- This is CLI coordination with Steward, not evidence that this release makes the Steward service generally available.

Evidence: Search for `"tengu_federated_flask"`, `"claude-pr-steward-watching"`, and `"PR Steward is watching"`.


### Memory-file content checks [In Development]

What: Additional checks protect Markdown memory files from invisible characters and text that imitates harness instructions.

Status: Feature-flagged; `tengu_memdir_write_lint` defaults to false.

Details:

- Rejects memory filenames containing invisible or control characters.
- Adds content checks and cleanup for invisible characters and harness-like markup.
- Detects edits that become empty after cleanup and avoids writing them.

Evidence: Search for `"tengu_memdir_write_lint"`, `"This memory file's path contains invisible or control characters"`, and `"Nothing to change once the invisible characters are removed"`.


### Clearing old tool results after inactivity [In Development]

What: Eligible sessions can request removal of older tool-result content from model context after a long idle period.

Status: Feature-flagged through `tengu_zany_pike`, with off, shadow, and on states.

Details:

- The shipped configuration considers idle periods of roughly 65 minutes.
- It retains recent tool uses and excludes unsuitable tool results.
- It requires compatible model context-management support.
- Shadow mode does not apply the clearing operation.

Evidence: Search for `"tengu_zany_pike"` and `"clear_tool_uses_20250919"` in the new idle-detection and context-management request logic.


### Additional review of computer-use actions [In Development]

What: Selected computer-use actions can receive additional permission review even when a broad tool-level allow rule exists.

Status: Feature-flagged through `tengu_quirky_shore`, which defaults to `"off"`, or enabled through the corresponding computer-use checks configuration.

Details:

- Permission evaluation checks the action before accepting a whole-tool allow rule.
- Browser and computer tool guidance now requests short descriptions of actions such as clicking, typing, and filling forms.

Evidence: Search for `"tengu_quirky_shore"`, `"computerUseChecks"`, and `"A few words saying what this action does"`.


### Illustrated mods guide [In Development]

What: An optional guide explains how Claude-written mods load and reload, using a small illustrated panel in the question interface.

Status: Feature-flagged; `tengu_linen_acorn` defaults to false.

Details:

- Adds a “How mods work” panel with an animated Clawd illustration.
- The guide is a new addition to existing mods functionality.
- No unconditional tip for this disabled guide was identified.

Evidence: Search for `"tengu_linen_acorn"`, `"cc-plugin-mods-guide"`, and `"How mods work"`.


## Notes

- To keep using Sonnet 5 where available, specify `--model claude-sonnet-5` instead of relying on the changing `sonnet` alias.
- Workflows that relied on Ultracode selecting xhigh should now set xhigh explicitly.
- Findings were checked against both version snapshots and the original Bun module sources. Rebundling changes, renamed identifiers, and module ordering are excluded.


Generated with:
- tool: `harness-investigations@3d7a0e4-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.284.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.284.txt`
- source modules: `archive/claude-code/original/cli-v2.1.284.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
