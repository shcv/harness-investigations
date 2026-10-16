# Changelog for version 2.1.302

## Summary

Version 2.1.302 adds options to show account-accessible models unknown to this CLI release and to use models outside a signed client-data document’s coverage. It also improves idle-compaction controls, cloud-session feedback, connected-folder permissions, and Artifact publishing. A new transcript-chart implementation ships behind a server-controlled gate that defaults to off.

## New Features


### Show Additional Account-Accessible Models

What: A new flag lets the model picker offer models your account can access even when this Claude Code version does not recognize them.

Usage:
```bash
claude --include-unsupported-models
```

Then open `/model`.

Details:

- Extends the account-provided model catalog; it does not grant access to additional models.
- Models with an explicit minimum Claude Code version remain subject to that requirement.
- The option is also forwarded when launching teammate processes.
- The flag is hidden from ordinary help output, but its parser and catalog-filtering behavior are implemented.

Evidence: Model-catalog filtering checks `includeUnsupportedModels` before excluding unknown models (search for `"--include-unsupported-models"` and `"Offer models your account can use that this version of Claude Code does not know"`). These identifiers are absent from 2.1.301.


### Allow Models Outside Signed Configuration Coverage

What: Sessions using `--client-data-url` can explicitly continue with a model that has no matching entry in the signed configuration document.

Usage:
```bash
claude --client-data-url "$SIGNED_CONFIG_URL" \
  --model "$MODEL_ID" \
  --allow-other-models
```

Alternatively:
```bash
CLAUDE_CODE_ALLOW_OTHER_MODELS=1 claude \
  --client-data-url "$SIGNED_CONFIG_URL" \
  --model "$MODEL_ID"
```

Details:

- Without the override, an uncovered selected model still causes startup to fail.
- For an uncovered model, none of the document’s per-model client data is applied.
- The override also permits startup when the document contains no model entries.
- Loading and verifying the document remain required; this option bypasses the model-coverage check.

Evidence: The startup coverage check now recognizes `CLAUDE_CODE_ALLOW_OTHER_MODELS` (search for `"--allow-other-models"` and `"applying none of its per-model client data"`). Both the flag and environment variable are absent from 2.1.301.

## Improvements


### Idle Compaction Control in `/config`

Eligible sessions now show an “Idle compaction” toggle in `/config`. Idle-compaction notifications also explain how to disable it through settings:

```json
{
  "idleCompaction": false
}
```

The setting and idle-compaction implementation already existed. This release adds the interactive control and clearer guidance. The control appears only when the rollout configuration supports an active idle-compaction mode; setting it to `true` does not independently enable the feature.

Evidence: Conditional configuration row and updated completion messages (search for `"Idle compaction"`, `"tengu_sunny_locket"`, and `"turn off with \"idleCompaction\": false in settings.json"`).


### Better Cloud Starting-Commit Selection

Cloud launches improve their search for a usable pushed commit when the current branch is not available remotely.

The search now considers branch-creation history, upstream relationships, and remote references at relevant commits before falling back to a broader search. GitHub branch checks can also identify remote-tracking information that no longer matches GitHub.

Launch messages explain which commit or branch the cloud session will use and which later commits or uncommitted changes remain on your computer.

Evidence: Branch-origin inspection and remote preflight checks (search for `"branch: Created from "`, `"/v1/code/github/get-batch-branch-status"`, and `"the newest commit beneath it that"`).


### Clearer Cloud Startup and Resume Failures

Remote-session setup now distinguishes failed startup from failed resume. If startup fails while messages are queued, the transcript explicitly says those messages were not sent and tells you to resend them.

While attached to a remote session, `/resume` also explains how to leave the attachment before opening a local conversation.

Evidence: Remote setup status and queue feedback (search for `"Cloud session didn't resume"`, `"Cloud session didn't start"`, `"not sent — the cloud session didn't start"`, and `"/resume can't open this computer's conversations"`).


### Capability-Aware Remote “Send Now”

The terminal’s remote “Send now” path checks whether the attached worker supports the operation. Unsupported sessions receive an actionable message explaining that Escape can interrupt the turn so the message can be sent.

Evidence: Remote worker capability check and fallback notification (search for `"Send now isn't available here · esc to interrupt and send"`).


### Clearer Connected-Folder Consent and Directory Access

Connected-computer folder requests can now display a dedicated approval card naming the folder and computer. The explanation states that the cloud session may run commands and read or change files there under that computer’s sandbox, rules, and hooks.

For integrations using the served-file protocol, the new `ListDirectoryForRemote` operation returns bounded directory listings, including directory and symlink information. It requires permission context and rejects requests when the workspace has moved.

The MCP server also accepts a validated workspace-root hint for folder registration, with invalid or private-folder roots rejected.

Evidence: Folder approval rendering and served-file handlers (search for `"Let this cloud session use a folder on your computer?"`, `"ListDirectoryForRemote"`, and `"CLAUDE_CODE_MCP_SERVE_WORKSPACE_ROOT"`). Folder-request infrastructure existed previously; the dedicated card and directory-listing handler are additions.


### Artifact Publishing Handles Missing Copies More Carefully

Artifact publishes can preserve useful changes when some files copied from another Artifact are unavailable.

Details:

- Safe partial publishes report which copied files were omitted.
- An omitted path retains its existing file, if any.
- Publishes that remove or replace files are refused when missing copies could cause unintended deletion.
- The response explains how to retry while preserving existing content.
- Older servers that reject the new request field are handled through a compatibility retry.

Evidence: Partial-copy handling and deletion safeguards (search for `"leave_out_missing"`, `"the other files in this publish were saved"`, and `"publishing without the copies could remove a file"`).


### Better Guidance for Skills Moved Into Plugins

When a previously listed skill is superseded by a synced plugin skill, invoking it now identifies the replacement command. If its plugin is disabled, the message directs you to `/plugin`.

Plugin inspection errors also explain that built-in plugins are listed in the interactive `/plugin` Installed tab rather than `claude plugin list`.

Evidence: Replacement-skill messages and plugin discovery guidance (search for `"is now the plugin skill"`, `"which is turned off. Check /plugin"`, and `"Built-in plugins don't appear in"`).


### More Useful Background-Agent Progress Labels

Background-agent labels can now be generated from recent activity notes, following the configured language or the predominant language of those notes. The instructions allow an accurate previous label to remain while the agent continues the same activity.

Evidence: Activity-note summarization and language selection (search for `"You write a 3-5 word progress label for a background agent"` and `"Write the label in the predominant language of the notes"`).


### More Visible Prompt Feedback

Several terminal actions now provide compact feedback in the prompt’s hint row, including copying selections, finding no clipboard image, and editing queued shell commands.

Attempting to pull a queued shell command into a nonempty draft now explains that the input must first be cleared.

Evidence: Action-specific hint text (search for `"copied · paste with prefix + ]"`, `"no image · over SSH, try scp"`, and `"clear input to edit shell command"`).


### MCP End-Turn Requests Can Honor Stop Hooks

MCP tools can now request that an end-turn response still pass through Stop hooks:

```json
{
  "_meta": {
    "claude/endTurn": true,
    "claude/endTurnHonorsStopHooks": true
  }
}
```

This lets a tool request completion while allowing a Stop hook to require further work. Existing end-turn responses without the additional field retain their separate handling.

The new path is controlled by `tengu_glittery_mitten`, which defaults to enabled.

Evidence: MCP response metadata parsing and Stop-hook dispatch (search for `"claude/endTurnHonorsStopHooks"` and `"tengu_glittery_mitten"`).


### Clearer Organization-Policy Handling in Cloud Sessions

When a cloud session obtains managed policy from its organization, machine-managed settings files are treated as additional restrictions. New warnings identify settings that were ignored or only partly retained.

In this context, a machine file’s `disableAllHooks` request is interpreted as `allowManagedHooksOnly`, preserving organizational managed hooks.

Evidence: Restrictive settings processing and diagnostics (search for `"a managed settings file may only restrict"` and `"was taken as \"allowManagedHooksOnly\""`).


### Claude Design Transition Notices

The existing Design integration now displays a notice that standalone Claude Design at `claude.ai/design` closes by December 14, 2026. Its sign-in guidance clarifies that the authorization applies to the standalone service and remains relevant to `/design-sync` or `/design consent` during the transition.

Evidence: Design integration and authorization notices (search for `"Standalone Claude Design (claude.ai/design) closes by December 14, 2026"` and `"This sign-in is only for standalone Claude Design"`).

## Bug Fixes

- Image reads now enforce a 128 MiB input bound for the affected local-file path, including streamed input from pipes or devices. Oversized images receive guidance to resize or export a smaller copy. Search for `"File over the image read limit"` and `"Image stream over the read limit"`.

- Claude Test now watches for login or plan changes and removes its browser helper when the session becomes ineligible or its login cannot be checked. Failure messages explain when to retry `/claude-test`, sign in again, or restart. Search for `"Claude Test did not run: the Claude Code login or plan changed"` and `"claude-test: could not watch who is signed in"`.

- Built-in plugin MCP tools now recheck whether their providing plugin permits the server connection before executing a call. A refusal produces an explicit tool error. Search for `"was not called: the plugin that provides it refused this call"`.

- Turning off a synced claude.ai skill now also attempts to persist the corresponding plugin’s disabled state in local settings. If writing is unsafe or fails, the plugin remains suppressed during loading. Search for `"Could not turn off a synced plugin in local settings"` and `"It is held off at each load instead"`.

- MCP skill loading now rejects a connection that no longer matches the server configuration under which the skill was listed, with instructions to reconnect or start a fresh task. Search for `"is not connected as it was when this skill was listed"`.

- Auto-mode classifier selection now validates environment overrides against organization model policy and compatibility with escalated safety checks. Invalid overrides fall back with a specific explanation; shadowed overrides are also identified. Search for `"Auto mode classifier: ignoring CLAUDE_CODE_AUTO_MODE_MODEL"` and `"the API's safeguards refuse the classifier's escalated check on it"`.

- Background sessions launched from another folder now receive a specific explanation when a shell-configured model gateway was withheld, including how to respawn from the session’s own folder or configure the gateway in settings. Search for `"CLAUDE_BG_GATEWAY_WITHHELD"` and `"No LLM gateway: a gateway set in your shell isn't passed"`.

- Stored-transcript inspection in diskless sessions now conservatively retains a conversation when it cannot determine whether the transcript contains content. Search for `"could not read the stored transcript to its end; keeping it as if it holds a conversation"`.

- Session Git preparation handles a non-directory `.git/refs/heads` placeholder left by reftable repositories. Newly prepared repositories also explicitly select file-based refs. Search for `"a reftable repository leaves a placeholder file there"` and `"init.defaultRefFormat=files"`.

- Monitor-command execution adds explicit refusal paths for mismatched checked commands, invalid approval associations, and replaying a call that already started. Search for `"RunMonitorCommand was not run again: this very call was already started here once"` and `"its command is not the command of the Monitor call that was checked"`.

## In Development

These implementations ship in the CLI but require server-controlled enablement or eligibility. Their presence does not establish general availability.


### Transcript Charts [In Development]

What: A built-in chart plugin can draw data directly in the conversation, including automatic charts beneath suitable MCP metric results.

Status: Feature-flagged; `tengu_joyful_otter` defaults to `false`.

Usage when enabled: Ask Claude to chart a tool result, or provide a small table and request a chart.

Details:

- Provides the `mcp__easel__chart` tool.
- Supports lines, columns, horizontal bars, sparklines, and part-to-whole displays.
- Accepts tables under 64 KiB, including JSON records, CSV, TSV, and Markdown tables.
- Recognizes metric formats from services including Prometheus, Grafana, and Datadog.
- Includes terminal rendering and screen-reader text.
- Automatic charts default to on within the enabled plugin. “Auto charts” can be disabled in `/config`, and individual MCP servers can be excluded.
- The availability check currently permits Linux and macOS, requires settled policy information, and excludes HIPAA- or ZDR-tainted sessions.
- File-backed or truncated tool results are not automatically treated as complete chart data.

Evidence: Original module sources contain chart registration, rendering, configuration, and the disabled-by-default availability check (search for `"mcp__easel__chart"`, `"Auto charts: servers to skip"`, and `"tengu_joyful_otter"`). This implementation is absent from 2.1.301.


### API Credit-Link Offer Notices [In Development]

What: Eligible accounts may receive an in-session notice associated with an API credit-link offer.

Status: Feature-flagged and eligibility-dependent.

Details:

- Notice text comes from `tengu_snug_storm`; without valid configured text, the notice is unavailable.
- Display is separately controlled by `tengu_radiant_fox`, which defaults to off.
- Eligibility is checked through an organization-specific endpoint and cached.
- Additional account, session, and impression limits apply.
- The source does not establish an offer amount, redemption terms, or a general launch date.

Evidence: Offer eligibility requests and announcement registration (search for `"api-credit-link"`, `"tengu_snug_storm"`, `"tengu_radiant_fox"`, and `"/api/oauth/organizations/:orgUUID/quirky-lollipop/link-offer"`). These are absent from 2.1.301.


Generated with:
- tool: `harness-investigations@7db407c-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.302.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.302.txt`
- source modules: `archive/claude-code/original/cli-v2.1.302.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
