# Changelog for version 2.1.160

## Summary
Claude Code 2.1.160 adds a gated DesignSync workflow for pushing React design systems to claude.ai/design, adds enterprise-gated cloud review entry points around `/code-review ultra` and `/ultrareview`, and improves model fallback behavior. It also tightens shell/path safety checks and clarifies several user-facing errors around remote sessions, attachments, background sessions, and auto mode.

### DesignSync for claude.ai/design [Gradual Rollout]
What: Claude Code now includes a gated `/design-sync` skill and `DesignSync` tool for syncing a local React design system into a claude.ai/design design-system project.

Usage:
```bash
/design-sync
```

Details:
- The workflow bundles a React design system from Storybook or a built package into `_ds_bundle.js`, `styles.css`, per-component `.d.ts`, `.prompt.md`, and preview-card HTML files.
- The `DesignSync` tool can list/create design-system projects, read project files, finalize an upload plan, write/delete files, and register/unregister Design System pane asset cards.
- Writes are guarded by an explicit `finalize_plan` permission boundary. Uploads can use `localPath`, so file contents do not need to enter model context.
- Requires claude.ai authentication, `user:design:read` and `user:design:write` scopes, and nonessential network traffic enabled.
- Status: feature-flagged. The tool is enabled only when `allow_design_sync` and `tengu_slate_quill` are active, so not all users will see it yet.

Evidence: DesignSync gated tool and skill (search for `"DesignSync"`, `"/design-sync"`, `"sync local design system components to a claude.ai/design project"`, and `"tengu_slate_quill"`)


### Cloud Code Review Entrypoints [Gradual Rollout]
What: Claude Code adds cloud review launch paths around `/code-review ultra` and `/ultrareview` for multi-agent review in Claude Code on the web.

Usage:
```bash
/code-review ultra
/code-review ultra <PR number>
claude ultrareview
```

Details:
- `/code-review ultra` is described as launching a multi-agent cloud review of the current branch, or a specific GitHub PR when given a PR number.
- `/ultrareview` appears as a deprecated alias for `/code-review ultra`.
- New UI strings include preflight, launch confirmation, active status, stop confirmation, and cloud-review fallback messaging.
- Status: gated. Several strings describe Claude for Enterprise availability, and the command path checks environment/provider capability before launching.

Evidence: Cloud review launch flow (search for `"Run ultrareview in the cloud?"`, `"/code-review ultra"`, `"/ultrareview runs a deep, multi-agent review of your changes"`, and `"c4e-ultrareview"`)

### Multiple Turn-Scoped Fallback Models
Claude Code’s `--fallback-model` option now accepts a comma-separated list of models and retries the primary model at the start of each user turn. The fallback event schema also now includes `permission_denied` in addition to retired/unknown model and overload cases.

Usage:
```bash
claude -p "Summarize this" --fallback-model model-a,model-b
```

Evidence: Updated CLI help and SDK event description (search for `"Enable automatic fallback to specified model(s)"`, `"permission_denied"`, and `"Turn-scoped"`)


### Configurable Safety-Filter Model Switching
A new `switchModelsOnFlag` setting controls whether Claude Code automatically switches models when a message is blocked by safety filters. The UI label is “Switch models when a message is flagged”; disabling it can cause the chat to stop instead of retrying with another model.

Evidence: New setting schema and config UI (search for `"switchModelsOnFlag"` and `"When safety filters block a message"`)


### Ultracode Keyword Trigger Renamed and Clarified
The workflow keyword setting now describes the `ultracode` keyword instead of the older `workflow`/`workflows` trigger. This makes the opt-in language match the visible `/effort ultracode` behavior and the dynamic workflow orchestration prompts.

Usage:
```bash
# In a prompt:
ultracode refactor this module and verify behavior
```

Evidence: Settings description changed from workflow keywords to ultracode (search for `"Ultracode keyword trigger"` and `"Enable the \"ultracode\" keyword trigger"`)


### Workflow-Backed Code Review Routing
High, xhigh, and max effort code reviews can now route to a workflow-backed review when workflows are enabled and the Workflow tool is available. The workflow runs finder angles, independent verification, a sweep pass, and then produces a ranked findings report.

Usage:
```bash
/code-review high
/code-review xhigh src/
```

Evidence: Workflow-backed review routing (search for `"Workflow-backed code review"`, `"Run the workflow-backed code review at"`, and `"tengu_review_workflow_routing"`)


### Clearer Auto Mode Provider Gating
When auto mode is unavailable because of the current provider, Claude Code now explains that `CLAUDE_CODE_ENABLE_AUTO_MODE=1` is required instead of only reporting a generic disabled state.

Evidence: Auto mode provider message (search for `"auto mode requires CLAUDE_CODE_ENABLE_AUTO_MODE=1"`)


### Background Sessions Use Fullscreen Renderer When Attached
A new config explanation clarifies that background sessions always use the fullscreen renderer so scrolling and mouse support work when attached. The `tui` setting now applies only to sessions started directly with `claude`.

Evidence: TUI setting text (search for `"Background sessions always use the fullscreen renderer"`)


### Remote Session Provider Errors Are More Explicit
Remote session creation now fails early with a clear first-party-provider message when the current provider cannot support remote sessions.

Evidence: Provider guard (search for `"Remote sessions are only available on the first-party Anthropic API provider."`)

## Bug Fixes

- Improved shell permission analysis for tricky Bash constructs, including brace-expanded write targets, `read`/`select` stdin writes to `REPLY`, unsafe `set -o` state changes, unescaped quote parser issues, and unbalanced `[[ ]]` regex parsing. Evidence: shell safety checks (search for `"Brace characters in write target require manual approval"`, `"select statement reads stdin into $REPLY"`, and `"[[ ]] regex has unbalanced parentheses"`)

- Network and UNC path redirections now get explicit manual-approval reasons, including Windows UNC paths that could trigger SMB connections. Evidence: network redirect classification (search for `"Redirect target is a Windows UNC path"`)

- Attachment accessibility errors now include the underlying access failure instead of always saying “permission denied.” Evidence: attachment error wording (search for `"is not accessible ("`)

- DesignSync upload safety blocks writes/deletes to reserved instruction paths such as `CLAUDE.md` and `.claude/`, even if they appear in the finalized plan. Evidence: reserved path guard (search for `"Cannot write reserved paths"` and `"CLAUDE.md and .claude/ carry instructions"`)

### DesignSync Upload and Converter Infrastructure [In Development]
What: A large bundled converter and validation loop for React design systems now ships inside the CLI.

Status: Feature-flagged/dark-launched

Details:
- The converter can build design-system bundles from Storybook or package output, generate component previews, run validation, and upload through `DesignSync`.
- It includes troubleshooting for render failures, missing fonts, missing docs, Storybook fallbacks, preview overrides, and server-side self-check behavior.
- This is mostly accessible through the gated `/design-sync` workflow, so many users will not see it until rollout flags are enabled.

Evidence: Bundled design-system converter and gated tool (search for `"Convert a React design system into the claude.ai/design DS-project layout."`, `"package-validate.mjs"`, and `"allow_design_sync"`)


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.160.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.160.txt`
