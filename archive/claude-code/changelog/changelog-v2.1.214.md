# Changelog for version 2.1.214

## Summary

Patch release with one internal fix: sandboxed tool execution now sets `MIMALLOC_SCAVENGER=0` in the subprocess environment on supported platforms, disabling the background memory reclaim thread to reduce CPU overhead during sandbox runs. No user-facing behavior changes.

## Improvements

### Reduced CPU overhead in sandboxed tool execution

When Claude Code spawns a subprocess inside the sandbox (e.g., during a Bash tool call with sandboxing enabled), it now injects `MIMALLOC_SCAVENGER=0` into the subprocess environment on platforms that use the mimalloc allocator.

`MIMALLOC_SCAVENGER=0` disables mimalloc's background scavenger thread, which periodically reclaims unused memory pages. Disabling it trades slightly higher peak RSS for lower sustained CPU use — worthwhile for short-lived tool subprocesses where memory reclamation latency doesn't matter.

The flag is only set when sandbox mode is active and the platform check passes (search for `"MIMALLOC_SCAVENGER"` to verify). On non-mimalloc platforms the helper returns an empty object, so there is no effect.

Evidence: subprocess environment builder (search for `"MIMALLOC_SCAVENGER"`)


Generated with:
- tool: `harness-investigations@d5cccf8-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.214.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.214.txt`
