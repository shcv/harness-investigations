# Changelog for version 2.1.153

## Summary
Version 2.1.153 expands the Workflows rollout into “dynamic workflows,” including a new `workflow` keyword trigger, a `/config` toggle, richer review dialogs, and better per-agent workflow progress details. It also adds a feature-of-the-week credit grant flow, improves model switching defaults, and makes update/auth/plugin diagnostics more explicit.

### Dynamic Workflow Trigger and Controls [Gradual Rollout]
What: Workflows are now presented as “dynamic workflows,” and users can trigger them by including `workflow` or `workflows` in a prompt when the feature is enabled.

Usage:
```bash
claude
# then type a prompt containing "workflow" or "workflows"
```

Details:
- The old hidden trigger language was changed from `ultrawork` to the more direct `workflow` / `workflows`.
- When the keyword is detected, Claude shows “Dynamic workflow requested for this turn.”
- `alt+w` can ignore or restore the workflow keyword request for the current prompt.
- `/workflows` now lists “dynamic workflow” history.
- `/config` includes a “Dynamic workflows” toggle backed by the new `enableWorkflows` setting.
- Availability is still gated: the code checks `allow_workflows`, `tengu_workflows_enabled`, `CLAUDE_CODE_WORKFLOWS`, and managed settings such as `disableWorkflows`.

Evidence: Dynamic workflow keyword attachment and toggle (search for `"workflow_keyword_request"`, `"The user included the keyword \"workflow\" or \"workflows\""`, `"chat:workflowKeywordToggle"`, and `"Dynamic workflows"`)


### Dynamic Workflow Review Dialog
What: Workflow permission prompts now show a summarized workflow plan before execution, with an option to inspect or edit the script.

Usage:
```bash
/workflows
# or invoke a saved workflow by slash command when available
```

Details:
- The review prompt is now titled “Run a dynamic workflow?”
- If the workflow has phase metadata, the dialog summarizes the subagent phases instead of only showing raw code.
- Users can toggle between “View workflow summary” and “View raw script.”
- `ctrl+g` opens the script in `$EDITOR`.
- Saved workflows are described as “Dynamic workflow saved to … Invoke as /name or Workflow({name: ...}).”

Evidence: Workflow review UI (search for `"Run a dynamic workflow?"`, `"This dynamic workflow will spin up multiple subagents"`, `"View workflow summary"`, and `"ctrl+g to edit script in $EDITOR"`)


### Feature-of-the-Week Usage Credit Grants [Gradual Rollout]
What: Claude Code can grant temporary usage credits when a server-side “feature of the week” campaign is active.

Usage:
```bash
/loop
/code-review
/security-review
```

Details:
- The campaign payload is read from the `tengu_lilac_loom` flag.
- Supported campaign targets map to `loop`, `review`, and `security-review`; `remote` is present in the schema but maps to `null`.
- The client calls the overage credit grant endpoint and shows pending, success, or failure messages.
- Granted credits are shown as expiring in 90 days and used before purchased credits.

Evidence: Feature-of-the-week credit flow (search for `"tengu_lilac_loom"`, `"feature_of_the_week"`, `"/api/oauth/organizations/:orgUUID/overage_credit_grant"`, and `"Thanks for trying the feature of the week."`)


### Background Resume Reply Flag
What: A hidden resume flag can immediately continue a transcript that ends on a user message, mainly for background-session handoff.

Usage:
```bash
claude --resume <session-id> --reply-on-resume
```

Details:
- The flag creates an initial replay message when resuming.
- The help text says it is set by `/background` mid-turn so the fork continues the in-flight turn.
- This looks primarily infrastructure-facing, but it is a real CLI flag in the main command parser.

Evidence: Resume flag parser (search for `"--reply-on-resume"` and `"When resuming, immediately query if the loaded transcript ends in a user-role message"`)


### Model Picker Now Defaults Selections for Future Sessions
The `/model` picker changed from “applies to this session only” to making the selected model the default for new sessions, with a separate “use this session only” action.

Evidence: Model picker copy and action rename (search for `"Switch between Claude models. Your pick becomes the default for new sessions"` and `"modelPicker:thisSessionOnly"`)


### Workflow Agent Progress Details
Dynamic workflow history now shows richer per-agent status, including queued/running/completed/failed/stopped states, model, agent type, remote session ID, attempt reason, token count, tool-call count, idle time, prompt preview, recent activity, and outcome text.

Evidence: Workflow agent detail panel (search for `"Available once the agent starts."`, `"No tool calls yet."`, `"The workflow stopped before this agent finished."`, and `"from resume journal"`)


### Auto-Update Diagnostics and Recovery
Claude Code now records the last update result and surfaces update/install problems more clearly.

Details:
- Update attempts are persisted in `.last-update-result.json`.
- `/doctor` can show “Last update attempt.”
- A startup notice warns “Claude Code can't auto-update · run `/doctor`” after a global npm update fails because of permissions.
- The installer now explains server-side version caps and forced downgrades.
- Failed update recovery now tells users where the preserved executable is and how to rename it back.

Evidence: Update result persistence and notices (search for `".last-update-result.json"`, `"Last update attempt:"`, `"Claude Code can't auto-update"`, `"The update target is capped at"`, and `"Your Claude Code executable could not be restored"`)


### Clearer Lost Command Output Errors
When command output is lost because the temp filesystem is full or out of inodes, Claude Code now reports the filesystem path, the low-space/inode condition, and the `CLAUDE_CODE_TMPDIR` workaround.

Evidence: ENOSPC diagnostic (search for `"Command output was lost: the temp filesystem"` and `"Free up space or set CLAUDE_CODE_TMPDIR"`)


### Plugin Relevance Signals Use Read Files and CWD Globs
Marketplace plugin suggestion metadata now supports `filesRead` and `cwd` signals instead of a single regex-style `filePath` signal.

Details:
- `filesRead` matches files Claude has read this session.
- `cwd` matches the session working directory.
- Both require forward-slash glob patterns.
- Built-in frontend-design and Vercel plugin suggestions were migrated to `filesRead` globs.
- Marketplace clone/update can skip Git LFS smudge with `GIT_LFS_SKIP_SMUDGE=1`.

Evidence: Marketplace signal schema (search for `"filesRead"`, `"must declare at least one signal (cli, hosts, filesRead, manifestDeps, or cwd)"`, `"must use forward slashes"`, and `"GIT_LFS_SKIP_SMUDGE=1"`)


### More Explicit MCP Policy Diagnostics for Agents
Agent MCP setup now distinguishes plugin-only customization, `--strict-mcp-config`, and managed settings policy blocks in its debug messages.

Evidence: Agent MCP diagnostics (search for `"strictPluginOnlyCustomization"`, `"--strict-mcp-config"`, and `"managed settings MCP policy"`)


### Login Warning for Overriding OAuth Tokens
During login, Claude Code now warns if `CLAUDE_CODE_OAUTH_TOKEN` is set, because that environment variable will override the newly saved login token at runtime.

Evidence: Login warning (search for `"Warning: CLAUDE_CODE_OAUTH_TOKEN is set in your environment"`)


### Auth Error Mentions WIF Credentials
Headless/auth-required paths now mention WIF environment variables alongside API keys and OAuth tokens.

Evidence: Auth requirement text (search for `"ANTHROPIC_API_KEY, CLAUDE_CODE_OAUTH_TOKEN, or WIF env vars"`)


## Bug Fixes

- Permission allow-rules that should be unsafe in auto mode are filtered when auto mode is active, reducing accidental auto-approval of dangerous rules. Evidence: auto-mode permission filtering (search for `"auto"` and `"getAllowRules"` near `"kRH"`)

- TTY stream error handling now covers stdin as well as stdout/stderr and treats `ENXIO` and `EBADF` like broken-pipe style stream failures. Evidence: stream error handling (search for `"ENXIO"` and `"EBADF"`)

- Background job directories are explicitly allowed for current background sessions, which should reduce false permission denials when reading or writing files under the active job directory. Evidence: job directory access (search for `"Job directory files for current bg session are allowed for reading"` and `"Job directory files for current bg session are allowed for writing"`)


### Dynamic Workflows [Gradual Rollout]
What: Dynamic workflows are now substantially built out, but still controlled by server and managed-setting gates.

Status: Feature-flagged

Details:
- Without `CLAUDE_CODE_WORKFLOWS`, availability depends on `tengu_workflows_enabled`.
- If available, default enablement depends on plan; Pro defaults off while other plans default on.
- Managed settings can still disable the feature with `disableWorkflows`.
- The `enableWorkflows` setting is documented as “Unset = default by plan once the feature is available.”

Evidence: Workflow availability gates (search for `"tengu_workflows_enabled"`, `"enableWorkflows"`, `"disableWorkflows"`, and `"CLAUDE_CODE_DISABLE_WORKFLOWS"`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.153.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.153.txt`
