# Changelog for version 2.1.233

## Summary

This release adds artifact watching from the CLI, Windows sandbox provisioning commands, and optional identity forwarding for organization-owned Anthropic-compatible proxies. It also expands plugin validation and adds GitLab merge-request support when Claude Code creates worktrees.

## New Features


### Watch a Claude artifact from a local interactive session

What: Start Claude Code while watching a specific Claude artifact for new versions and comments.

Usage:

```bash
claude --watch-artifact <artifact-id-or-claude.ai-artifact-url>
```

Details:

- Use `--watch-artifact-no-autoreact` to receive watch updates without enabling automatic comment reactions.
- The watch requires an interactive, plain local session; it is rejected in print mode, redirected-output sessions, SDK sessions, and remote-environment sessions.
- The artifact URL must belong to the environment you are currently signed in to.

Evidence: Artifact watcher CLI option and validation (search for `"Watch a Claude artifact (id or URL) in this session and hear about new versions and comments"` and `"Error: --watch-artifact requires an interactive session"`).


### Windows sandbox installation and status commands

What: Native Windows builds can provision the Claude Code sandbox prerequisites and report whether sandboxing is usable.

Usage:

```bash
claude sandbox status
claude sandbox install
```

Details:

- `status` prints JSON containing `available`, `installed`, `policyLocked`, and `reasons`.
- `install` provisions the Windows sandbox user and network filters and may prompt once for UAC elevation.
- These commands are available only on native Windows builds with sandboxing enabled and permitted by the `enabledPlatforms` policy.

Evidence: Windows sandbox commands (search for `"Install the Windows sandbox user and network filters"` and `"Print Windows sandbox availability and install state as JSON"`).


### Forward signed-in developer identity to an organization-owned proxy

What: Anthropic-compatible custom upstreams can opt in to forwarding the signed-in developer’s identity to a proxy you operate.

Usage:

```yaml
upstreams:
  - name: internal-proxy
    provider: anthropic
    base_url: https://proxy.example.com
    forward_user_identity: true
```

Details:

- Requires configured OIDC identity; without a session principal, no identity headers are sent.
- The proxy can receive the developer’s IdP subject and, when present, email (`x-litellm-end-user-id`).
- Claude Code refuses this option for Anthropic-owned endpoints, including `anthropic.com`, so developer email is not forwarded to Anthropic.

Evidence: Upstream setting and endpoint guard (search for `"forward_user_identity"` and `"so user emails are never sent to Anthropic"`).

## Improvements


### Plugin validation now covers component directories

`claude plugin validate <path>` can now validate not only plugin and marketplace manifests, but also skills, agents, and commands within a directory.

```bash
claude plugin validate .
```

Validation now avoids following symlinks and warns when a component is a symlink, non-regular file, or too large to inspect. Validate the real path when such warnings appear; installation may still dereference safe in-tree links.

Evidence: Expanded command description (search for `"Validate a plugin or marketplace manifest, or the skills, agents, and commands in a directory"`) and symlink handling (search for `"validation never follows one"`).


### GitLab merge requests work in worktree-based flows

Claude Code now recognizes GitLab merge-request URLs and fetches GitLab’s `merge-requests/<number>/head` ref when preparing a worktree. GitHub pull-request behavior remains supported.

Evidence: GitLab MR URL recognition and ref fetching (search for `"/-/merge_requests/"` and `"merge-requests/${r.prNumber}/head"`).


### Plugin-evaluation verbose tracing moves to the debug log

For `claude plugin eval`, `--verbose` now records per-message trace events in the debug log rather than streaming the trace directly in the terminal.

```bash
claude --debug-file claude-debug.log plugin eval . --verbose
```

Evidence: Updated option description (search for `"Log per-message trace events to the debug log (use --debug-file to read them)"`).

## Bug Fixes

- Artifact comment automation now detects when a Claude reply already exists on a thread and suppresses a likely duplicate. A deliberate follow-up must explicitly use `acknowledge_duplicate: true`. Evidence: duplicate-reply guard (search for `"Reply not posted: a Claude reply"` and `"acknowledge_duplicate"`).

## Notes

The source diff identifies the comparison as 2.1.232 to 2.1.233. The standalone prettified version files were not accessible in this run, so verification used the supplied structural diff—including old and new code hunks—and AST-extracted string diff rather than direct full-file searches.


Generated with:
- tool: `harness-investigations@e22318a-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.233.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.233.txt`
