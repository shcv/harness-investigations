# Changelog for version 2.1.315

## Summary

This release adds independent effort defaults for subagents, selected read-only exceptions to working-directory boundaries, and shared group budgets for enterprise gateways. Custom certificate handling and layered gateway policy validation are stricter, so affected installations may need configuration changes. More informative Bash output previews and memory-pressure diagnostics are also present behind gates that are off by default.

## New Features


### Set a Default Effort for Subagents

Use `CLAUDE_CODE_SUBAGENT_EFFORT` to give ordinary subagents a different reasoning effort from your main conversation—for example, keeping routine delegated work inexpensive while using higher effort yourself.

```bash
CLAUDE_CODE_SUBAGENT_EFFORT=low claude --effort high
```

- Accepts `low`, `medium`, `high`, `xhigh`, and `max`, subject to model support.
- Explicit agent or workflow effort settings take precedence.
- Forked agents retain their separate inheritance behavior; this does not override every agent’s effort.


### Read Selected Paths Outside the Working Directories

The new `permissions.blockReadsExemptPaths` setting lets a launcher expose specific files or directories while retaining `blockReadsOutsideWorkingDirectories`. This is useful for shared reference material that should be readable without making its directory a working directory.

```bash
claude --settings '{
  "permissions": {
    "blockReadsOutsideWorkingDirectories": true,
    "blockReadsExemptPaths": ["/opt/project-reference"]
  }
}'
```

Exemptions remove the outside-directory read block; normal permission checks still apply. They do not grant write access or change the sandbox’s filesystem access.

This setting is accepted through `--settings` and settings supplied by the launching application, rather than user, project, local, or managed settings. Paths must be absolute local paths; roots, patterns, `~`, and `..` are not supported. Cloud and restricted sessions may not apply these exemptions.


### Shared Monthly Budgets for Enterprise Gateway Groups

Administrators running `claude gateway` can now configure a shared monthly spending pool for an RBAC group alongside each member’s individual limit. Spend-limit responses also include the pool’s spending so far.

For example, a request to the gateway’s `/v1/organizations/spend_limits` API can contain:

```json
{
  "scope": {
    "type": "rbac_group",
    "rbac_group_id": "GROUP_ID"
  },
  "period": "monthly",
  "amount": "10000",
  "pooled_budget": {
    "amount": "100000",
    "paused": false
  }
}
```

Amounts are in cents: this example sets a $100 individual limit and a $1,000 shared pool. Pooled budgets are supported only for monthly group limits and can be paused independently.

Pool enforcement depends on successful database checks; a failed pool lookup leaves individual limits enforced but temporarily skips the shared cap.


### Choose Which Input Bedrock Guardrails Inspect

Enterprise gateway Bedrock upstreams now support `guardrail.input_tagging`, letting administrators select which parts of a conversation receive guardrail input tags.

```yaml
guardrail:
  id: YOUR_GUARDRAIL_ID
  version: "1"
  input_tagging: user_messages
```

Supported values are `last_message`, `user_messages`, `all_messages`, and `all_messages_and_system`. All Bedrock upstreams must use the same setting so failover preserves the tagging behavior.

## In Development


### Bash Output Previews That Include the Ending

Large Bash results can now include both the beginning and the end of their output, making final test summaries and build errors visible without another file read. The complete saved output remains available separately.

Successful-command previews are gated by `tengu_quiet_pike`; failed-command previews use `tengu_hushed_wren`. Both default to off.


### Memory-Pressure and Command Diagnostics

Bash results can carry a notice when the kernel killed a process under the session’s shared memory limit, even when a test runner replaced the worker and the command appeared to succeed. The notice explains that another concurrent command may have caused the event and suggests reducing parallelism.

This is gated by `tengu_wiggly_gray`, off by default. Separate command-specific advice can be supplied through `tengu_temporal_kazoo`, which defaults to no rules and can select hints by command type, duration, failure, and output filtering.


### Permission Checks for MCP Resource Reads

MCP resource reads and directory listings have a new path through permission checks instead of being automatically allowed. The implementation also prevents these resource tools from offering a blanket “always allow” shortcut.

The behavior is gated by `tengu_greedy_shore`, off by default.

## Other Changes

- Changed layered gateway policy validation to reject policy helpers, conflicting hook restrictions, and negated paths in `deny` or `ask` rules.
- Changed CA loading to filter problematic certificate loops and certificates whose subject and issuer match but whose self-signature cannot be verified.
- Changed automatic Bash edit-diff activation to include model configuration in `auto` and `bypassPermissions` modes; explicit `bashEditDiffEnabled` settings remain available.
- Added `CLAUDE_CODE_DISABLE_ULTRATHINK=1` to disable the `ultrathink` keyword’s effort boost.
- Improved plugin-message presentation across transcripts, session previews, search, and exports by showing the message without its instruction wrapper.
- Improved auto-mode notices to explain when gateway safety checks fall back to the built-in check and incur additional Claude requests.
- Improved remote-session warnings to explain when `--chrome` has no effect because MCP tools run in the remote workspace.
- Improved archived cloud-session errors to explain that the session can receive messages again after being unarchived at claude.ai.
- Improved sign-in errors to distinguish unloaded organization settings, invalid administrator helper configuration, and a required restart.
- Fixed copied sessions resuming their source session’s unfinished turn or executing a tool call deferred in the source session.
- Fixed sandbox cleanup to quarantine uncertain Git-related entries rather than deleting potentially pre-existing files.
- Fixed hosted MCP requests using stale CA settings to refuse connections when the old and current trust sets have no certificates in common, with instructions to reconnect.

## Notes

Gateway administrators using `policy_mode: layered` should remove `policyHelper` and `policyHelpers`, move `disableAllHooks`, `allowedHttpHookUrls`, and `httpHookAllowedEnvVars` restrictions into a catch-all `match: {}` policy, and replace negated `deny` or `ask` paths with narrower rules. Alternatively, remove layered mode.

If custom-CA connections stop working, run with `--debug` to identify the rejected certificate and have the CA bundle corrected. Compatibility switches are available as `CLAUDE_CODE_DISABLE_SELF_NAMED_CERT_DROP=1` and `CLAUDE_CODE_DISABLE_LOOPED_CROSS_CERT_DROP=1`; the former retains all certificates affected by the self-signature check.

The gateway’s shared-budget support requires a database migration. If startup reports that migration 7 could not acquire its table lock, release the blocking database transaction and restart the gateway.


Generated by `harness-investigations@800291d-dirty` using codex `gpt-6.1-sol` (medium effort)
Inputs: astdiff, strings, module sources
