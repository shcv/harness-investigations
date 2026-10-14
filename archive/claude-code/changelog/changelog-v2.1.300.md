# Changelog for version 2.1.300

## Summary

Version 2.1.300 adds secret scanning to the existing plugin-authoring workflow, a standalone proxy mode for self-hosted runners, and a message-specific prompt-cache control. It strengthens hook and plugin policy enforcement, improves recovery of background MCP tasks, and changes Remote Control sandbox configuration. Console cloud-session sign-in and several compaction improvements ship with activation limits described below.

## New Features


### Secret Scanning Before Sharing a Plugin

What: The existing plugin-authoring workflow can scan a mod’s folder for known key and token formats before it is shared.

Usage: In a session where plugin authoring is available, ask Claude to check the mod before sharing it. The workflow registers `mcp__plugin-authoring__scan_secrets` and can present a “Scan it” confirmation.

Details:

- Reports affected file names and secret types without printing secret values.
- Reads the working files directly; it does not run Git or inspect `.git`.
- Checks Read permissions and reports files it could not scan.
- Skips symbolic links, hard links, Git LFS pointers, and oversized files.
- Limits scanning to 10 MiB per file and 25 MiB overall, with a bounded directory traversal.
- Refuses scanning when compliance policy forbids it, organization policy has not loaded, or managed read hooks cannot be honored.

The scanner has a real implementation wired into the built-in plugin. The fallback message “this build carries no scan” does not mean the shipped scanner is universally stubbed.

Evidence: Scanner registration, permission checks, and filesystem implementation—search for `"scan_secrets"`, `"Secret scan"`, and `"Values are not shown."`.


### Standalone Proxy for Self-Hosted Runners

What: Self-hosted runner sessions can route traffic through an organization’s own HTTPS proxy using session credentials.

Usage: Configure these variables in the runner container before starting a new runner session:

```bash
export CCR_AGENT_PROXY_RELAY_MODE=agent_proxy_standalone
export CCR_AGENT_PROXY_STANDALONE_URL=https://proxy.internal:3128
```

Details:

- Requires a self-hosted runner session with a usable session ID and token.
- Creates a local forwarding listener and configures HTTP and HTTPS proxy variables.
- Authenticates upstream with the session’s credentials; the proxy URL must not contain a username or password.
- Requires HTTPS, including for a proxy on the same machine, and verifies its certificate.
- Refuses startup when the required proxy configuration or credentials are unavailable.
- Cannot be combined with governed Git or the runner’s separate `--proxy-authorization-*` egress listener.

Evidence: Standalone proxy validation and forwarding—search for `"agent_proxy_standalone"` and `"CCR_AGENT_PROXY_STANDALONE_URL"`.


### Separate Five-Minute Cache TTL for Messages

What: A new environment variable selects a five-minute prompt-cache lifetime for message content.

Usage:

```bash
CLAUDE_CODE_MESSAGES_PROMPT_CACHE_TTL=5m claude
```

Details:

- Accepts `5m`.
- Applies a message-specific TTL override without replacing the existing general and subagent cache controls.
- Leaves the normal message TTL selection unchanged when unset.

Evidence: Message cache TTL selection and request construction—search for `"CLAUDE_CODE_MESSAGES_PROMPT_CACHE_TTL"`.

## Improvements


### Background MCP Task Results Survive Resume More Reliably

Completed MCP tasks now have persisted outcome records that can be recovered when a conversation resumes. Claude queues saved completion notifications that are missing from the transcript and retains their records until notification consumption and conversation persistence are confirmed.

Rewinding past the call that started a task also withdraws its saved outcome. Recovery is bounded, so older notifications may be deferred to a later resume.

Evidence: Outcome persistence, replay, and deletion checks—search for `".outcome.json"`, `"MCP task endings:"`, and `"saved ending(s) are kept and checked again at the next save or resume"`.


### MCP Tasks Handle Sign-In and Polling Failures More Clearly

Background MCP tasks distinguish a lost connection from a server that is still responding with errors. Their status can show that sign-in is needed, that polling is retrying, or that sign-in has been accepted again.

The recovery path uses bounded retry and timeout handling rather than treating every polling failure identically.

Evidence: MCP task polling and authentication recovery—search for `"status requests come back with errors; retrying"` and `"the sign-in is accepted again"`.


### Conversation Recovery from Invalid MCP Tool Schemas

An API rejection of an MCP tool’s input schema can now trigger a bounded retry with that schema replaced by a generic object schema. This lets the conversation continue, although Claude no longer sees the affected tool’s parameter descriptions.

The warning tells server authors to fix the schema and start a new conversation. This behavior is controlled by `tengu_calm_crescent`, which defaults to enabled.

Evidence: Schema-rejection recovery—search for `"the API refused this tool's input schema"` and `"retry:tool-schema-refused-"`.


### Fewer Repeated Web Fetches After a Known Failure

Web fetching now tracks failed targets and can avoid immediately fetching another URL associated with a recently failed target. Claude receives an explanation that the page was not fetched and instructions to continue with other sources.

The message also provides an explicit retry path when another attempt was requested. This extension is controlled by `tengu_patient_finch`, defaulting to enabled.

Evidence: Failed-target handling—search for `"tengu_patient_finch"` and `"a second fetch this soon nearly always fails the same way"`.


### Conditional PDF Reading Budgets After Context Exhaustion

PDF reads gain per-message and per-turn page budgets for sessions where the relevant read limits are configured and enforced after context exhaustion.

When a request exceeds the budget, the response distinguishes between spreading reads across later assistant messages and stopping until the user’s next message. It identifies the range that was not read.

These are conditional safeguards, not new universal PDF limits.

Evidence: PDF budget checks—search for `"CLAUDE_CODE_FILE_READ_MAX_PDF_PAGES_PER_MESSAGE"`, `"CLAUDE_CODE_FILE_READ_MAX_PDF_PAGES_PER_TURN"`, and `"The context has filled up once already"`.


### Hook-Rewritten Tool Inputs Are Checked More Thoroughly

Inputs rewritten by `PreToolUse` or `PermissionRequest` hooks receive additional validation before execution. The enforcement path checks the tool schema, rejects changes to harness-reserved fields, and runs the tool’s own input validation.

Errors distinguish an invalid hook rewrite from an originally valid model request. The additional enforcement is controlled by `tengu_glimmering_newt` and is also enforced in the applicable diskless-session path.

Evidence: Hook input validation—search for `"returned updatedInput that the tool refused"`, `"The tool input from the model was valid"`, and `"tengu_glimmering_newt"`.


### Clearer Handling of Unavailable Organization Policy

User-installed mods and hooks are held while their organization policy is unreadable or pending. Notices explain which checks are not running and whether later hooks can begin once policy becomes available.

Modules evaluated under an older policy are also withheld until checked against the current policy. Applicable sessions refuse to start a turn when the required organization policy cannot be read.

Evidence: Policy-dependent plugin and turn admission—search for `"Mods you installed are off for now"`, `"was judged under a policy that has since changed"`, and `"Your organization's policy could not be read, so this session cannot run a turn."`.


### Command-Sourced Plugins Wait for Organization Settings

Plugin installation, updates, marketplace header helpers, and background command-source refreshes now explicitly handle organization settings that have not yet loaded. Commands can be held rather than run before the policy decision is known.

Messages distinguish waiting for settings from a managed prohibition. Some contexts also refuse to run marketplace or plugin commands independently.

Evidence: Command-source policy handling—search for `"organization_unanswered"`, `"waiting for your organization's settings"`, and `"A tool server doesn't run a plugin's command on its own."`.


### More Precise Managed-Settings Diagnostics

Managed-settings errors now distinguish a failed policy source from invalid entries that leave particular `PreToolUse` or `PermissionRequest` hooks unloaded. Messages explain that those hooks are not protecting calls and identify entries that need repair.

Evidence: Managed-settings validation messages—search for `"Managed settings contain invalid entries, including PreToolUse/PermissionRequest hooks that are NOT loaded"`.


### Safer Settings Updates

Settings updates gain explicit failures for damaged, unreadable, or oversized stored settings and for changes that would exceed the storage limit. Diskless sessions also refuse settings writes when no supported storage path is available.

Evidence: Settings write checks—search for `"Your saved settings are damaged, so this change was not saved"`, `"Your saved settings would be too large after this change"`, and `"This session does not write settings to disk"`.


### Self-Hosted Runner Permission-Mode Guidance

When a launch would otherwise inherit a settings default that cannot apply on a self-hosted runner, Claude now explains the mismatch and how to select the mode explicitly.

For example:

```bash
claude --permission-mode plan
```

An already-running session can use `/plan` where available.

Evidence: Runner launch-mode notices—search for `"your settings' default permission mode"` and `"Type /plan: your default mode doesn't apply on a self-hosted runner."`.


### File Delivery Through Host-Provided Paths

A new host-controlled attachment mode lets supported sessions use file delivery through paths. It extends the existing send-file tool to that mode and preserves its result in subagents.

This requires a compatible host; setting the variable alone does not establish a file-delivery integration.

Evidence: Attachment delivery mode—search for `"CLAUDE_CODE_ATTACHMENTS_BY_PATH"` and `"rendered_locally"`.

## Bug Fixes

- Plugin `WorktreeCreate` and `WorktreeRemove` matchers are registered before worktree creation, allowing existing plugin hooks to participate at the required stage. Search for `"matcher(s) ahead of the worktree"`.

- PR/MR worktree creation validates explicit forge refs and their fetched commits. It rejects misleading similarly named refs, conflicting GitHub/GitLab refs, and cases where concurrent fetching prevents verification. Search for `"tengu_melodic_octopus"` and `"FETCH_HEAD did not record that fetch"`.

- Moving a Remote Control session to the cloud now rejects untracked files as well as other unsynchronized work, with guidance to commit and push or use `git stash -u`. It also publishes Git state before handoff. Search for `"You have untracked files on"`.

- Writes to sensitive Claude configuration locations receive tighter permission handling, including jobs, daemon files, shell snapshots, and session-environment scripts. Search for `"tengu_merry_boot"` and `"A file there can start a background session without asking anyone."`.

- `PermissionRequest` hook responses cannot change the permission mode in Cowork cloud sessions or sessions with MCP tools declared as code-running. Search for `"PermissionRequest allow: dropped its setMode"`.

- Hidden workflow runs refuse resume when the process cannot establish their local provenance or read the journal needed to determine whether the script is hidden. Search for `"This workflow run hides its script, and this process has no record of starting it"`.

- Daemon stopping more carefully verifies the process being signaled, never signals PID 1, and reports when the daemon remains alive after termination attempts. Search for `"this command never signals pid 1"` and `"daemon_stop_still_running"`.

- Remote Control credential-renewal failures no longer uniformly imply that the user’s login is invalid. The connection can continue using its current credential until expiry, with more specific recovery guidance. Search for `"register got a 401 that did not prove the login dead"`.

- Inline commands loaded from skills or command files reject the invisible characters U+FEFF and U+180E when the selected shell tool does not accept them. Search for `"command contains the invisible character U+FEFF"`.

- Hosted Linux file tools can reject paths that look like locations on the user’s separate computer, preventing a local container write from being mistaken for a delivered edit. Search for `"starts like a path on the user's computer and was refused"` and `"tengu_hazy_cosmos"`.

- Artifact publishing refuses inline edits when the automatic permission check cannot see those edits, directing Claude to edit the file separately before publishing. Search for `"Automatic check cannot see the edits"`.

## In Development

These additions contain shipped infrastructure whose activation is disabled, conditional, or not exposed as an ordinary user setting.


### Cloud Sessions with Console Sign-In [In Development]

What: A separate browser authorization flow would let an eligible Console-profile user authorize cloud sessions for the same organization.

Status: Disabled entry point.

Details:

- Includes browser authorization, manual-code handling, organization and account validation, secure credential storage, refresh locking, and renewal.
- Validates that the authorization grants the required sessions scope.
- The function permitting a fresh cloud-session sign-in returns `false` in this build.
- The presence of browser sign-in messages does not establish that users can invoke this flow.

Evidence: Console cloud-session authorization—search for `"Opening your browser to sign in for cloud sessions with your Console organization"` and `"cloud-sessions sign-in"`; the fresh-sign-in permission check returns `!1` in the original module source.


### Apply an Idle Summary When the User Returns [In Development]

What: Existing idle compaction gains a mode that prepares a summary while the user is away and applies it when they return.

Status: Feature-flagged; defaults to off.

Details:

- Adds `compact_on_return` alongside the existing idle modes.
- Requires precomputed compaction and a session that supports replacing the conversation.
- Checks cache warmth, conversation size, prefix changes, and newer requests before proceeding.
- Idle compaction itself existed previously; the return-time mode is the addition.

Evidence: Idle summary preparation and application—search for `"compact_on_return"`, `"tengu_sunny_locket"`, and `"Compacted after an hour idle, using a summary written while you were away"`.


### Automatic First-Page Reads for Long PDFs [In Development]

What: Reading a long PDF without specifying pages can return its first pages instead of failing immediately.

Status: Feature-flagged by `tengu_misty_sunbeam`; defaults to false.

Details:

- Returns the initial page range with the document’s total page count.
- Explains which pages were delivered and how to request the next range.
- With the flag disabled, the existing request-for-an-explicit-range behavior remains.

Evidence: Long-PDF partial-read path—search for `"tengu_misty_sunbeam"` and `"These are pages 1-"`.


### Up-Front Consent for Unattended Remote Commands [In Development]

What: Eligible users can be asked early whether auto-mode cloud sessions may run commands on their computer without asking for every command.

Status: Feature-flagged by `tengu_violin_guarneri`; defaults to false.

Details:

- Extends existing unattended-serving consent rather than introducing unattended serving itself.
- Offers a bounded up-front question.
- An unanswered or unsaved choice leaves commands asking for approval.
- The message points users to `/config` or `claude daemon` to answer later.

Evidence: Early unattended-serving consent—search for `"tengu_violin_guarneri"` and `"No answer yet, so commands from cloud sessions keep asking before they run."`.


### Hold Tool Calls Until a Person Types [In Development]

What: New permission-state infrastructure can pause tool calls until the user sends a message themselves.

Status: Infrastructure present; no ordinary user activation path identified.

Details:

- Adds a tool-admission check and explanatory refusal message.
- App- or automation-composed messages do not satisfy the stated release condition.
- Background memory extraction also recognizes the held state.
- The inspected code does not establish a normal UI or setting that activates it.

Evidence: Held-tool permission checks—search for `"tools_held_until_a_person_types"` and `"Tool calls are paused in this session until the user sends a new message themselves"`.

## Notes

Remote Control now rejects its previous `--sandbox` option and a true daemon Remote Control `sandbox` key. Remove those options and configure session sandboxing through settings instead:

```json
{
  "sandbox": {
    "enabled": true
  }
}
```

Evidence: Remote Control configuration rejection—search for `"The sandbox key is not supported for Remote Control. Remove it."` and `"To sandbox sessions, set sandbox.enabled to true in settings."`.

This changelog compares 2.1.299 with 2.1.300 and checks substantive claims against the original split-module sources. Rebundling changes and separate VSCode, SDK-package, and native-installer features are excluded.


Generated with:
- tool: `harness-investigations@21a0a7a-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.300.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.300.txt`
- source modules: `archive/claude-code/original/cli-v2.1.300.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
