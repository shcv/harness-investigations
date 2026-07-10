# Changelog for version 2.1.204

## Summary

This is a small patch release. The only behavioral change is a fix for SDK consumers using `--output-format stream-json` with `--verbose`: system messages queued during session initialization are now flushed to the output stream before the session goes live, preventing them from being silently dropped.

## Bug Fixes

- Stream-json verbose mode no longer drops system messages that were queued during session initialization. When `--output-format stream-json` and `--verbose` are both active, a subscriber is now registered before setup begins; any messages pushed to the queue (task notifications, task-started events, etc.) are immediately written to the stream as they arrive, and the subscriber is cleared once the session is fully initialized. Evidence: new `Fdf` function — `a3e(t), t()` pattern with `lse()` queue drain — activated by `l.outputFormat === "stream-json" && Boolean(l.verbose)` check (search for `"stream-json"` near `a3e` and `lse`).


Generated with:
- tool: `harness-investigations@03136fb-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.204.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.204.txt`
