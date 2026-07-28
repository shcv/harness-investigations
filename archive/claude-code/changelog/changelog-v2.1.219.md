# Changelog for version 2.1.219

## Summary

This release adds Claude Opus 5 model choices, including a 1M-context option for long sessions. It also introduces DirectoryAdded hooks and expands the gradual rollout of dynamic multi-agent workflows with configurable size guidance.

## New Features

### Claude Opus 5 model selection

What: Claude Code can offer Opus 5 as the primary Opus model, plus an Opus 5 1M-context variant for large codebases and long-running sessions.

Usage:

```bash
/model
```

Details:

- Select Opus for everyday complex work where it is available to your account.
- Select the 1M-context option for sessions that need to retain more repository context.
- Fast mode now identifies Opus 5 as a supported model.

Evidence: Model entries include `"Opus 5 - best for everyday, complex tasks"` and `"Opus 5 with 1M context window - for long sessions with large codebases"`.


### DirectoryAdded hooks

What: Hook authors can now run automation after a working directory is added to a session.

Usage:

```bash
/add-dir ../another-project
```

Details:

- The new `DirectoryAdded` hook receives the directory and its source, such as `/add-dir` or an SDK registration request.
- Hook output can be returned as a session notification.
- Duplicate directory registrations are rejected, so the registration pipeline and hooks do not run twice.

Evidence: New hook event `"DirectoryAdded"` and handler output `"DirectoryAdded hook:"`; directory registration documentation says `"the registration pipeline and DirectoryAdded hooks do not re-run"`.


### Dynamic workflows [Gradual Rollout]

What: Claude can orchestrate multi-agent workflows, with a user-configurable size guideline.

Usage:

```text
Use a small workflow, 5 agents max
```

Details:

- Use the `ultracode` keyword or directly ask Claude to use a workflow.
- In `/config`, set “Dynamic workflow size” to `small`, `medium`, `large`, or `unrestricted`.
- The guidance targets fewer than 5, 15, or 50 agents respectively; it is advisory rather than a hard limit.
- Availability is controlled by the `tengu_workflows_enabled` rollout flag and policy/settings gates.

Evidence: `"Dynamic workflows let Claude write a script that orchestrates many agents for you"` and `tengu_workflows_enabled`.

## Improvements

### More flexible protected-directory registration

`/add-dir` and SDK directory registration can now accept a strict subdirectory of either the current working directory or a launch-time `--add-dir` / SDK additional-directory root. This makes it easier to bring approved sibling project directories into an active session without broadening access arbitrarily.

Evidence: `"The directory must resolve to a strict subdirectory of cwd, or of a directory passed at launch via --add-dir / the SDK additionalDirectories option"`.


### Clearer synced-memory conflict recovery

When synced project memory cannot mount because a directory belongs to another store or already contains files, Claude Code now explains how to recover safely: rename or relocate the conflicting directory, then allow the next sync cycle, write, or restart to re-enable syncing.

Evidence: `"sync re-enables automatically on the next sync cycle once it is out of the way"` and `"the store mounts automatically on the next sync cycle once the directory is empty or gone"`.

## Bug Fixes

- MCP policy URL predicates now fail closed when environment-variable expansion would introduce wildcard semantics, restructure the URL, or produce an invalid URL. Denylist entries are unaffected. Evidence: `"MCP policy URL predicate expansion was unsafe"`.

## In Development

Features with infrastructure added but not yet enabled. These are shipped dark and may become available in future versions.


### Plugin skill-usage statistics [In Development]

What: A `/plugin stats` view is prepared to show skill usage and context costs, replacing the prior `/skill-doctor` location.

Status: Feature-flagged

Details:

- The command and Installed-tab Stats view are implemented.
- Access is gated by `tengu_lantern_prism`, which defaults to disabled unless enabled by rollout or environment configuration.

Evidence: `"Show skill usage and context costs"`, `"/skill-doctor moved — skill usage and context costs now live in this Stats tab."`, and `tengu_lantern_prism`.


Generated with:
- tool: `harness-investigations@3c353ff`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.219.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.219.txt`
