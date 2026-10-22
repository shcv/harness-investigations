# Changelog for version 2.1.309

## Summary

Claude Code now shows messages waiting for delivery, lets you draft a prompt while a cloud session starts, and adds explicit workspace trust for `claude ultrareview`. Worktree creation gains missing-object recovery for partial clones, while tighter hook and permission checks may require changes to existing automation.

## New Features


### See Messages Waiting for Delivery

The transcript now shows queued messages under `Waiting to be delivered`, including messages addressed to the agent you are viewing. This makes it easier to distinguish a message that is still queued from one Claude has already received.


### Trust a Workspace for an Automated Ultrareview

`claude ultrareview` now checks workspace trust before running Git to collect changes. Interactive runs can show a trust dialog; scripts and CI can grant trust for that invocation with the new `--trust-workspace` flag.

```bash
claude ultrareview 123 --trust-workspace
```

The flag takes no value. Put the PR number or base branch before it, and use it only for a folder you trust: its Git configuration and Claude Code project settings can run programs.


### Draft Prompts During Cloud Session Setup [Gradual Rollout]

You can start typing while the cloud-session setup checklist is still running. The composer displays `Type your message while the session is set up`; sending remains unavailable until the session opens.

If setup is canceled or refused, supported exit paths print the unsent draft so you can recover it. A waiting setup question also prompts you to pause typing to see it.

This is controlled by `tengu_velvety_mango`, which defaults to enabled.


### Create Worktrees from Partial Clones More Reliably [Gradual Rollout]

Claude Code can fetch missing Git objects before creating a worktree from a partial clone, including repositories using sparse checkout. Recovery respects the files needed for the checkout and gives more actionable errors when a promisor remote is unreachable, misconfigured, or still missing objects.

The recovery has bounded fetch attempts and time limits. For very large missing-object sets, it recommends narrowing `worktree.sparsePaths` or materializing the commit in the main checkout first.

This is controlled by `tengu_eager_balloon`, which defaults to enabled.

## In Development


### Save Files Produced by Managed Tasks

A new `Save task files` capability is wired into compatible managed-task connectors. It would let you ask Claude to download files listed by a task into the local session’s `task-files` folder.

The implementation supports up to 20 files per call, a 500 MiB limit per file, approval for every save, and numbered filenames to avoid overwriting existing files. It requires a connector that advertises task-file support and is unavailable in cloud sessions.

The `tengu_serene_frog` gate defaults to off.


### Recover Expired Connector Sign-ins When Needed

Cloud sessions gain a connector authentication placeholder when an installed connector’s sign-in has expired. When your request needs that connector, Claude can retry its connection and, if necessary, trigger a sign-in prompt. Successful reconnection adds the connector’s tools back to the session.

Retries are limited to once per connector per turn. The `tengu_eager_raccoon` gate defaults to off, with additional cloud-session eligibility checks.


### Expanded Claude Test Panel

The bundled Claude Test implementation gains a richer panel for app startup, test outlines, run progress, screenshots, results, sign-in requirements, and proposed fixes. It also adds controls for confirming runs, requesting more tests, and remembering choices.

Availability remains behind `tengu_mellow_hollerith`, off by default. The eligibility checks require a supported Linux, macOS, or WSL environment, a non-root user, and an eligible claude.ai sign-in.

## Other Changes

- Changed `mcp_tool` hooks to reject calls to the Artifacts MCP server and the cloud browser where those calls would bypass permission checks.
- Changed `PermissionRequest` hook approvals so they cannot grant access to the cloud browser or loosen its restrictions.
- Changed Windows command hooks without Git Bash so explicitly selecting PowerShell no longer exempts shell-form hooks from failure blocking.
- Changed some directory-scoped skills to require their full scoped name in allow rules, and suppressed scoped skills whose names would collide.
- Changed teammate launches to preserve command-line deny rules and abort when a rule cannot be passed intact.
- Changed isolated-worktree commands to reject mentions of `RSYNC_CONNECT_PROG`, including obscured spellings that could conceal commands outside the worktree.
- Changed Artifact creation to require a person’s approval when mandated by organization policy, including refusals in unattended or bypassed-permission contexts.
- Added `CLAUDE_CODE_SYNC_PLUGINS_DOWNLOAD_CONCURRENCY` to control simultaneous plugin-sync downloads, accepting integers from 1 to 32 with a default of 6.
- Improved restarted self-hosted sessions to preserve information about interrupted tool calls whose execution or results may be incomplete.
- Improved self-hosted runner startup monitoring to recognize activity heartbeats while initialization continues.
- Improved disk-full and quota errors to distinguish missing output from truncated output and identify the volume needing space.
- Improved sandbox startup feedback to explain that setting file permissions can take a few minutes.
- Improved local mod development by telling Claude when a watched mod fails, allowing it to repair the mod for the next reload.
- Improved feedback failures to distinguish organization policy, unavailable submission, and rejected credentials.
- Improved Artifact publishing errors with concrete corrections for `root`, source paths, and served paths.
- Fixed MCP results with omitted text being treated as ordinary results; Claude is warned that the tool may already have run before retrying.
- Fixed shell commands running after their starting directory disappears in additional recovery paths; affected calls now stop and request reissue.
- Fixed sandboxed commands proceeding when sandbox wrapping produces no confinement.
- Fixed additional shell permission-checking gaps involving zsh expansions, special variables, locale assignments, and wrapped Git commands.
- Fixed browser-pane uploads bypassing relevant read restrictions, with additional checks for credentials and Claude Code’s own files.
- Fixed oversized project-document rewrites risking loss of content omitted from the preceding read.
- Fixed additional project-context reads proceeding when the repository’s read-permission rules could not be loaded.

## Notes

For unattended ultrareviews in an untrusted folder, add `--trust-workspace` only after establishing that the checkout is trusted. Unlike the self-hosted runner’s similarly named option, this ultrareview flag does not accept `true` or `false`.

On Windows without Git Bash, shell-form hooks that previously continued after a PowerShell failure may now block. Return exit code 0 for success or 2 for an intentional blocking verdict, or explicitly set `"onFailure": "continue"` when failures should pass.

Remove or retarget `mcp_tool` hooks that call the protected Artifacts or cloud-browser servers. If a scoped skill stops matching an allow rule, use its full name as displayed by Claude Code.


Generated by `harness-investigations@a3f0d92-dirty` using codex `gpt-6.1-sol` (medium effort)
Inputs: astdiff, strings, module sources
