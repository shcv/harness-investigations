# Changelog for version 2.1.310

## Summary

Claude Code can display images through supported tmux sessions, and cloud handoff can proceed with local changes after explaining what will stay behind. This release also adds provider model-catalog opt-in and self-hosted proxy support for Anthropic-managed GitHub access. Stricter file attachment and Windows sandbox checks may require changes to existing workflows.

## New Features


### Images Inside tmux

Terminal image rendering now works through tmux, including screenshots shown by terminal panels. Previously, image detection treated tmux as unsupported.

Use tmux 3.3 or later with kitty 0.28+, Ghostty, or iTerm2 3.5+, and enable:

```bash
tmux set -g allow-passthrough on
tmux set -g focus-events on
```

Detach and reattach, then restart Claude Code so it can detect the configuration.

- iTerm2 requires `allow-passthrough on`; `all` is not supported for its images.
- Claude Code reports specific reasons when images cannot work, including missing pane information or an oversized tmux window.
- GNU screen remains unsupported.


### Anthropic-Managed GitHub Access Through a Self-Hosted Proxy

Self-hosted runners can now combine Anthropic-managed Git access with the `agent_proxy_standalone` relay mode. Previously, this combination was refused because managed Git required the hosted relay.

Eligible sessions route `git` and `gh` through the self-hosted proxy’s forwarder, with the required certificate and Git configuration installed for the session.

- Windows runners remain unsupported for this combination.
- Runners using `--exec-path` or a command hook cannot use this route because the runner cannot verify the child CLI’s handling of the proxy.
- Missing Git setup causes the session to be refused.


### Provider Model-Catalog Opt-In

Users of Bedrock, Vertex, Foundry, and Mantle can explicitly opt into the published model catalog, allowing supported model information to update independently of a CLI release.

With your existing provider configuration:

```bash
CLAUDE_CODE_MODEL_CATALOG=1 claude
```

Organization policy and other catalog eligibility checks still apply. Project settings can disable the catalog with `CLAUDE_CODE_MODEL_CATALOG=off`; enabling it belongs in the launch environment, user settings, or managed settings.


### Continue in the Cloud With Local Changes [Gradual Rollout]

The existing `/teleport` cloud handoff can now continue when you have uncommitted changes or unpushed commits. Instead of requiring you to clean up first, it explains what will remain on your computer and asks whether to proceed.

```text
/remote-control
/teleport
```

The cloud session uses the branch as last pushed. If the branch is absent from the remote, the handoff can offer the default branch instead. Claude Code rechecks the branch and Remote Control connection before moving.

This remains behind `tengu_teleport_send_to_cloud`, which defaults to `false`; it requires a claude.ai login and an available managed cloud environment.

## In Development


### Live Claude Test Panel

The `/claude-test` terminal panel now has a substantial implementation in place of its previous placeholder. It can show app startup, code inspection, test writing, individual test results, elapsed time, screenshots, and a link to the full report. Terminals without image support receive a text-only presentation.

The panel remains behind `tengu_velvet_harrow`, off by default, and Claude Test itself requires the account-controlled `tengu_mellow_hollerith` gate. The code supports eligible Linux, macOS, and WSL sessions; availability is not implied by upgrading.


### Deprecated API Model Detection

The `/claude-api` skill can scan project files for deprecated or retired Claude API model IDs and prepare a warning with retirement dates and current replacements. It directs Claude to mention affected models when working on code that calls them, while leaving existing IDs unchanged unless you request a migration or fix.

The scanner is wired into the skill, but `tengu_cosmic_sketch` defaults to `false`, and user-facing warnings require the treatment arm of `tengu_typed_trinket`, whose default is unenrolled. This is experimental rather than generally available.

## Other Changes

- Changed file attachments to require the resolved file path, rejecting a linked or differently resolved path with instructions to retry using its actual destination.
- Changed Windows strict-sandbox checks to reject commands that cannot be sandboxed or safely covered by an eligible exclusion.
- Changed isolated-worktree Git checks to reject additional ambiguous command forms and `git init` options that could affect the shared repository.
- Changed unattended artifact uploads and database imports to require human approval for suspicious source files, including certain linked files and files outside recognized user attachments.
- Added warnings in `/status` and `claude doctor` when sandbox deny paths refer to another computer and cannot be enforced by the local sandbox.
- Improved Ubuntu sandbox diagnostics to identify AppArmor restrictions that prevent bubblewrap from creating user namespaces.
- Improved Bedrock and Vertex default selection to reject unavailable catalog-provided defaults and report which model was skipped.
- Improved artifact comment notifications to explain which comments wake the session and when processing is paused by plan mode or an hourly limit.
- Improved resumed-session warnings to show how old missing disk changes may be and identify repeated restoration problems.
- Improved connector discovery guidance for expired sign-ins, directing users toward reconnecting the affected connector.
- Fixed Windows hooks containing only quoted strings being mistaken for successfully executed commands when falling back to PowerShell without Git Bash.
- Fixed API compatibility recovery for HTTP 400 and 422 responses rejecting `thinking.display`, avoiding repeated use of the rejected display option.
- Fixed stale telemetry environment values persisting after the settings that supplied them were removed.
- Fixed sandbox protection of linked-worktree metadata when its worktree directory cannot be listed on supported non-Windows systems.
- Fixed MCP question timeouts prompting immediate repeat calls; Claude is now instructed to report the unanswered question and wait.
- Fixed artifact MCP connections bypassing artifact-disable settings or an applicable deny rule.
- Fixed remote approvals proceeding on an earlier classifier decision after the target’s policy changed to require a person.

## Notes

For rejected attachments, retry with the resolved path shown in the error. Approval must name the file that will actually be sent.

On Windows, strict-mode `sandbox.excludedCommands` exemptions must come from user settings, managed settings, or `--settings`; project and local project settings do not qualify. Exclusions also cannot authorize an unsandboxed run where the required approval prompt is unavailable.

If a Windows hook stops working without Git Bash, install Git for Windows and restart, or specify the executable in `command` and its arguments in `args`. Hooks intended to print text through PowerShell should explicitly set `shell` to `powershell`.


Generated by `harness-investigations@638f5d2-dirty` using codex `gpt-6.1-sol` (medium effort)
Inputs: astdiff, strings, module sources
