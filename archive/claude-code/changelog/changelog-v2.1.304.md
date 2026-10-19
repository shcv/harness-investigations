# Changelog for version 2.1.304

## Summary

Claude Code adds readable context-window sizes, optional low-resource warnings, and finer control over plugin MCP servers. Eligible accounts also gain more specific limit resets and usage-credit offers through server-controlled rollouts. Safety checks now require confirmation for more mounted-drive deletions and better protect nested worktrees during cleanup.

## New Features


### Readable Auto-Compact Window Sizes

`CLAUDE_CODE_AUTO_COMPACT_WINDOW` now accepts suffixes such as `200k` and `1M`, making context limits easier to configure. Invalid or out-of-range values produce explanations at startup and in the auto-compact settings display.

```bash
CLAUDE_CODE_AUTO_COMPACT_WINDOW=200k claude
```

The supported range is 100,000–1,000,000 tokens, capped further by the model’s context window. Values below or above that range are clamped; unusable values are ignored.


### Plan Approval Without a Plan File

Sessions without a local filesystem can now present the complete plan on an approval card. Approving ends plan mode and lets Claude proceed; declining keeps it in plan mode for revision. Previously, these sessions instructed Claude to return the plan as ordinary reply text.

Only the main conversation can request approval, and the submitted plan must fit within a 32 KiB JSON payload.


### Selective Plugin MCP Loading

New environment variables let you keep plugin skills and commands while limiting the servers those plugins start.

```bash
CLAUDE_CODE_SKIP_PLUGIN_LOCAL_MCP_SERVERS=1 claude
```

- `CLAUDE_CODE_SKIP_PLUGIN_LOCAL_MCP_SERVERS=1` permits only plugin servers using `sse`, `http`, or `ws`, and skips MCP bundles.
- `CLAUDE_CODE_SKIP_PLUGIN_MCP_BUNDLES=1` skips `.mcpb` and `.dxt` sources without excluding other server declarations.
- `CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS_EXCEPT` accepts comma-separated plugin exceptions; use full `plugin@marketplace` IDs for exceptions to the new restrictions.


### Optional Low-Disk and Low-Memory Warnings

Claude can now receive low-resource notices during a session, helping it recognize when disk or memory pressure may explain failing commands.

```bash
CLAUDE_CODE_WARN_DISK_FREE_GIB=5 \
CLAUDE_CODE_WARN_MEMORY_FREE_GIB=2 \
claude
```

Thresholds are nonnegative whole numbers in GiB; `0`, the default, disables each warning. Checks run approximately once a minute. Disk checks cover the filesystem holding the working directory, and memory checks account for container limits.


### Choose Which Limit to Reset [Gradual Rollout]

The existing `/limit-reset` flow now distinguishes full, 5-hour, weekly, and Fable resets. When several types are available, it offers a chooser or accepts a specific type:

```text
/limit-reset
/limit-reset 5-hour
/limit-reset weekly
/limit-reset full
/limit-reset fable
```

Confirmations explain what each reset restores, how many remain, and when they expire. A Fable reset returns only Fable’s weekly usage; it may leave another limit in place. Your weekly reset day stays unchanged.

Availability requires an account grant and the `tengu_cedar_ember` gate, whose fallback is disabled.


### Usage-Credit Offers [Gradual Rollout]

Eligible users can see limited-time discounts or bonus-credit offers in `/usage-credits` and limit-related prompts. Offers show their remaining duration and applicable pricing. If prices change while confirmation is open, Claude Code cancels the purchase and asks you to reopen `/usage-credits`.

The `tengu_starry_waterfall` gate defaults to disabled, and promotional offers must be permitted for the session.


### Organization Surveys [Gradual Rollout]

Enterprise users may receive an optional survey from their organization inside the terminal. Surveys support single-choice, multiple-choice, and text answers, identify the organization requesting feedback, and can be dismissed.

This requires the `tengu_steady_mitten` gate, which defaults to disabled. `CLAUDE_CODE_DISABLE_FEEDBACK_SURVEY=1` also disables these surveys.


### Managed-Settings Startup Checks [Gradual Rollout]

Selected organization-managed sessions now wait for required organization settings before starting. A blocking screen explains connection, proxy, sign-in, or invalid-settings failures and offers automatic retries, `Retry now`, and relevant sign-in recovery.

The rollout uses `tengu_org_config_required`; its fallback configuration is disabled with a rollout percentage of zero.

## In Development


### GitHub Pull Request Subscriptions

New `SubscribePR` tool guidance describes receiving CI failures, an all-green notification, review comments, and PR close/reopen events without repeatedly polling GitHub. Subscribing would show a permission dialog, and unsubscribing would stop delivery.

The tool’s description and supporting restrictions are present, but this build does not wire it into an available tool entry point. The described feed also excludes new pushes and merge-conflict transitions.


### Automatic Worktree Name Numbering

New code can choose numbered worktree names when a name has already been used or is occupied by a folder or branch. It preserves existing branches and refuses a collision that appears during creation.

The visible worktree entry point still leaves this selection mechanism unset, so automatic numbering is not yet active there.


### Project Attribution

`CLAUDE_CODE_ATTRIBUTION_PROJECT` and supporting code prepare for associating requests with a claude.ai Project. However, the project resolver is stubbed and returns no project, so setting the variable does not enable attribution in this build.

## Other Changes

- Changed recursive `rm` checks to require explicit approval for recognized mounted-drive paths and shallow targets beneath them, even when permission rules would otherwise allow the command.
- Changed Linux sandboxing to block nested user namespaces by default where supported, preventing commands from undoing filesystem write restrictions.
- Changed skill loading to withhold `allowed-tools` grants when the skill’s declared hooks cannot be registered, and explain the missing protection.
- Changed remote machine access to reject additional unsuitable locations, including hidden folders beneath the home directory.
- Improved MCP skill-resource validation to reject unlisted files, alternate URL spellings, and content that fails declared size or checksum checks.
- Improved worktree removal checks to detect nested `.claude/worktrees` directories and require an additional confirmation before deleting them.
- Improved worktree-exit warnings to account for branch changes and commits made after the session started.
- Improved custom `ANTHROPIC_BASE_URL` compatibility by retrying unsupported tool-search requests without tool search and remembering the refusal for a day.
- Changed tool-search selection to keep conversations that began without `ToolSearch` in that state until compaction or clearing, unless `ENABLE_TOOL_SEARCH=true` overrides it.
- Improved mod lifecycle reporting to distinguish successful reloads, retained earlier versions, removals, and changes requiring a restart.
- Fixed mods being able to initiate new background work, schedules, or subscriptions after Stop.
- Improved trusted-device recovery for remote API calls by attempting enrollment and retrying when permitted.
- Improved archived cloud-session handling to explain why messages cannot be sent and provide a link to view the session.
- Fixed Git operations continuing after repository configuration or Git-directory identity changes during safety checks.

## Notes

Use `200k` or `200000` for a 200,000-token environment override. A bare `CLAUDE_CODE_AUTO_COMPACT_WINDOW=200` means 200 tokens and is clamped to the 100,000-token minimum; the environment variable does not use the numeric-thousands shorthand accepted by the settings command.

Mounted-drive deletion prompts can be disabled with `CLAUDE_CODE_DISABLE_MOUNTED_DRIVE_RM_PROMPT=1`. For worktree cleanup warnings, move any nested worktrees you need to keep with `git worktree move` before confirming deletion.


Generated by `harness-investigations@25234fc-dirty` using codex `gpt-6.1-sol` (medium effort)
Inputs: astdiff, strings, module sources
