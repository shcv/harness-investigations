# Changelog for version 2.1.232

## Summary

This release adds automatic Git-backed recovery checkpoints when a session nears or reaches a usage limit, making long-running work easier to resume. It also improves session-name disambiguation and tightens the security checks for explicit local messaging sockets.

## New Features

### Usage-limit recovery checkpoints

What: Claude Code can save a resumable snapshot of in-progress work when usage is nearly exhausted or a rate limit is reached.

Usage:

```bash
claude --resume <session-id>
```

Details:

- The checkpoint includes a `.claude/RESUME.md` file with the session ID, active TodoWrite plan, and the next step.
- Claude writes the snapshot to an internal Git ref named `refs/claude/checkpoint-*`, without creating a normal branch commit.
- The generated resume file is added to Git’s local exclude list so it does not become a project change.
- Checkpointing is skipped when the repository is unsafe or unsuitable, such as during an in-progress Git operation or for overly large snapshots.
- Older checkpoint refs are cleaned up after 14 days.

Evidence: Rate-limit checkpoint commit and resume instructions (search for `"WIP: Claude Code rate-limit checkpoint"` and `"claude --resume"`).


## Improvements

### Clearer handling of duplicate session names

When a name selected through `/rename` is already held by another live local session, Claude Code now assigns a distinct name and tells you which name to use when addressing the session. This reduces the risk of messaging the wrong concurrent session.

Evidence: Session-name collision notice (search for `"is held by another live session on this machine"`).


### Safer explicit messaging socket setup

Claude Code now requires the parent directory for `--messaging-socket-path` to be private and owned appropriately, setting it to mode `0700` where possible. This hardens local cross-session messaging against unsafe shared directories.

Evidence: Explicit socket-path guidance (search for `"Choose a different --messaging-socket-path whose directory you own and can make private (0700)."`).


## Notes

### Cloud-session invocation change

`--project` no longer starts a cloud session. If you use `--ref` or `--on-branch` for cloud work, invoke a cloud session explicitly with `--cloud` or `--environment`.

Evidence: Updated validation error (search for `"--project no longer starts cloud sessions"`).


Generated with:
- tool: `harness-investigations@0b079a4-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.232.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.232.txt`
