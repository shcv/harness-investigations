# Changelog for version 2.1.227

## Summary

This release adds cloud-session repository syncing, optional posting of cloud code-review results to GitHub pull requests, and model-proposed completion goals. It also strengthens remote-session safety, LSP reliability, MCP status reporting, and plugin/agent permission validation.

## New Features

### Sync the current repository into cloud sessions

What: When starting a cloud session from a repository, Claude Code can now copy the current working tree—including uncommitted and untracked files—to the cloud so the session starts with your local work.

Usage:

```bash
claude --remote
```

Details:

- The confirmation dialog lets you choose “Yes, sync this repository,” “No, don’t sync,” or defer the choice.
- Gitignored files are never copied; the choice is saved per repository.
- Synced files are encrypted at rest.
- The initial seed is bounded: the implementation limits eligible untracked files and skips unsafe, unreadable, oversized, linked, generated/dependency, or out-of-root files. If syncing cannot complete, the cloud session falls back to the repository’s Git state.

Evidence: Cloud-session consent dialog and behavior (search for `"Sync this repository to the cloud?"` and `"including uncommitted and untracked files but never gitignored ones"`)


### Post cloud code-review findings to a pull request

What: Cloud-hosted ultra reviews can post their completed findings to a GitHub pull request as a single comment from your GitHub account.

Usage:

```bash
claude ultrareview 123 --post
```

Details:

- Available for GitHub PR targets only.
- The post is one plain comment, not a GitHub review or approval.
- Posting is opt-in; `--no-post` remains the default.
- The session must remain open while the cloud review finishes because the posting consent is scoped to that run.
- Local `/code-review` uses `--comment` for inline comments; `--post` is specifically for cloud ultra review.

Evidence: CLI option and posting flow (search for `"Post the finished review's findings to the PR as you"` and `"one plain comment, not a review"`)


### Model-proposed session goals [Gradual Rollout]

What: Claude can propose a measurable completion condition for multi-turn work, then continue until a separate evaluator determines that condition is met.

Details:

- Proposals can ask for one-keypress approval, or set a goal directly only when the user explicitly stated the outcome.
- A goal can be at most 500 characters, only one may be active, and `/goal clear` removes an active goal.
- The setting offers `auto`, `alwaysAsk`, and `disabled`; typed `/goal` commands are unaffected.
- This is available only in interactive local sessions and is controlled by the server-side `tengu_propose_goal` rollout flag.

Evidence: Goal tool and trusted setting (search for `"Propose a session goal condition"` and `tengu_propose_goal`)


### Secure local command access for bound remote sessions

What: Remote/cloud sessions can use a `device_bash` tool to run commands on the machine where Claude Code was launched.

Usage:

```bash
claude --remote
```

Details:

- Commands run through the device’s Claude Code OS sandbox, not the cloud container.
- The bridge refuses execution unless the session is device-bound and the local sandbox is enabled, fully confining, and not configured to expose broad Unix sockets or real credentials.
- Calls have a 45-second maximum timeout and a four-command concurrency limit.

Evidence: Remote device command tool (search for `"Run a shell command on the user's local machine"` and `"device_bash"`)

## Improvements

### Remote artifact watches can wake cloud sessions

Existing artifact watches now work more usefully in remote sessions. Instead of requiring a live stream, a remote session can register a durable wake subscription and receive a new turn when the artifact is republished.

Evidence: Remote-watch behavior (search for `"durable wake subscription"` and `"re-read the artifact on wake"`)


### More resilient LSP startup and protocol handling

Claude Code now detects malformed LSP output, invalid headers, oversized messages, startup crashes, and initialization timeouts more explicitly. It can retry crashed servers within a configured restart limit instead of silently treating corrupted protocol traffic as valid.

Evidence: LSP recovery and diagnostics (search for `"LSP server crashed during startup"` and `"LSP server exceeded the header size limit"`)


### Clearer MCP state across sessions

The `/mcp` experience now explains when an MCP server was disabled or re-enabled in another session and gives concrete recovery guidance, such as disabling and re-enabling it or restarting Claude Code.

Evidence: Cross-session MCP guidance (search for `"MCP server(s) were disabled in another session"`)


### Stricter plugin, skill, and spawned-agent tool boundaries

Plugin adoption now rejects reserved and hidden skill directories, while agent spawning validates MCP deny rules and Bash command clamps more strictly. Invalid wildcard or mismatched MCP restrictions fail closed rather than launching an agent with broader access than intended.

Evidence: Validation and fail-closed errors (search for `"'mcp__*' for every MCP server's tools"` and `"reserved skills directory name"`)

## Bug Fixes

- LSP server failures now surface as explicit startup/protocol errors instead of allowing invalid stdout or a crash during initialization to leave the client in an ambiguous state. (search for `"LSP server sent non-protocol output in the header block"`)

- Cloud-session repository syncing falls back to the Git bundle when the file seed cannot complete, avoiding a failed sync preventing session startup. (search for `"Cloud file sync could not finish; the session starts from the git bundle alone"`)


Generated with:
- tool: `harness-investigations@50c1649-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.227.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.227.txt`
