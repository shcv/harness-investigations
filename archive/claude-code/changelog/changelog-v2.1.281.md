# Changelog for version 2.1.281

## Summary

Version 2.1.281 extends custom-agent configuration, adds Windows support for safely receiving cloud-session file changes, and improves recovery after cloud environments restart. It also strengthens destructive-command checks, improves streaming-error handling, and clarifies hook behavior. New infrastructure for creating cloud sessions with `claude -p --cloud` is included but remains disabled in this build.

## New Features


### Windows support for receiving cloud file changes

What: The CLI adds a Windows implementation for safely placing files received through cloud directory sync.

Usage: Open a cloud session from a local project directory using the existing cloud workflow:

```bash
claude --cloud
```

Details:

- The previous version rejected Windows at the safe-file-placement step; this version implements Windows-specific file and directory operations.
- Requires a build with the necessary native file interface and a supported local filesystem.
- Network drives remain unsupported for this path.
- Files held open by other programs can be left unchanged and retried after those programs release them.
- Online-only files are skipped rather than downloaded automatically.

Evidence: Windows directory-sync backend selection and file-placement implementation (search for `"win32_handle"`, `"dirSync anchor (win32): held-handle backend up"`, and `"this file is online-only"`).


### Look up people referenced in Artifact data

What: Artifact database operations can resolve opaque person IDs into available display names and guest indicators.

Usage: Ask Claude to identify people referenced in an Artifact’s records or live events. The database tool supports `action: "profiles"` with the Artifact URL and an `ids` array.

Details:

- Accepts between 1 and 64 IDs from that Artifact’s data.
- Returns only information the Artifact service permits the session to see.
- Names are user-chosen display names, not verified identities.
- IDs should not be compared across Artifacts belonging to different owners.
- Requires access to the existing Artifact tools and a service that supports the lookup.

Evidence: New profile lookup schema, service request, and result rendering (search for `"db_profiles"`, `"/api/frame/user/profiles/"`, and `"action 'profiles' only:"`).

## Improvements


### Load custom-agent definitions from a file

The existing `--agents` option now accepts a JSON file path when used with `--print`, avoiding the need to place a large agent definition directly on the command line.

Usage:

```bash
claude -p --agents ./agents.json "Have the reviewer inspect this project"
```

The file contains the same agent-name-to-definition object previously supplied inline. Interactive sessions and `--bg` still require inline JSON. File loading checks for oversized files, multiple hard links, and changes to the file while it is being read.

Evidence: Updated option and file-loading validation (search for `"--agents <json-or-file>"`, `"Error: --agents takes a JSON object"`, and `"Error: --agents file changed while it was read:"`).


### Disable attribution with a boolean setting

The `attribution` setting now accepts `false` to suppress commit attribution, pull-request attribution, and session links together:

```json
{
  "attribution": false
}
```

Setting it to `true` restores the default behavior. The existing object form remains available for configuring each field separately.

Evidence: Settings validation converts `false` to empty commit and PR attribution plus `sessionUrl: false` (search for `"Set to false to hide all attribution"`).


### Use `/batch` outside Git with worktree hooks

`/batch` now accepts non-Git projects when a `WorktreeCreate` hook supplies worker isolation.

Usage:

```text
/batch replace deprecated API calls throughout this project
```

Configure `WorktreeCreate` and `WorktreeRemove` hooks for the project’s version-control system. The generated worker instructions then use the project’s own publishing commands instead of assuming Git and `gh`. A worker’s publication report can count as completion even when no PR URL exists.

Evidence: The command now checks for a worktree hook before rejecting a non-Git directory and adjusts its instructions (search for `"no WorktreeCreate hook is configured"` and `"worker worktrees come from a WorktreeCreate hook"`).


### Restore more work after a cloud environment restart

For sessions using directory sync, the CLI can reconstruct an earlier cloud checkout from stored uploads after its container is replaced.

Details:

- Recovery can restore commits, the staged state, and working files, including supported uncommitted files.
- Notices distinguish complete recovery through the last completed turn, partial recovery, and failed recovery.
- Edits from an interrupted turn may be missing.
- Other local branches, stashes, repository configuration, installed tools, and background processes are not reconstructed.
- Files excluded from synchronization remain outside the recovery scope.

Evidence: Checkout restoration and differentiated recovery notices (search for `"RESTORED into this checkout"` and `"RESTORED into this checkout only IN PART"`).


### Clearer hook ownership and safe-mode explanations

The `/hooks` interface better explains where hooks come from and how to change them. It distinguishes built-in, plugin, managed, settings-file, and dynamically registered session hooks.

Safe-mode messaging now explicitly states that settings-file hooks are suspended while session hooks created by `/goal`, agents, and skills can still run. It also explains when managed policy hooks remain active and when saved settings edits will take effect.

Evidence: Updated hook detail and status views (search for `"Built in to Claude Code. It can't be changed or removed."`, `"Session hooks created by /goal, agents and skills still run"`, and `"Registered while Claude Code was running"`).


### Warn about the combined size of instruction files

Instruction-file diagnostics now detect an excessive combined size, even when individual files are below their separate warning thresholds. This helps identify projects where many modest instruction files collectively consume substantial context.

The new diagnostic reports the file count, total character count, and combined threshold.

Evidence: Aggregate instruction-file checks (search for `"Instruction files will impact performance:"` and `"totalLimitChars"`).


### Personalized auto-mode suggestions in `/insights`

`/insights` can now estimate how many recent permission prompts auto mode might have handled and suggest switching when appropriate.

For users already using auto mode, it can instead recommend `/auto-mode-setup` when environment guidance is missing. Recommendations check availability and session behavior rather than appearing indiscriminately.

Usage:

```text
/insights
```

Evidence: Recommendation selection and report output (search for `"Tip: auto mode could have handled up to ~"` and `"Tip: you already use auto mode"`).


### Stronger checks for ambiguous removal commands

Destructive-command checks now cover additional removal targets that cannot be safely resolved before execution, including command-substitution output, potentially empty expansions ending in top-level directory names, and backslash-only targets that denote a drive root in Git Bash.

For command-substitution targets, the prompt recommends evaluating the substitution first and then removing explicit literal paths.

Dangerous-removal approval prompts also gain a default two-minute timeout. After three unanswered timeouts in a session, further matching prompts can be denied without being shown again. Server configuration can adjust these defaults.

The new environment overrides are:

- `CLAUDE_CODE_DISABLE_SUBSTITUTION_RM_PROMPT`: disables the added command-substitution prompt check.
- `CLAUDE_CODE_DISABLE_DANGEROUS_RM_TIMEOUT`: disables the new dangerous-removal timeout behavior.

Evidence: Removal-target checks and bounded approval handling (search for `"on statically-unresolvable target: command substitution output"`, `"A backslash-only target is the drive root"`, and `"tengu_splendid_horizon"`).


### Recover sign-in state after another session logs in

A running session can now notice credentials updated by another session, recheck authentication, and refresh login-dependent state. This reduces the need to restart a session that is showing a sign-in notice after completing authentication elsewhere.

Managed settings must refresh successfully before dependent connectors and other account-sensitive surfaces are updated. The controlling flag defaults to enabled.

Evidence: Credential-change watcher and adoption flow (search for `"tengu_streamed_thimble"` and `"sibling-login watch: the managed-settings refresh"`).

## Bug Fixes

- Incomplete streamed responses are now detected when a stream ends inside an open content block or before the response reaches a valid terminal state. Error messages distinguish incomplete responses from malformed streams instead of silently treating partial output as complete. Evidence: search for `"Stream ended cleanly inside open block"` and `"Part of the response never arrived"`.

- Tool calls are cancelled and accounted for when a turn fails because of an image or model error. Cancellation messages explain that an already-started call may have had effects. Evidence: search for `"An image in this turn could not be sent to the API"` and `"The turn ended on an error, so this tool call was cancelled"`.

- Slow-starting stdio MCP servers get a targeted recovery attempt when a timed-out negotiation probe causes initialization to fail with an unsupported-protocol error. The CLI restarts the server once without that probe, within the remaining connection budget. Evidence: search for `"stdio server rejected initialize with -32022"`.

- Transient failures to save login credentials now produce actionable errors, including guidance to unlock the macOS keychain when applicable. Evidence: search for `"Couldn't save your login. If your Mac's keychain is locked"`.

- Bedrock and Vertex setup restarts now preserve session context more carefully and carry the selected model only when the provider, region, project, and credential context still match. Restarts are refused when they would orphan background work or lose session restrictions. Evidence: search for `"Provider-setup restart:"` and `"Work is running in the background, and restarting would orphan it"`.

- Sessions explicitly pinned to a missing working directory no longer silently recover their shell into another directory. The error explains that absolute-path file tools can still be used to restore it. Evidence: search for `"no longer exists and the session is pinned to it"`.

- Missed one-shot scheduled tasks remain in `scheduled_tasks.json` if their notification handler throws, allowing a later session to surface them. Evidence: search for `"missed one-shot task(s); they stay in scheduled_tasks.json for a later session"`.

- Emergency context compaction gains an additional recovery attempt that summarizes the opening conversation round before falling back to dropping earlier content. Evidence: search for `"summarizing the opening round alone first"`.

- Thinking controls now respect model capabilities that prohibit disabling thinking, with an explicit explanation instead of offering an unsupported state. Evidence: search for `"Thinking can't be turned off for"` and `"rejects_disabled_thinking"`.

- MCP resource listings omit app UI resources identified by `ui://` or the `text/html;profile=mcp-app` MIME profile. These remain readable explicitly by URI, but no longer clutter the model’s general resource listing. Evidence: search for `"MCP Apps UI resource(s) left out of"`.

- Background-task recovery distinguishes tasks interrupted by a restart from tasks that finished before the restart but whose results were never delivered. The latter point Claude to recorded output files instead of being described as unfinished work. Evidence: search for `"These background tasks finished before the restart, but their results were not delivered to you"`.

- Auto mode now handles explicit API requests to wait with retry guidance and denial of actions that still require classifier review. The explanation distinguishes temporary unavailability from a judgment that the action itself is unsafe. Evidence: search for `"Auto mode classifier told to wait by the API, denying (fail closed)"`.

## In Development


### Create new cloud sessions in print mode [In Development]

What: Infrastructure is added for starting a new cloud task with `claude -p --cloud`, waiting for its result, and returning text or JSON output.

Status: Stubbed — the launch gate returns `false` in this build.

Details:

- The implementation accepts a task through the prompt, the cloud-option value, or stdin.
- It handles session startup failures, completed results, interruption, and questions an unattended run cannot answer.
- This is separate from the pre-existing ability to send a prompt to an existing cloud session.
- Creating a new cloud session in print mode is not enabled by this release.

Evidence: The CLI passes a hardcoded-false gate into `"cloudPrintEnabled"`; the unreachable runner contains `"Error: claude -p --cloud needs a task"`.


### MCP step-up re-authentication [In Development]

What: An interactive MCP tool call can offer browser re-authentication when an HTTP server requires additional OAuth scope.

Status: Feature-flagged — **[Gradual Rollout]**, with `tengu_mcp_step_up_auth_dialog` defaulting to `false`.

Details:

- The dialog offers “Re-authenticate in browser” or “Not now.”
- Successful authorization reconnects the server and retries the tool call once.
- Declining leaves that tool call failed while other tools continue working.
- The implementation is restricted to eligible interactive main-session calls; it does not provide this dialog to headless runs or subagents.
- Cancelling the browser authorization can leave the server signed out until the user reconnects through `/mcp`.

Evidence: OAuth challenge handling and consent dialog (search for `"tengu_mcp_step_up_auth_dialog"`, `"Re-authenticate in browser"`, and `"needs additional permissions for this tool"`).


### URL-based requests from traditional MCP servers [In Development]

What: Capability negotiation is added so eligible MCP servers can request URL-based user interactions alongside form-based requests.

Status: Feature-flagged — **[Gradual Rollout]** for the traditional connection path.

Details:

- The new capability declaration includes both `form` and `url` elicitation.
- Traditional server connections require `tengu_mcp_legacy_url_elicitation`, which defaults to `false`.
- A server denylist and a per-server compatibility option can suppress the expanded declaration.

Evidence: MCP initialization capability selection (search for `"tengu_mcp_url_elicitation"`, `"tengu_mcp_legacy_url_elicitation"`, and `"bareElicitationCapability"`).

## Notes

This comparison covers **2.1.280 → 2.1.281**. Claims were checked against both analysis snapshots and the original split Bun module sources; module ordering, wrappers, and identifier changes are excluded. Availability statements describe the shipped code and its defaults, not independently observed server rollout status.

Older versions reject boolean values for `attribution`. For settings shared across versions, retain the compatible object form:

```json
{
  "attribution": {
    "commit": "",
    "pr": "",
    "sessionUrl": false
  }
}
```


Generated with:
- tool: `harness-investigations@28c465c-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.281.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.281.txt`
- source modules: `archive/claude-code/original/cli-v2.1.281.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
