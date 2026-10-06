# Changelog for version 2.1.292

## Summary

Compared with v2.1.291, this release adds mod-provided prompt autocomplete and improves plugin model calls, overload retries, and compaction after switching models. It also tightens background memory permissions and improves session recovery, theme persistence, and file-search errors. Organization plugin publishing, artifact history, and several cloud-session enhancements have new infrastructure with availability restrictions described below.

## New Features


### Mod-Provided Prompt Autocomplete

What: Mods can supply suggestions while you type in the prompt composer through the new `prompt.autocomplete` hook.

Usage: With a mod implementing this hook installed, type a token, navigate its suggestions, and accept one with Tab, Enter, or a click.

Details:

- The hook receives the prompt text, cursor position, current token, and token start position.
- It returns a `suggestions` array. Each suggestion supplies replacement `text` and can include a `label` and `description`.
- Mod suggestions appear alongside the existing autocomplete interface.
- Acceptance replaces the token immediately before the cursor.
- Stale responses are discarded as you continue typing. A failed hook does not prevent the native suggestions from working.
- This is an extension capability; it does not supply a new built-in suggestion provider by itself.

Evidence: Hook registration, argument/result validation, and terminal-composer integration all use `"prompt.autocomplete"`, which is absent from v2.1.291.

## Improvements


### Configurable Backoff for Overloaded API Requests

The new `CLAUDE_CODE_OVERLOADED_RETRY_BASE_DELAY_MS` environment variable lets you adjust the base delay used when retrying overload errors.

Usage:

```bash
CLAUDE_CODE_OVERLOADED_RETRY_BASE_DELAY_MS=2000 claude
```

The value is in milliseconds. It changes the base used by the retry calculation; exponential backoff, jitter, and applicable server retry guidance still apply. Other retry categories retain their existing handling.

Evidence: The overload-error retry branch reads `"CLAUDE_CODE_OVERLOADED_RETRY_BASE_DELAY_MS"`; this variable is absent from v2.1.291.


### Cacheable Blocks in Mod Model Calls

The existing `$.model.complete` interface now accepts prompt and system text as arrays of blocks, allowing mod authors to mark reusable text for prompt caching.

Usage:

```javascript
await $.model.complete({
  model: "sonnet",
  prompt: [
    { text: "Reusable reference material", cache: true },
    { text: "Answer this specific question." }
  ]
});
```

Details:

- String prompts remain supported.
- Block arrays preserve cache markers when constructing the model request.
- Existing hook processing can still receive the combined text.
- Cache markers are removed when prompt caching is disabled for the selected model.

Evidence: Input normalization and request construction use `"promptBlocks"` and `"systemBlocks"`; the new validation describes a prompt as a string or blocks containing `"text"` and optional `"cache"`.


### Compaction Recovery After Switching to a Smaller Context Window

When a conversation no longer fits after a model switch, compaction can attempt to use the previously used model if it has a larger context window and remains available to the account. This provides another route to compact the conversation and continue with the selected model.

Details:

- The larger-model attempt is bounded to a single compaction API attempt.
- An explicitly selected compaction model takes precedence.
- If that attempt fails, the normal compaction path remains available.
- Model availability and account restrictions still apply.
- The new controlling flag defaults to enabled, although server configuration can disable it.

Evidence: Larger-context model selection and bounded compaction retries are controlled by `"tengu_tidy_axolotl"` with a default of `!0`; the attempt is identified by `"compact_larger_model"`.


### More Consistent Marketplace-Source Plugin Installation

The existing marketplace-source installation workflow now has more consistent handling between the plugin CLI and interactive installation.

Usage:

```bash
claude plugin install my-plugin --marketplace owner/repository
```

Details:

- Installation validates the marketplace source and plugin name through shared handling.
- Errors distinguish failure to install a plugin from successful addition of its marketplace.
- If the marketplace was added before installation failed, the message explains that it remains declared in user settings.

Marketplace-source installation already existed in v2.1.291; this is an improvement to that workflow.

Evidence: CLI wiring uses `"--marketplace <source>"`. Partial-success reporting includes `"The marketplace itself was added, and is declared in user settings."`


### More Informative Artifact Listings

For sessions offering the existing artifact tool, listings now explain their ordering and incompleteness more precisely.

Details:

- Own artifacts are described as ordered by recent opening or updating.
- Combined listings distinguish own artifacts from shared artifacts.
- Incomplete results report that their count is a lower bound.
- When raising the limit cannot reach every artifact, the response suggests requesting the artifact’s link or listing appropriate scopes separately.

Evidence: Updated listing output includes `"Not every artifact could be listed, so the count is a lower bound"` and `"most recently opened or updated first"`.


### Clearer PDF Page-Selection Errors

Invalid PDF page selections now explain the accepted syntax and how to read multiple separate ranges.

Usage: Ask Claude to read page `3` or the range `1-5`. Separate ranges require separate reads.

This clarifies the existing restriction rather than adding support for comma-separated selections.

Evidence: The validation message says `"Give one page"` and `"To read several pages or ranges, read each one separately."`

## Bug Fixes

- **Theme changes report persistence failures accurately.** `/theme` and onboarding now report failed or refused saves instead of presenting them as successful. Custom-theme feedback distinguishes saving a theme from activating it. Search for `"Couldn't save Theme"`, `"Saved custom theme"`, and `"/theme: config.set failed:"`.

- **Background memory saving checks write permissions before proceeding.** When an applicable rule denies writes or requires approval, background saving pauses and explains why: the background agent cannot ask for approval. Search for `"Claude isn't saving memories to"` and `"needs your approval for each write, and background saving can't ask"`.

- **Memory-agent calls fail closed when permission checks cannot complete.** A `PreToolUse` hook requiring confirmation is treated as a denial for the headless memory agent. Additional checks restrict its tool access and Windows shell commands under outside-directory read restrictions. Search for `"the memory agent could not evaluate configured permission rules; failing closed"`, `"MCP tools are not available to the memory agent"`, and `"even split by quotes or a backslash"`.

- **Resuming a plugin-defined agent checks that its implementation and tools remain available.** Resume now rejects missing plugin implementations, disallowed tools, and agent types no longer offered by the session. Search for `"so the agent was not resumed"` and `"is not offered in this session"`.

- **Plan-mode restoration covers additional interactive resume paths.** The resume picker and interactive resume operations share the restoration logic, while preserving explicit startup permission choices and avoiding restoration into forked sessions. Search for `"planModeOnInteractiveResume"`, `"interactive_picker"`, and `"interactive_slash"`.

- **Future dynamic `/loop` wakeups can survive session resume.** Eligible sessions persist pending wakeup metadata and restore a matching future wakeup from the recorded tool call and result. Expired or mismatched wakeups are not rearmed. Search for `".pending-wakeup"` and `"re-armed pending wakeup for"`.

- **Rewinding a cloud conversation can restore notifications consumed by an unfinished turn.** Notifications read by an interrupted or failed turn can become unread again when that turn is removed, so they remain available for subsequent processing. Search for `"notification(s) that an interrupted or failed turn had read are unread again"`.

- **Cloud-worker recovery restores valid thinking preferences.** Recorded thinking budgets and display preferences are checked before restoration; unsupported display modes are left out rather than applied blindly. Search for `"thinking budget and display in the worker record: applied"` and `"thinking display 'highlights'"`.

- **File-search failures provide safer, actionable guidance.** Grep reports when ripgrep cannot read the supplied path or did not receive the file Claude Code opened. Its recovery guidance avoids bypassing those restrictions with a recursive shell search. Search for `"Search failed: ripgrep could not read the path it was given"` and `"the file Claude Code opened was not passed to ripgrep"`.

- **Sandbox protections are rechecked when trusted paths move.** Changes to read-deny or credential-mask paths after sandboxed execution begins can cause the running configuration to be narrowed. Failed rechecks also take the restrictive path. Search for `"A trusted read-deny or credential-mask path moved after the session's first sandboxed command"`.

- **Plugin disable and uninstall operations handle refused settings reads conservatively.** Additional settings-file reads use screened handling; an unreadable or refused legacy local settings file is counted as potentially present rather than assumed absent. Search for `"readScreenedSettingsFile refused it"` and `"counting it as present"`.

- **Plugin commands account for managed-settings approval.** If required organizational settings approval cannot be requested in the current command, the CLI explains how to approve them interactively before retrying. Search for `"managed settings need your approval"` and `"then run this command again"`.

- **Hidden workflow scripts cannot be silently changed during resume.** Such runs must resume with their original, unedited script. A changed script requires a new run. Search for `"it can only be resumed with its original script file, unedited"`.

- **Branch-based Ultrareview can stop before uploading code when required preflight checks are unavailable.** The branch-preflight requirement defaults to enabled and can be controlled by server configuration. Search for `"branch_preflight_required"` and `"it stopped before uploading your code"`.

## In Development

These changes add functionality with disabled defaults, host-controlled availability, or an inactive entry point. Their presence in the package does not establish availability in an ordinary CLI session.


### Publishing Plugins to an Organization [In Development]

What: A new publishing workflow is designed to submit a local plugin or mod folder to the signed-in organization’s library on claude.ai.

Status: Feature-flagged; `"tengu_copper_gazette"` defaults to false.

Details:

- The implementation validates the folder, prepares an upload, and presents a confirmation describing what will be sent.
- Confirmation is tied to the reviewed submission; changes to the folder can invalidate it.
- Uploads are scanned and submitted according to organizational policy. Some organizations require administrator review.
- It requires a suitable claude.ai sign-in and an attended approval surface.
- Cloud-session publishing, third-party providers, `--bare`, and disabled nonessential traffic have explicit refusal paths.
- If enabled for your account, the intended interaction is to ask Claude to publish the plugin folder to your organization.

Evidence: The new tool description starts with `"Publish a plugin folder on this machine"`. Its availability check uses `"tengu_copper_gazette"` with a false default.


### Artifact Version History [In Development]

What: Supporting sessions can list an artifact’s retained versions and download an earlier version’s page to a local file.

Status: Host-controlled; availability depends on `"CLAUDE_CODE_ARTIFACT_VERSIONS"`.

Details:

- Listing versions uses the artifact URL; reading a particular version also supplies its version identifier.
- Historical access requires confirmed ownership. Shared access alone is insufficient.
- Permission and ownership checks fail closed.
- Reading history does not change the live artifact.
- Restoring an earlier page requires a separate publish operation. Other artifact files are not restored as a complete historical snapshot.

Evidence: The availability check reads `"CLAUDE_CODE_ARTIFACT_VERSIONS"`. The implementation includes `"Listing an artifact's versions is read-only"` and `"An artifact's earlier versions are not available in this session."`


### Cloud Artifact Viewer Previews [In Development]

What: A new renderer is intended to open a local HTML page in the real artifact viewer and return a screenshot before publication.

Status: Disabled in this build.

Details:

- The implementation includes viewer downloading, headless-browser execution, file checks, and screenshot results.
- Previewing is designed to leave the artifact unpublished.
- Despite the emulator configuration and rollout checks, engine selection additionally requires a hardcoded switch whose value is `{on: !1}`.
- Setting the emulator environment variable alone does not activate this path.

Evidence: The renderer uses `"CLAUDE_CODE_ARTIFACT_PREVIEW_EMULATOR"` and describes `"Look at a local page in the real artifact viewer inside this cloud session. Nothing is published."` The emulator selection is blocked by the hardcoded off switch.


### Screen-Reader Suggestion Navigation [In Development]

What: Additional autocomplete-navigation behavior is being added for screen-reader mode.

Status: Feature-flagged; `"tengu_ax_sr_suggestion_nav"` defaults to false.

Details:

- The new path requires screen-reader mode as well as its separate rollout gate.
- It tracks the suggestion explicitly selected through navigation and preserves that selection through suggestion updates.
- Existing screen-reader mode remains separate from this new capability.

Evidence: The screen-reader controller’s suggestion-navigation check reads `"tengu_ax_sr_suggestion_nav"` with a false default.


### Reporting Programs Left Running by a Cloud Worker [In Development]

What: Cloud-worker recovery can identify subprocesses left running by an earlier worker and inform the resumed session about them.

Status: Feature-flagged; `"tengu_keen_dolphin"` defaults to false.

Details:

- The implementation records bounded process information and rechecks whether recorded processes or process groups remain alive.
- It distinguishes running, gone, and uncertain states.
- This supports recovery awareness; it does not establish terminal reattachment or restoration of a process’s output stream.

Evidence: Process tracking and recovery reporting use `"tengu_keen_dolphin"` and `"left_running_programs"`.


### Serialized Cloud WebFetch Approvals [In Development]

What: Cloud WebFetch permission requests can be queued so concurrent fetches do not all ask for approval at once.

Status: Feature-flagged; `"tengu_orderly_lantern"` defaults to false.

Details:

- Queued requests recheck permissions before prompting.
- Approvals for URLs or origins can avoid redundant questions during the turn.
- Unanswered requests have withdrawal and retry handling.
- After an unanswered request, subsequent requests can wait for a user reply before asking again.

Evidence: The queue is controlled by `"tengu_orderly_lantern"`. New explanations include `"was not answered in time and was withdrawn"` and `"the request for this URL was not sent to them"`.


### Additional Handling for Cloud Attachments Still Arriving [In Development]

What: Cloud sessions gain optional handling for prompts and tool calls that arrive before their attached files finish staging.

Status: Feature-flagged; the new relevant gates default to false.

Details:

- `"tengu_slate_marten"` extends the existing gated ahead-of-files path to PDFs.
- `"tengu_cozy_kite"` permits bounded waiting before a tool call while recently staged files are still pending.
- The wait is cancellable and reports a files-arriving state.
- These additions do not make attachment processing universally synchronous.

Evidence: PDF-aware selection uses `"tengu_slate_marten"` and `"on_with_pdfs"`; tool-call waiting uses `"tengu_cozy_kite"` and `"files_arriving"`.


### Context-Based Project Write Limits [In Development]

What: Project-document writes can receive a size budget derived from the model’s effective context window.

Status: Feature-flagged; `"tengu_breezy_pelican"` defaults to null.

Details:

- Supported configurations apply the budget either always or immediately after compaction.
- The calculation applies to effective context windows of at most 200,000 tokens.
- The default fraction is one sixth of the context window, with a validated configurable fraction.
- This adds an optional policy to the existing Project tool.

Evidence: Budget calculation reads `"tengu_breezy_pelican"` and recognizes `"always"` and `"after_compaction"`.


### Usage-Credit Consent for Additional Model Families [In Development]

What: The existing usage-credit consent handling can be extended beyond its previous Fable-specific coverage.

Status: Feature-flagged; `"tengu_calm_seal"` defaults to null.

Details:

- Additional model families must appear in a server-provided list.
- Existing Fable handling remains supported.
- The code does not establish that any additional family is currently enabled or introduce a confirmed new model release.

Evidence: Model-family eligibility checks use `"tengu_calm_seal"`, accepting additional families only from its configured list.


Generated with:
- tool: `harness-investigations@a993ec8-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.292.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.292.txt`
- source modules: `archive/claude-code/original/cli-v2.1.292.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
