# Changelog for version 2.1.293

## Summary

Version 2.1.293 adds client-side recognition of Haiku 5.5 and lets plugin authors control whether registered tools are deferred behind tool search. It also improves background-session handoffs, protects conversation summaries in Remote Control, and strengthens safeguards around remote hooks, MCP calls, and project document saves. Task file attachments and several recovery mechanisms ship behind server-controlled gates.


## New Features


### Haiku 5.5 Model Recognition

What: Claude Code now recognizes `claude-haiku-5-5`, including its provider identifiers and model capabilities.

Usage:
```bash
claude --model claude-haiku-5-5
```

Details:

- Adds model-name normalization and catalog entries for first-party, Bedrock, Vertex, Foundry, and other supported providers.
- Adds `VERTEX_REGION_CLAUDE_HAIKU_5_5` for configuring its Vertex region.
- The catalog declares support for effort levels and adaptive thinking.
- This is client-side support; successful use still requires the model to be available through your account and provider.
- The built-in fallback for the `haiku` alias remains Haiku 4.5 unless another configuration selects a different model.

Evidence: Model catalog and provider mappings (search for `"claude-haiku-5-5"`, `"VERTEX_REGION_CLAUDE_HAIKU_5_5"`, and `"haiku_5_5_early_stopping_guidance"`). These identifiers are absent from 2.1.292.


### Deferral Options for Plugin-Registered Tools

What: Plugin authors can now specify `isDeferred` when registering a tool through `$.tool.register`.

Usage:
```javascript
await $.tool.register({
  name: "project_status",
  description: "Report the project's current status",
  inputSchema: { type: "object", properties: {} },
  isDeferred: false
});
```

Details:

- `isDeferred: false` publishes the tool with `_meta["anthropic/alwaysLoad"]` set to `true`.
- `isDeferred: true` publishes that metadata as `false`, allowing the tool to remain behind tool search.
- Omitting the option preserves the existing default behavior.
- Non-boolean values are rejected.

Evidence: Registration validation and MCP tool-list metadata (search for `"isDeferred must be true or false"`, `"$.tool.register"`, and `"anthropic/alwaysLoad"`). Tool registration and `alwaysLoad` already existed; passing this option through registration is new.


## Improvements


### Queued Messages Survive Background Handoffs

Moving an existing session into the background now carries eligible queued prompts into the background process instead of leaving them behind.

Details:

- Carries prompt text and associated paste data, including images.
- Checks the carried data against the handoff’s integrity binding.
- Avoids replaying messages already present in the transcript.
- Refuses the move when queued messages cannot safely be carried, explaining that you should wait until Claude has read them.

Usage: Use the existing background-session action or left-arrow workflow while messages are queued.

Evidence: Queued-prompt transfer and replay checks (search for `"adopt.json.queued-prompts"`, `"CLAUDE_BG_CARRIED_PROMPTS_SHA256"`, and `"queued"` near `"can't move to the background"`).


### Backgrounding Protects Unsent Drafts and Pending Questions

A deferred background move now checks whether you have started typing or whether Claude is waiting for an answer.

- Unsent input cancels the move and asks you to send or clear the draft.
- A pending question keeps the move waiting instead of skipping the interaction.

Evidence: Background-transition guards (search for `"Backgrounding cancelled — you have unsent text in the input"` and `"Still backgrounding after the current tool — a question is waiting for your answer"`).


### Remote Control Withholds Potentially Sensitive Summaries

Conversation summaries receive additional protection when they could contain account memory.

Details:

- Protects compacted summary messages and command output that repeats a summary.
- Preserves the summary markers when loading and transferring transcript history.
- Shows replacement text remotely while retaining the content in the terminal session.
- Gives resumed conversations an explanation that earlier details were withheld.

Evidence: Summary detection and redaction (search for `"repeatsCompactSummary"`, `"[conversation summary withheld: it may include account memory]"`, and `"command output withheld from Remote Control"`).


### Project Uploads Can Reuse Verified Files in More Session Contexts

The existing project document tool gains additional handling for `project_write` with `local_path`.

Details:

- Supported cloud-backed contexts can upload a file that the session has read or written in full.
- Additional permitted upload/output locations can be used outside the normal working directory.
- These paths require evidence that the file’s contents have not changed since the session examined them.
- Notebook and non-UTF-8 cases require inline `content` instead.
- The new cloud-backed read path applies a 1 MiB limit.

Usage: Ask Claude to read the complete file, then save it to the project. If path upload is refused, use inline content.

Evidence: File provenance checks and cloud-backed reads (search for `"project_write: Read the whole file at local_path first"`, `"project_write: the file at local_path is not what this session read or wrote there"`, and `"project_write: the file at local_path is over 1 MiB"`). Project writes and `local_path` existed previously.


### Project Save Errors Explain What Was Preserved

Failed project saves now distinguish refusals, transient failures, and uncertain outcomes more precisely.

Details:

- Explains whether the existing document remains intact.
- Recommends reading the document before retrying a write whose result is uncertain.
- Limits retries rather than encouraging repeated writes.
- Warns against deleting the existing document to make a retry possible.
- Explains when a delayed save may have created a second document at the same path.

Evidence: Save-stage error handling (search for `"This call changed nothing: the doc at this path is still there"`, `"The new content may have been saved late as a second doc at this path"`, and `"Call project_read on this path before any other write or delete"`).


### Agent Guidance Reflects Available Messaging Tools

Agent listings, completion notifications, and resume instructions now account for whether the calling context actually has a messaging tool.

Details:

- Stops recommending `SendMessage` where it is unavailable.
- Explains when an agent cannot be continued from the current context.
- Warns that relaunching an agent may repeat work already completed.
- Distinguishes an empty listing from a context that cannot message listed sessions.

Evidence: Tool-aware agent guidance (search for `"An agent cannot be continued from this context"`, `"Its report cannot be retrieved from this session"`, and `"No other session appears in this listing right now"`).


### Silent Background Commands Get More Useful Check-Ins

Background-shell check-ins now identify other commands that have also been silent, including their output-file locations.

This helps Claude investigate several quiet or stalled tasks together. The notice still distinguishes a check-in from completion and asks Claude to inspect output and processes before deciding what to do.

Evidence: Grouped shell check-ins (search for `"It speaks for your other background commands too"` and `"no new output for"`).


### Host-Provided Skill Switches Are Respected

CLI skill loading can now honor individual skill switches supplied by a host integration.

Details:

- Enabled through the host-provided `CLAUDE_CODE_DESKTOP_SKILL_SWITCHES` value.
- Applies to account-skill wrapper plugins.
- Reads enabled/disabled entries from the wrapper’s root `manifest.json`.
- Leaves disabled skill folders out of the loaded skill set.
- Refuses to load the wrapper’s skills when its switch manifest is unusable, rather than assuming everything is enabled.

Evidence: Conditional manifest processing during plugin skill loading (search for `"CLAUDE_CODE_DESKTOP_SKILL_SWITCHES"`, `"switched off in its manifest.json"`, and `"Loading no skills from plugin"`).


### Purge Failures Explain What Remains

The existing purge command now gives clearer guidance when cleanup stops early or individual deletions fail.

It explains that some data may remain on disk and recommends rerunning the command, using `--dry-run` to inspect remaining targets, or fixing the reported deletion problem.

Evidence: Interrupted and partial purge reporting (search for `"Purge stopped before it finished"` and `"What could not be deleted is still on disk"`).


### Ignored Bypass Requests Stay Visible

When bypass permissions were requested at launch but ignored because the required consent setting is absent, the terminal now shows a pinned warning.

The warning identifies the user settings file and the relevant `skipDangerousModePermissionPrompt` setting. This improves visibility of an existing consent requirement.

Evidence: Pinned permission-mode notice (search for `"Bypass permissions was requested at launch and ignored"` and `"background-bypass-unconsented"`).


## Bug Fixes

- Remote plugin hooks can no longer authorize or rewrite tool calls executed in a different environment. A changed input can cause the call to be refused; an attempted result replacement leaves the original result intact. Cross-environment permission updates and answers on the user’s behalf are also filtered. Evidence: search for `"A plugin hook tried to change this tool call's input"`, `"A plugin hook tried to replace this tool call's result"`, and `"was not taken as printed"`.

- Diskless cloud sessions now have execution-time guards against running command, script, HTTP, or MCP hooks from the shared server. Unavailable permission-request hooks deny the request instead of implicitly permitting it. Evidence: search for `"a cloud session does not run command, script, HTTP or MCP tool hooks"` and `"hook can't run in this cloud session, so this permission request is denied"`.

- MCP calls are handled more conservatively when a POST may have reached the server but no answer arrived. Additional uncertain outcomes avoid automatic resending, reducing the risk of duplicate side effects. Evidence: search for `"MCP call went out and got no answer"` and `"its POST does not show whether the server got the call"`.

- Cloud-session message failures now distinguish definite failure from uncertain delivery, explaining when the message may have reached the session. Evidence: search for `"Your message may not have reached the cloud session"`.

- Recreated cloud environments can now explicitly report that forwarded settings are gone, including deny/ask rules, `CLAUDE.md`, and preferences. Evidence: search for `"settings_gone"` and `"any user settings forwarded from your machine are not in force here"`.

- Cloud repository uploads now check that linked-worktree Git metadata resolves to the repository under which Claude Code keeps trust and settings. Mismatched or unresolved layouts are refused with recovery guidance. Evidence: search for `"its .git file leads git to another repository"` and `"the folder that keeps this tree’s trust could not be resolved"`.

- Split-index upload guidance no longer recommends deleting `sharedindex.*` files manually. It directs users toward a fresh clone when those files prevent upload. Evidence: search for `"do not delete any of these files by hand: the index may need one of them"`.

- Claude in Chrome file uploads gain stronger checks for credential and device paths, including linked paths, case/Unicode variants, and alternate-stream spellings. Evidence: search for `"claudeInChrome/fileUpload: path refused by its name or place on the pass-through"` and `"the file before a ':stream'"`.

- Chrome permission checks gain a fallback tab lookup after certain timeouts or failures, while checking that recovered tab information agrees with the original lookup. Evidence: search for `"tab_lookup_rescued_after_answer_timeout"` and `"tab_lookup_hosts_differed"`.

- Claude Test eligibility now verifies that cached flag answers belong to the current account and organization. Its agent restrictions also expand protection of credential files and use absolute glob patterns for sensitive configuration paths. Evidence: search for `"claude-test: could not read the account Claude Code's flag client was built with"`, `"Read(~/.config/claude-test/**)"`, and `"Edit(//**/CLAUDE.md)"`.

- The self-hosted runner waits for running hooks to finish before exiting after a terminal orchestrator rejection. Evidence: search for `"running hook(s) to end, then exiting"`.


## In Development

These implementations are present in the CLI but depend on server-controlled gates that default to disabled. The source does not establish which accounts, if any, currently have access.


### File Attachments for Managed Tasks [In Development]

What: Claude will be able to attach local or cloud-environment files when invoking a supported managed-agent server’s `start_task` tool.

Status: Feature-flagged by `tengu_twinkling_cosmos`, default `false`.

Intended input:
```json
{
  "task_description": "Analyze the attached report",
  "files": [
    { "path": "/absolute/path/to/report.csv" }
  ]
}
```

Details:

- Uploads files and converts path entries into server-facing file references.
- Supports up to 20 files, with size and total-upload limits.
- Checks file permissions, credential-like names, regular-file status, hard links, and filename safety.
- Handles local uploads and uploads through a supported cloud environment.
- Cleans up uploaded files when a task call is abandoned.
- Rechecks policy and upload expiry after an approval delay.
- Requires suitable sign-in, organization policy, traffic settings, and server compatibility.

Evidence: Task upload entry point and validation (search for `"tengu_twinkling_cosmos"`, `"Cannot call start_task with these arguments"`, and `"No task was started"`). No related new orphaned tip was found.


### Required Organization Configuration at Startup [In Development]

What: Selected Team or Enterprise sessions can be prevented from starting until organization policy and managed settings have been obtained.

Status: Feature-flagged by `tengu_org_config_required`; defaults include `enabled: false` and a rollout percentage of zero.

Details:

- Selects eligible first-party signed-in sessions by plan and rollout bucket.
- Distinguishes explicit policy refusal from temporary configuration-fetch failures.
- Can accept previously admitted configuration within a configurable grace period.
- Defaults include a 96-hour cache grace period and a six-second wait budget.
- Malformed rollout configuration is treated as disabled.

Evidence: Startup admission checks (search for `"tengu_org_config_required"`, `"graceTtlHours"`, and `"org-config gate"`).


### Recovery of Interrupted MCP Permission Calls [In Development]

What: A resumed session can close an interrupted MCP call cleanly when its tool is no longer available.

Status: Feature-flagged by `tengu_expressive_church`, default `false`.

Details:

- Applies to specific interrupted-turn permission requests after the MCP server reaches a known connection state.
- Can record a denial or an unavailable-tool result so the conversation can proceed.
- Avoids re-executing an unavailable tool.
- Does not apply when the turn was aborted or server state remains unknown.

Evidence: Orphaned-permission recovery conditions (search for `"tengu_expressive_church"` and `"closing the call of the"`).


### User Messages Can Take Priority Over Automatic Recovery [In Development]

What: Eligible automatic recovery work in remote sessions can yield when a human prompt is waiting.

Status: Feature-flagged by `tengu_cosmic_crayon`, default `false`.

Details:

- Checks for queued human prompts.
- Applies only to recovery work marked as able to yield.
- Keeps stop requests and drain-only work from being bypassed.

Evidence: Recovery-queue arbitration (search for `"tengu_cosmic_crayon"` and `"yieldsToPersonPrompt"`).


### Settings-Change Notices for Remotely Served Shell Commands [In Development]

What: Claude Code can detect and report local settings-file changes while a shell command from a cloud session runs.

Status: Feature-flagged by `tengu_violin_endpin`, default `false`; local flag overrides are not accepted by this gate.

Details:

- Compares settings-file identities before and after eligible served shell calls.
- Tracks user, project, local, managed, and launch settings.
- Warns that the command may have changed settings and that nothing was undone.
- The notice detects a concurrent change; it does not prove which process caused it.

Evidence: Before/after settings checks and notices (search for `"tengu_violin_endpin"`, `"served-settings-changed"`, and `"A Claude Code settings file on this computer"`).


## Notes

- Hook authors using remote integrations should review hooks that return permission approvals, input rewrites, or replacement outputs. Those effects now depend on the hook and tool executing in the same environment.
- For project path-upload failures, read the whole file again or provide inline `content`. Do not delete an existing project document to retry a failed replacement.
- This changelog compares **2.1.292 → 2.1.293**. Substantive changes were checked against both prettified versions and the original split-module sources. Rebundling artifacts, internal-only changes, and Desktop-only settings were excluded; backend availability is not inferred from bundled code.


Generated with:
- tool: `harness-investigations@ed78970-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.293.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.293.txt`
- source modules: `archive/claude-code/original/cli-v2.1.293.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
