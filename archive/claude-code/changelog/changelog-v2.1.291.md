# Changelog for version 2.1.291

## Summary

Version 2.1.291 removes a transcript-loading retry mechanism that could cause session resume to fail when transcript rewrites repeatedly interrupted reads. It also changes how feedback collects subagent histories and introduces server-controlled gating for mid-turn cost updates in headless sessions.


## Improvements


### Concurrent Subagent History Collection for Feedback

Feedback collection now starts all eligible subagent transcript reads together, replacing the previous limit of four concurrent reads. This removes batching delays when collecting histories from sessions with many subagents; the actual time saved depends on storage performance.

Usage:
```text
/feedback
```

Unreadable or empty subagent histories continue to be omitted. This changes collection behavior rather than adding a new feedback capability.

Evidence: Subagent history collection follows progress records containing `"agent_progress"` and `"skill_progress"` and supplies `subagentTranscripts` to feedback. Both versions contain this workflow; the original modules show the loader changing from a concurrency-limited mapper to `Promise.all`.


## Bug Fixes

- **Removed transcript-rewrite retry exhaustion during session resume.** In 2.1.290, transcript rewrites could abandon active reads, restart loading, and eventually fail after three unsuccessful passes. Version 2.1.291 removes that coordination and the associated exhaustion error. Resume uses the existing command:
  ```bash
  claude --resume
  ```
  Large-transcript scanning also becomes synchronous, replacing periodic event-loop yields. This removes the specific retry-exhaustion path, but does not establish that every resume problem is fixed or that loading is faster; large scans may temporarily reduce CLI responsiveness.

  Evidence: Search the old source for `"TranscriptLoadExhaustedError"` and `"loadTranscriptFile: rewrites of the transcript left every load pass behind"`—both are absent from the new source. The loader and resume error handling remain searchable through `"loadTranscriptFile: transcript unreadable"` and `"loadFullLog: transcript unreadable"`. The original modules confirm that the retry loop, read-abandonment checks, and rewrite-wait helpers were removed.


## In Development


### Server-Controlled Mid-Turn Cost Updates [In Development]

What: Headless sessions can report cumulative cost and token usage during an ongoing turn, with the reporting interval now controlled by a server-provided value.

Status: Feature-flagged; disabled by default in the shipped code.

Details:

- Mid-turn reporting already existed in 2.1.290, with a fixed minimum interval of 15 seconds.
- Version 2.1.291 introduces `"tengu_enchanted_willow"`, read with a default value of `0`.
- Reporting runs only when that value is a finite, positive number. The interval is clamped to at least 15 seconds.
- With the default value, periodic mid-turn updates are skipped. The separate turn-end reporting path remains.
- No new CLI flag, environment variable, or setting is provided for users to enable this behavior. Actual availability depends on server configuration.

Evidence: Search for `"tengu_enchanted_willow"` in 2.1.291; it is absent from 2.1.290. The existing reporting payload contains `"cumulative_cost_usd"` in both versions. Original module sources confirm the new gate around `pushMidTurn()` and its default-disabled behavior.


Generated with:
- tool: `harness-investigations@42d39a3-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.291.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.291.txt`
- source modules: `archive/claude-code/original/cli-v2.1.291.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
