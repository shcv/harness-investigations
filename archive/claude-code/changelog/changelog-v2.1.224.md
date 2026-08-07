# Changelog for version 2.1.224

## Summary

This release adds first-class self-hosted runner support for Claude Code on the web, including setup, diagnostics, and running cloud sessions on a selected self-hosted environment. It also adds HTTPS ZIP distribution for marketplace plugins, persistent databases for capable Artifacts, and safer shared-memory updates.

## New Features

### Self-hosted runners and environments

What: Run Claude Code cloud sessions on your organization’s self-hosted environment, with built-in runner setup, operations, diagnostics, and orchestration commands.

Usage:

```bash
claude self-hosted-runner setup
claude -p "Review this pull request" --environment ccpool_your_environment
```

Details:

- `claude self-hosted-runner setup` starts an interactive setup wizard that creates an environment, starts a local runner, verifies it in the Admin UI, and writes a cheat sheet.
- `claude self-hosted-runner doctor` provides an interactive diagnostic workflow.
- The runner command also includes `orchestrator`, `code-sign`, and `decode-token` subcommands.
- `--environment <environment_id>` creates a new cloud session on the selected self-hosted environment; the older `--pool` name is retained as a deprecated alias.
- This requires an eligible self-hosted environment and the necessary Claude Code web/Admin UI access.

Evidence: New CLI dispatcher and setup flow (search for `"claude self-hosted-runner setup"` and `"Create a new cloud session that runs on the given self-hosted environment"`).


### ZIP-distributed marketplace plugins

What: Marketplace plugins can now be distributed as HTTPS ZIP archives, allowing hosting on static file servers or artifact repositories without Git or npm on the client.

Usage:

```json
{
  "source": "archive",
  "url": "https://plugins.example.com/my-plugin.zip",
  "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
}
```

Details:

- The archive may contain the plugin at its root or inside one wrapping directory.
- An optional SHA-256 digest is verified before installation and can serve as version identity when no declared version is available.
- Redirect destinations are checked against the archive URL policy.
- Marketplace authentication headers are forwarded only when the archive shares the marketplace source’s origin.

Evidence: Archive marketplace source schema and integrity enforcement (search for `"Plugin distributed as a zip archive"` and `"Plugin archive integrity check failed"`).


### Persistent databases for Artifacts

What: Claude can read and write structured shared data associated with Artifacts that declare database support.

Usage:

```bash
claude "Create a shared project tracker Artifact and store its tasks in the Artifact database."
```

Details:

- Supported database operations include `get`, `list`, `query`, `set`, `update`, and `delete`.
- Database rows are shared with people who can open the Artifact.
- First writes require confirmation; writes in plan mode require explicit user approval.
- Claude will prompt before reading another person’s Artifact database when ownership is not confirmed.

Evidence: Artifact actions now include `"read_db"` and `"write_db"` (search for `"artifact database"` and `"Database rows are shared state visible to everyone who can open the artifact"`).


## Improvements

### Safer collaborative memory updates

Shared memory documents now use optimistic version tokens, reducing the chance that one collaborator silently overwrites another’s changes.

Details:

- A memory write must provide `if_version`: either `new` for a new document or the token returned by a recent read/write.
- A conflicting write is rejected and can return current content and a fresh version token so Claude can merge and retry.
- Memory-store listings now expose each store’s index-document path.

Evidence: Versioned write guidance (search for `"Version tokens"` and `"If the document changed since you read it"`).


## In Development

Features with infrastructure added but not yet enabled. These are shipped dark and may become available in future versions.


### Local cross-session messaging [In Development]

What: Claude Code can host a local Unix-domain-socket messaging endpoint so compatible local sessions can exchange messages.

Status: Feature-flagged

Details:

- The hidden `--messaging-socket-path <path>` option configures the endpoint.
- The implementation creates a local socket, restricts it to local paths, and reports delivery states such as held, denied, expired, and delivered.
- It is unavailable on Windows and is gated by `tengu_harbor_kite`, which defaults to false unless enabled through `CLAUDE_CODE_HARBOR_KITE`.

Evidence: Feature gate defaults off (search for `"tengu_harbor_kite"` and `"cross-session messaging gate off"`).


Generated with:
- tool: `harness-investigations@a523eea-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.224.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.224.txt`
