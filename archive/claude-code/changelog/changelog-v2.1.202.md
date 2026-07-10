# Changelog for version 2.1.202

## Summary

This release ships audio file transcription (users can now @-mention audio files and Claude Code will transcribe them), a major agent-proxy enhancement that routes GitHub git and `gh` CLI access through the session relay for remote and cloud environments, and an explicit `stop: true` parameter on `ScheduleWakeup` for cleaner loop termination. It also adds a persistent workflow size default in `/config`, improves interrupted-response recovery with smooth continuation, and fixes a safety regression where restored sessions could inherit `bypassPermissions` mode without the flag.


## New Features


### Audio File Transcription

What: When you @-mention an audio file in your message, Claude Code now automatically transcribes it using Anthropic's speech-to-text service before sending the request to the model.

Details:
- The model receives a structured `<audio-transcript>` block containing the filename, duration, and transcript text.
- In the terminal UI, successful transcriptions display the filename in blue with duration and word count (e.g., `♪ recording.mp3 (1:23, 187 words)`).
- If transcription fails, the display shows the filename in orange with an error message: `♪ recording.mp3 — transcription failed: <reason>`.
- If the audio file could not be downloaded at all, the model receives `[attachment could not be downloaded]`.
- The `@-mention` reference appears as `[Audio #N]` in the conversation display alongside `[Image #N]` and `[Pasted text #N]`.
- Transcription can be controlled by the `allow_voice_file_transcription` policy setting.

Evidence: Audio transcript XML formatter (search for `"<audio-transcript filename="`) — `EBo()` function at ~line 515493; attachment rendering case `"audio_transcript"` at ~line 20326.


### Agent Proxy: GitHub Git and `gh` CLI Access

What: The session relay (agent-proxy) can now configure git and the `gh` CLI to route GitHub API traffic through the proxy tunnel, enabling authenticated GitHub access in sandboxed or remote agent environments.

Details:
- Opt in with two new environment variables:
  - `CLAUDE_CODE_AGENT_PROXY_GIT_CONFIG=1` — appends proxy and credential settings to `$GIT_CONFIG_GLOBAL` so git-over-HTTPS to github.com uses the tunnel.
  - `CLAUDE_CODE_AGENT_PROXY_GH_SHIM=1` — installs a per-session `gh` shim script that routes `gh` API calls through the proxy.
- The git config injection adds `[http "https://github.com/"]`, `[credential "https://github.com/"]`, and optionally `[url "https://github.com/"]` blocks with `proxy =`, `sslCAInfo =`, and `insteadOf =` entries. The injected block is fenced with sentinel comments so it is idempotent and cleanly replaced on each session start.
- The `gh` shim is a POSIX shell script written to a temp `bin/` directory prepended to PATH. It routes to the relay only for github.com targets with no customer credential present. GHE hosts (`GH_HOST`, `--hostname`, `-R` with a non-github.com owner, or a non-github.com `origin` remote) bypass the shim and execute the real `gh` directly. Customer tokens (`GH_TOKEN`, `GITHUB_TOKEN`, `GH_ENTERPRISE_TOKEN`, `GITHUB_ENTERPRISE_TOKEN`) bypass immediately.
- Safety: the shim is never written if the `gh` binary path or the temp directory contains a single quote.
- The shim injects `GH_TOKEN='proxy-injected'` for the relay path; the real token is supplied by the relay.

Evidence: Governed git config arm (search for `"[agent-proxy] governed git: relay routing for"`) — `RMm()` at ~line 762228; gh shim writer (search for `"# claude agent-proxy governed-git gh shim"`) — `LMm()` at ~line 762293; env var gate (search for `"CLAUDE_CODE_AGENT_PROXY_GIT_CONFIG"`) — `ALc()` at ~line 762223.


### Dynamic Workflow Size in /config

What: A new "Dynamic workflow size" setting in `/config` lets you set a persistent default that limits how large workflows can be.

Usage:
```
/config
# Select "Dynamic workflow size" → small / medium / large / unrestricted
```

Details:
- Options: `unrestricted` (default, no limit), `small` (~5 agents), `medium` (~15 agents), `large` (~50 agents).
- Changing the setting injects a system-level note into the next turn: "The user has configured a workflow size guideline in /config: small. This is a guideline, not a hard limit — follow it unless the user's prompt calls for a different scale."
- The change is acknowledged with a mid-session notification: "The user changed their workflow size guideline in /config: small."
- Setting it back to unrestricted generates: "The user removed their workflow size guideline in /config — workflow size is unrestricted again."
- The workflow size tip now also mentions: "For a lasting default, set Dynamic workflow size in /config."

Evidence: Config option definition (search for `"workflowSizeGuideline"`) — `Qwt()` structural change at ~line 7950; guideline system message injector (search for `"The user has configured a workflow size guideline in /config"`) — `J4o()` at ~line 4958.


## Improvements


### ScheduleWakeup: Explicit Stop with `stop: true`

The ScheduleWakeup tool now accepts a `stop: true` parameter to end a dynamic loop immediately. Previously, ending a loop required omitting the tool call entirely; now you can explicitly stop with `stop: true` (all other fields are ignored when stopping).

Details:
- New parameter: `stop` — boolean, defaults to false. When true, cancels all pending wakeups, clears the tick-in-flight prompt, and emits the loop-ended event.
- New log entry: `[loop] model called ScheduleWakeup({stop:true}) — ending loop (N pending wakeup(s) cancelled)`.
- If called after the loop already ended (race condition): `[loop] ScheduleWakeup({stop:true}) after loop already ended — cleanup only, terminal event suppressed`.
- Tool description updated from "always pass the `prompt` arg; omit the call to end it" to "always pass the `prompt` arg unless stopping; call with `stop: true` to end the loop immediately".
- When `stop` is true, `delaySeconds`, `reason`, `prompt`, and `noop` are all ignored.

Evidence: Stop handler (search for `"[loop] model called ScheduleWakeup({stop:true})"`) — `wCa()` at ~line 276348.


### Interrupted Response Continuation

When a model response is silently interrupted mid-stream (e.g., due to a refusal-continuation retry), the model now receives structured instructions to pick up exactly where it left off rather than starting over.

Details:
- The model receives: "The previous attempt at this response was interrupted before it could complete. The text it had produced so far is quoted below" followed by a `<partial-response>` block.
- The instruction "Continue from exactly where the quoted text leaves off. Do not repeat any of the quoted text, do not apologize or recap, and do not mention the interruption in this or any future turn." is appended.
- For very long partial responses, only the tail is included with "(earlier part omitted)" noted.
- Smart stitching (`sKn()`) handles punctuation and markdown list boundary rules when joining the partial response to the continuation.
- The internal telemetry event description for refusal-continuation was updated from "window begins" to "silent retry begins".

Evidence: Continuation message builder (search for `"The previous attempt at this response was interrupted"`) — `M1s()` at ~line 140889; smart stitcher (search for `"Continue from exactly where the quoted text leaves off"`) — `sKn()` at ~line 140871.


### Skill Re-invocation Deduplication

When a skill is invoked a second time in the same session, Claude Code now detects whether the content has already been seen and sends a compact reminder rather than re-inserting the full skill body.

Details:
- If the skill body is already verbatim in the conversation: emits "Skill /name is already loaded above; instructions unchanged." (plus arguments if provided).
- If the skill was loaded but is only in the compressed attachment (not the visible body): emits "Skill /name was loaded earlier (see the invoked-skills reminder above); this is a NEW invocation — follow those instructions now, including any setup steps."
- If the skill content ends with the compaction truncation marker: emits "(Re-invocation of /name — the previously loaded copy was truncated by compaction; the full instructions follow.)" and re-inserts the full content.
- Log message on deduplication: "SkillTool eliding byte-identical re-invocation of skill /name".

Evidence: Skill deduplication logic (search for `"SkillTool eliding byte-identical re-invocation of skill"`) — `vOf()` at ~line 527443.


### Worktree Orphan Self-Healing

Orphaned worktree directories left over from a previous crashed session are now detected and automatically removed when a new worktree operation encounters them.

Details:
- Detection: if the worktree directory exists but git's worktree index no longer references it (`ENOENT` on `readdir`).
- Safety checks before removal: (1) a git remote must exist (fails open if no remote is configured), (2) the branch must not have unpushed commits (refuses to delete if `git rev-list --not --remotes` returns any commits).
- On successful cleanup: logs `[worktree] removed orphaned worktree directory at <path>`.
- The worktree copy of `settings.local.json` is now also written to each new worktree on creation, skipping symlinked source files.

Evidence: Self-heal logic (search for `"Orphaned worktree dir at"`) — `sPp()` at ~line 287052; settings copy (search for `"Copying settings.local.json to worktree"`) — `aPp()` at ~line 287322.


### Workflow Script Parse Errors Show Exact Location

When a workflow script fails to parse, the error message now includes a caret (`^`) pointing to the exact column where the parse error occurred, alongside the surrounding line of source code.

Details:
- Uses the `loc.line` and `loc.column` from the parser's thrown error to extract the relevant source line.
- Truncates very long lines to a readable window, centering the caret on the error column.
- The hint message was updated from the previous phrasing to: "Workflow scripts must be plain JavaScript — common causes are TypeScript syntax (type annotations, interfaces, generics) and broken string quoting or escaping."

Evidence: Error formatter (search for `"Workflow scripts must be plain JavaScript"`) — `N8p()` at ~line 369297.


### Unified Proxy Error Reporting

The WebFetch and WebSearch worker-proxy error messages are now unified under a shared helper. Error messages no longer expose the internal `ccr webfetch-proxy` / `ccr websearch-proxy` log prefixes to users.

Details:
- Removed: separate `TPl()` (WebSearch proxy) and `$Lf()`/`Y1f()` (WebFetch proxy) implementations.
- Added: single `TFo()` helper used by both `r1l()` (WebFetch) and the WebSearch path.
- User-visible error labels changed from "Request to the WebSearch proxy failed" / "The WebSearch proxy rejected the request" to unified "Request to the", "returned HTTP", "search error", "fetch error", "transport error" patterns.
- Internal log prefixes updated from `ccr websearch-proxy` to plain `search error` / `websearch-proxy transport error`.
- The Monitor tool's compliance-policy egress denial message was updated to remove the trailing period for consistency.

Evidence: Unified proxy helper (search for `"webfetch-proxy"` in new file) — `r1l()` at ~line 528143.


### Model Family Detection Now Data-Driven

The hardcoded model name→family lookup tables for Vertex, Bedrock, and model override resolution have been replaced with dynamic lookups driven by the server-provided model registry.

Details:
- Removed: `LCa()` (hardcoded 15-entry model name→slug mapper) and `ukf()` (hardcoded Bedrock/Vertex override resolver).
- Added: `Vka()` (reads from live model registry sorted by family priority) and `EDf()` (iterates registry entries with `fallback_3p` field instead of hardcoded entries).
- The vertex region env var list is now built dynamically from the registry: `qAu` is populated by iterating `KLt().models` and filtering on `vertex_region_env_var`.
- New `Amr()` helper strips the `-0` semver sentinel from model version strings before comparisons.

Evidence: Dynamic family resolver (search for `"fable"` in new file near `Uka` array) — `D8` module at ~line 289044; fallback resolver (search for `"fallback_3p"`) — `snn` module at ~line 510219.


### MCP Connector Manifest Deduplication

When multiple MCP manifest entries resolve to the same connector name, they are now automatically merged into a single entry with their tool lists combined, instead of causing errors.

Details:
- A merge pass consolidates tools from duplicate entries.
- A warning is emitted per merged connector: "N manifest entries resolve to connector 'X' and were merged into one (M tools). A viewer with more than one connector named 'X' gets server_ambiguous on every call until the duplicates are renamed or removed."
- If after resolution any entry's tool list exceeds the limit, a `serverCount` error is returned.
- The `claude_ai_` prefix is used to detect first-party connectors; non-first-party duplicates are passed through unchanged.

Evidence: Merge logic (search for `"manifest entries resolve to connector"`) — `kMl()` at ~line 544136.


### Team Permission Path Escaping

Special characters in team-wide allowed paths are now properly escaped before being compiled into permission rules.

Details:
- Previously, paths containing `[`, `]`, `(`, `)`, `|`, `+`, `^`, `$`, `!`, `#`, or trailing whitespace could produce malformed glob patterns.
- The `NSr()` function now handles gitignore-style escaping including glob metacharacters, leading `!`/`#` characters, and trailing whitespace.

Evidence: Path escaper (search for `"escapeGlobs"`) — `NSr()` at ~line 66113; usage in teammate init (search for `"Applying team permission"`) — `Yii()` at ~line 17368.


## Bug Fixes

- `bypassPermissions` mode is now refused on session state restore if the session was not launched with `--dangerously-skip-permissions` or if the policy disables it. Previously, a session restored from a persisted state file could inherit elevated permissions it was never granted. Falls back to `default` mode with a warning. (search for `"Refusing restored mode 'bypassPermissions'"`)

- File atomic-write cleanup is now correct: when a rename-based atomic write fails and falls back to `copyFile`, the temp file path (not the destination path) is now cleaned up on failure. (search for `"ENOSPC"` in `KTu()` at ~line 21948)

- Chord keybinding matching now uses the correct comparison function `a2r()` instead of the removed `RZi()`, fixing a potential failure in multi-key chord detection. (search for `"chord_started"` in keyboard handler at ~line 8353)


## Notes

The `--teammate-mode` flag has been removed from subagent spawn command generation. Sessions using multi-agent (swarm) features will continue to work; the backend selection now uses a different mechanism. If you have scripts or automation that parse subagent invocation commands and look for `--teammate-mode`, those will need updating.

The `Insights` HTML report generator (used for session analytics artifacts) has been removed from the CLI bundle. If your workflow depended on the Claude Code Insights shareable HTML report, this feature is no longer available in this version.


Generated with:
- tool: `harness-investigations@03136fb-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.202.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.202.txt`
