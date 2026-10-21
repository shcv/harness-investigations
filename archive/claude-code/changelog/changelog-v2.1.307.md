# Changelog for version 2.1.307

## Summary

This release adds a Windows sandbox uninstall command and new controls for self-hosted runners, including nested-repository changes and explicit proxy configuration. Subagent history and improved MCP sign-in recovery are present behind disabled-by-default gates. Runner operators should review the proxy environment-variable change, the new 30-minute checkout-hook timeout, and stricter handling of workspace trust.

## New Features


### Remove the Windows Sandbox

You can now remove the Windows sandbox account and network filters from a terminal. The command also cleans up recorded sandbox permissions for your Windows account and reports anything left behind.

```bash
claude sandbox uninstall
```

For a machine-readable result:

```bash
claude sandbox uninstall --json
```

- Close all Claude Code sessions and other Claude programs before running it; removal refuses to proceed while detected Claude processes remain.
- Windows may request administrator approval.
- The JSON result contains `status`, `message`, `leftBehind`, and `filtersChecked`.
- This applies to native Windows; macOS, Linux, and WSL need no equivalent account or network-filter removal.


### Show Nested Repository Changes on Self-Hosted Runners

Sessions started without a repository can now show changes from a repository cloned into a subfolder of their working directory.

```bash
claude self-hosted-runner --capacity 1 --diff-finds-nested-repository
```

This is off by default. It selects one eligible repository, requires the session’s tool sandbox to be off, and checks a copy of the repository’s Git settings before reading changes. Rejected repositories leave the Changes pane empty and produce a reason in the runner log.

Enabling this changes repository selection: a repository in the working directory itself, or above it, is no longer shown. The runner recommends Git 2.45 or newer.


### Configure a Runner’s Agent Proxy Explicitly

Self-hosted runners now accept an operator-controlled proxy URL, with a flag taking precedence over the environment variable.

```bash
claude self-hosted-runner --agent-proxy-url https://proxy.internal:3128
```

Alternatively, set `SELF_HOSTED_RUNNER_AGENT_PROXY_URL` before starting the runner. The URL must use HTTPS and contain no username or password; sessions authenticate with their own credentials.

A runner configured this way refuses sessions requiring Anthropic-managed Git or Anthropic’s hosted relay. It also rejects combining this option with `--proxy-authorization-command` or `--proxy-authorization-file`.


### Reuse the Launcher’s Claude Sign-In [Gradual Rollout]

Eligible CLI sessions started by a desktop launcher can now request and refresh the launcher’s Claude account sign-in. The CLI checks the account against managed organization requirements and avoids taking this route when an explicit credential, gateway, provider, or sign-in policy takes precedence.

The `tengu_kestrel_lantern` gate defaults to enabled. Set `CLAUDE_CODE_DISABLE_LAUNCHER_SIGN_IN=1` to disable this behavior.

## In Development


### Subagent History in the Tasks Dialog

The tasks dialog gains an expandable `Earlier in this session` group built from saved subagent transcripts. It lists earlier agents with descriptions, parent-child nesting, stopped status, and start or last-activity times, making completed work easier to find after it leaves the active task list.

The listing is wired into the UI but gated by `tengu_rustling_crescent`, off by default. The code also provides a `CLAUDE_CODE_SUBAGENT_HISTORY` override.


### Recover MCP Sign-In Through claude.ai

When an HTTP or SSE MCP service rejects Claude Code’s automatic OAuth app registration, the CLI can offer a more useful recovery route. Depending on the service and account, it can identify an existing claude.ai connection, offer `Connect on claude.ai`, direct you to an administrator, or explain how to register an OAuth app manually.

The flow is implemented in both the MCP menu and CLI login handling, but `tengu_recursive_lobster` defaults to off. Connections established through claude.ai require restarting Claude Code to load their tools.

A separate disabled-by-default gate, `tengu_delightful_hamster`, would keep a plugin’s MCP server available when its only duplicate claude.ai connectors are ineligible.


### Idle Compaction for Keepalive Sessions

Idle compaction is being extended beyond sessions using the one-hour prompt cache. The new path tracks keepalive activity and can compact, or prepare a summary for your return, while the cached conversation remains usable.

The `tengu_bubbly_canyon` configuration controls this path and falls back to an off mode without an active configuration. The existing `idleCompaction: false` setting disables idle compaction.

## Other Changes

- Changed checkout hooks to time out after 30 minutes by default; added `--checkout-hook-timeout-min` and `SELF_HOSTED_RUNNER_CHECKOUT_HOOK_TIMEOUT_MS`, with `0` disabling the limit.
- Changed `--trust-workspace false` to ignore previously persisted workspace trust, preventing old trust records from restoring repository-level grants.
- Changed workflow scripts to refuse execution outside Bun with guidance to use the native `claude` binary.
- Changed remote managed-settings failure handling to retain restrictive policy settings when applicable, with `/status` explaining when cached restrictions remain active.
- Changed shell permission checks to require approval when nested commands or substitutions prevent a complete dangerous-`rm` analysis.
- Changed shell analysis to handle reserved words after assignments or redirects more conservatively.
- Improved MCP connection startup to detect sleep or clock changes and retry interrupted connections, with up to ten reconnect attempts.
- Improved MCP credential recovery so an unreadable keychain is distinguished from missing credentials, including instructions to unlock the Mac keychain.
- Improved MCP disconnect errors to distinguish calls that never ran from calls that may already have executed.
- Improved resumed cloud-session guidance to warn when restored disk state may lack recent tool changes or earlier uploaded attachments.
- Fixed empty model responses after a failed retry silently ending the turn; the CLI now reports an explicit error.
- Fixed `/clear` leaving a resume checkpoint active in the conversation it cleared.
- Fixed remote Artifacts MCP entries remaining eligible for connection when Artifacts are disabled in Claude Code settings.

## Notes

For standalone proxy deployments, replace `CCR_AGENT_PROXY_STANDALONE_URL` with `SELF_HOSTED_RUNNER_AGENT_PROXY_URL`, or use `--agent-proxy-url`, then restart the runner. Custom session wrappers must pass the new variable through.

Checkout hooks that intentionally take longer than 30 minutes need a larger `--checkout-hook-timeout-min` value or `0`. Hooks should wait for their child processes and redirect daemon output; a child retaining output pipes can still delay completion after the hook exits.

With `--trust-workspace false`, configure required grants in host-level settings. Project agent definitions that require trusted workspace access may need to move to the user or managed agents directory.

Sandbox removal preserves Claude Code settings. Disable `sandbox.enabled` separately if desired; settings that require an available sandbox can prevent subsequent startup until it is reinstalled or the requirement is changed.


Generated by `harness-investigations@01f4160-dirty` using codex `gpt-6.1-sol` (medium effort)
Inputs: astdiff, strings, module sources
