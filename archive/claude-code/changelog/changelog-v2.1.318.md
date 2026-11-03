# Changelog for version 2.1.318

## Summary

This release adds an opt-in mode for safer shared-memory deletion and substantial groundwork for experimental Code Mode, moving local conversations to the cloud, and reviewing batches of merged pull requests. MCP permission checks now reject ambiguous tool names, and self-hosted runners can inherit idle-release limits from Anthropic unless explicitly overridden.

## New Features


### Explicit Shared-Memory Deletions

A new `recorded` value for `CLAUDE_CODE_MEMORY_PUSH_DELETE_MODE` makes shared-memory deletion depend on an explicit removal Claude observes, rather than a file simply disappearing locally. This helps prevent cleanup scripts, renamed files, or a missing local memory folder from unintentionally deleting shared information.

```bash
CLAUDE_CODE_MEMORY_PUSH_DELETE_MODE=recorded claude
```

- Applies to writable shared user and team memory.
- Claude must use a standalone `rm` command naming each file by its full path.
- Missing files without a recorded deletion are restored from shared memory.
- The existing default remains `corroborate`.

## In Development


### Experimental Code Mode

Code Mode lets Claude investigate and act through a persistent JavaScript environment. It can combine file reads, searches, shell commands, and MCP calls into scripts, run independent operations concurrently, and retain variables between calls. Longer scripts can report their results asynchronously.

The implementation includes startup consent, permission prompts, hook handling, cancellation, and session-resume checks. It requires both `CLAUDE_CODE_EXPERIMENTAL_CODE_MODE=1` and the `tengu_rustling_blossom` gate, which defaults to off; the environment variable alone does not unlock it.

Current restrictions include:

- Requires the native build, an interactive local terminal, and a supported first-party claude.ai sign-in.
- Evaluated models are Opus 5.5 and Sonnet 5.5.
- Does not support agent teams, Remote Control, or installed JavaScript plugin hooks that inspect tool calls.
- Sessions created in this mode require Code Mode to remain available when resumed; cloud sessions and Claude apps cannot continue them.


### Move a Local Conversation to the Cloud

A new conversation-copy path is being added to `/teleport`. It checks a saved local conversation, restarts Claude Code, and starts a cloud session with the transferable history. The CLI also recognizes a local session ID supplied to `--cloud`.

```bash
claude --cloud <local-session-id>
```

This path uses `tengu_woolly_blanket`, off by default. It requires a matching claude.ai account and organization and an Anthropic-hosted cloud environment.

The implementation checks for unsaved messages, another window using the conversation, active background work, and launch settings or permissions that would be lost. Account memory and some local context are withheld from the transferred history; conversations containing third-party-provider replies are refused.


### Assign Usage to a claude.ai Project

The new `/project` command will let eligible sessions choose the claude.ai Project named in organizational usage reports.

- `/project` shows the current assignment.
- `/project <Project ID or URL>` changes it until Claude Code restarts.
- `/project <Project ID or URL> --save` saves it for the current folder.
- `/project clear --save` removes the saved local assignment.

This is a usage-reporting assignment. The command is behind `tengu_gentle_cupcake`, off by default, and requires a local session using claude.ai authentication directly with Anthropic. `CLAUDE_CODE_ATTRIBUTION_PROJECT` and managed attribution settings take precedence.


### Add claude.ai Connectors from the Terminal

A hidden `--web` option for `claude mcp add` starts connector setup on claude.ai instead of writing a local MCP server configuration.

```bash
claude mcp add my-connector https://example.com/mcp --web
```

The flow opens claude.ai, guides you through connecting the server, and checks whether the connector is ready. It also detects when an existing local MCP server at the same address would take precedence.

The `tengu_twinkling_aurora` gate defaults to off. This path accepts a name and HTTPS address; local server options such as headers, environment variables, transport, and OAuth client settings cannot accompany `--web`.


### Batch Evaluation of Merged Pull Requests

A hidden `claude ultrareview eval` mode can review multiple merged pull requests and write a combined JSON report.

```bash
claude ultrareview eval owner/repo#123 owner/repo#456 \
  --output reviews.json --max-cost 100
```

It supports a file of targets through `--list`, removes duplicates, checks merge commits, and runs reviews concurrently. It requires Git, authenticated GitHub CLI access, and a person accepting the cost in an interactive terminal outside Claude Code.

Availability requires existing ultrareview access plus `eval_enabled: true` in `tengu_review_bughunter_config`; evaluation is disabled when that field is absent. `--max-cost` limits how many reviews start using an estimated per-review cost—it is not a hard spending ceiling. Each review uploads its repository files to the cloud.


### Diffs Outside Git Repositories

There is a new implementation for producing workspace diffs when the launch folder is not a Git repository. It builds a temporary comparison repository, respects ignore rules, and excludes sensitive configuration paths.

Its enablement function currently always returns false, so it is not usable in this build. The implementation requires Git 2.32 or newer.

## Other Changes

- Changed MCP approvals so tools with colliding Claude Code names cannot use existing allow rules or `--permission-prompt-tool` approval.
- Changed `deniedMcpServers` URL matching to also inspect a server address carried in an `mcp_url` parameter.
- Changed self-hosted runners with no explicit idle limit to honor eligible limits supplied by Anthropic, releasing sessions only after checks find no work that would be lost.
- Added managed-only `disableReplyCheck` for self-hosted Claude Tag sessions, disabling reply-tool enforcement and associated service-supplied reminders.
- Added `CLAUDE_CODE_DISABLE_AGENT_PROGRESS_SUMMARIES` to suppress generated subagent progress summaries.
- Improved shared-memory mass-deletion protection to count recent explicit deletions across a rolling one-minute window.
- Improved login-expiry warnings to distinguish nonrenewable sign-in deadlines and explain when a fresh login is required.
- Improved Project attribution settings to accept `chan_` Project IDs.
- Improved Remote Control output handling to explain when large results must be read in the local Claude Code session.
- Improved streamed connections to reconnect promptly after computer sleep or a long process pause.
- Improved MCP task handling to stop following tasks when their connector identity changes or status polling fails, reporting the outcome as unknown.
- Fixed delayed shell approvals being reused after a restart when the original working directory cannot be confirmed.
- Fixed startup configuration reads treating a transiently missing configuration file as permanently absent without a second check.
- Fixed some atomic file saves failing with `EBUSY` on NFS by retrying the save.
- Fixed connections to previously recognized legacy stdio MCP servers failing immediately when the server exits during initialization.

## Notes

Self-hosted runner operators who need to retain idle sessions should explicitly set `--release-idle-session-min 0`. A positive value selects the operator’s own timeout; leaving the option unset now permits service-supplied limits.

If MCP allow rules stop working because of a tool-name collision, the server must give its tools distinct names and affected rules must be updated. If a proxied MCP server is newly blocked, check whether `deniedMcpServers` matches its underlying `mcp_url`.

When a sign-in reaches its nonrenewable deadline, run `claude auth login`. For unattended jobs, use `claude setup-token` and configure `CLAUDE_CODE_OAUTH_TOKEN` as directed.


Generated by `harness-investigations@76c43e4-dirty` using codex `gpt-6.1-sol` (medium effort)
Inputs: astdiff, strings, module sources
