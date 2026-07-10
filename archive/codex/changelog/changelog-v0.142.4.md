# Changelog for version 0.142.4

## Official Release Highlights

The upstream release categorizes this version as a chore release with no user-facing changes. The diff confirms there are no new CLI subcommands, config keys, JSON-RPC methods, or breaking protocol changes. The two substantive changes are refinements to the LLM instructions Codex sends to itself and its sub-agents, which can affect observable agent behavior without altering the public API surface.

## Additional Changes Beyond Official Notes

### Multi-agent delegation guidance tightened

What: The system prompt injected into the `spawn_agent` tool description now includes clearer, more conservative rules for when an orchestrating agent should delegate work versus keep it local.

Details:
- A new explicit prohibition is added: "Requests for depth, thoroughness, research, investigation, or detailed codebase analysis do not count as permission to spawn." This closes a loophole where an agent could interpret a user asking for thorough analysis as implicit permission to fan out sub-agents.
- A new `### When to delegate vs. do the subtask yourself` section introduces a four-rule heuristic: analyze the full task and identify the critical path before delegating; delegate only bounded sidecar tasks that can run in parallel without blocking the next local step; do not delegate the immediately blocking task; keep work local when a subtask is tightly coupled, urgent, or likely to block forward progress.

In practice this should reduce unnecessary sub-agent spawning during analysis or research tasks, keeping the orchestrating agent on the critical path.

Code references:
- Added guidance in `spawn_agent_tool_description()` in `codex-rs/core/src/tools/handlers/multi_agents_spec.rs`


### AutoReview approval prompt simplified

What: When `approvals_reviewer` is set to `auto_review`, Codex now uses the same escalation prompt template as the standard `OnRequest` path rather than a separate, more detailed template.

Details:
- The `on_request_auto_review.md` template (45 lines of escalation guidance) and the corresponding `APPROVAL_POLICY_ON_REQUEST_AUTO_REVIEW` constant have been removed.
- The branch in `approval_text()` that selected this template for `ApprovalsReviewer::AutoReview` has been removed. `AutoReview` now falls through to `APPROVAL_POLICY_ON_REQUEST_RULE`, the same template used for user-approval mode.
- The short `AUTO_REVIEW_APPROVAL_SUFFIX` (mentioning `approvals_reviewer` is `auto_review` and the `materially safer alternative` fallback rule) is still appended, so the agent still knows it is in auto-review mode.
- The removed template contained extensive per-scenario escalation guidance (when to preemptively request escalation for sandbox-blocking commands, network access, lock files, destructive operations, etc.). That guidance is no longer sent to the agent when `auto_review` is active without `exec_permission_approvals_enabled`.

Users relying on `approvals_reviewer: auto_review` may notice the agent is less proactive about pre-requesting escalated sandbox permissions, since the detailed guidance for that scenario has been consolidated away.

Code references:
- `APPROVAL_POLICY_ON_REQUEST_AUTO_REVIEW` removed from `codex-rs/prompts/src/permissions_instructions.rs`
- `approval_text()` branch for `ApprovalsReviewer::AutoReview` removed from the same file
- Deleted file: `codex-rs/prompts/templates/permissions/approval_policy/on_request_auto_review.md`


Generated with:
- tool: `harness-investigations@03136fb`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/codex/diff/v0.142.4.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.142.4.md`
