# Changelog for version 2.1.172

## Summary

This release introduces the Artifact tool, which lets Claude publish HTML and Markdown files to private pages on claude.ai that teammates can view and share. It also hardens URL provenance enforcement for web_fetch, refactors the auto-mode security classifier into a simpler single-stage design, improves Chrome browser automation ergonomics, and adds a `--plugin-dir-no-mcp` flag for plugin authors who manage their own MCP connections.


## New Features


### Artifact Tool — Publish HTML/Markdown to claude.ai [Gradual Rollout]

What: Claude can now render local `.html` or `.md` files to a default-private page on claude.ai that the user can later share with teammates.

Usage:
```
Claude, turn this analysis into a shareable artifact
Claude, publish report.html as an artifact with the 📊 favicon
```

Details:
- Claude writes the file via Write/Edit as usual, then calls the internal `Artifact` tool with the file path and a required emoji favicon
- Published pages are private by default; the user controls sharing
- The page URL is stable across redeploys when using the same file path — Claude passes the existing URL to update rather than mint a new one
- Pages are fully self-contained: CSP blocks all external CDN scripts, stylesheets, fonts, and remote fetches, so all CSS/JS must be inline
- Supports `.html`, `.htm`, and `.md` files; Markdown is rendered to HTML with an embedded stylesheet
- To update an artifact from a URL the user pastes in (from a previous session), pass it as the `url` parameter; otherwise a new URL is minted each session
- A `label` parameter lets Claude tag specific versions (e.g., "fixed-background") so they appear in the version picker by name
- New env var `CLAUDE_CODE_DISABLE_ARTIFACT` disables the tool globally
- Setting `disableArtifact: true` in project/user settings also disables it

Status: [Gradual Rollout] — controlled by `tengu_cobalt_plinth` feature flag (default off). Unavailable in headless/CI modes, the `local-agent` entrypoint, and Cowork sessions.

Evidence: Full tool implementation (search for `"Render an HTML or Markdown file to an Artifact"`) — gated by `j$("tengu_cobalt_plinth", !1)`


### `--plugin-dir-no-mcp` Flag for Plugin Authors

What: A new CLI flag that loads a plugin directory's skills, hooks, agents, and commands without reading or connecting to the plugin's `.mcp.json` or any `mcpServers` it declares. Intended for SDK hosts that own a plugin's MCP connections themselves and want to avoid double-connecting.

Usage:
```bash
claude --plugin-dir-no-mcp /path/to/plugin
```

Details:
- Behaves identically to `--plugin-dir` except the engine skips `.mcp.json` discovery for that plugin
- The `When-true` description in the schema: "the engine loads skills/hooks/agents/commands from this plugin but does NOT read its .mcp.json or manifest mcpServers"
- The flag can be specified multiple times for multiple plugin directories

Evidence: Flag definition (search for `"--plugin-dir-no-mcp"`) and schema description (search for `"does NOT read its .mcp.json"`)


### URL Provenance Check for web_fetch

What: `web_fetch` now enforces a provenance policy — it can only retrieve URLs that appeared in a user message or in a prior `web_fetch` result. Attempting to fetch a URL that entered the session through any other path (e.g., constructed by the model) triggers a user-facing permission prompt instead of silently fetching.

Details:
- If the URL has not been seen in a user message or prior result, Claude gets a denial and surfaces a prompt asking the user to allow or reject the fetch
- The permission prompt times out after a configurable window; on timeout the tool returns: "The permission request for this URL was not answered in time. Ask the user to approve the fetch or include the URL in a message, then try again."
- If the user denies: the error message from the denial rule is surfaced
- Error string for provenance failure: "URL not in provenance set. web_fetch can only retrieve URLs that appeared in a user message or a prior web_fetch result. Ask the user to include the URL in a message first."

Evidence: Provenance denial error (search for `"URL not in provenance set"`) and timeout message (search for `"permission request for this URL was not answered in time"`)


## Improvements


### Chrome Browser Automation — Batch Tool Loading in One ToolSearch Call

What: Claude's instructions for loading Chrome browser automation tools were rewritten to emphasize loading all needed tools in a single batched `ToolSearch` call rather than one tool at a time.

Details:
- Previous instruction told Claude to always call `tabs_context_mcp` first before anything else, as a required startup step
- New instruction starts with a core batch: `ToolSearch with query "select:mcp__claude-in-chrome__tabs_context_mcp,mcp__claude-in-chrome__navigate,mcp__claude-in-chrome__computer,mcp__claude-in-chrome__read_page,mcp__claude-in-chrome__tabs_create_mcp"` — and says to add task-specific tools (`read_console_messages`, `form_input`, `gif_creator`, `javascript_tool`) to the same call
- The explicit guidance: "Do NOT load tools one at a time; each separate ToolSearch call wastes a full round-trip"
- Only issue a second ToolSearch if a tool is needed that was not anticipated at startup

Evidence: Instruction update (search for `"batch every tool you expect to need into ONE ToolSearch call"`)


### Remote Control Status Labels Shortened to `/rc`

What: The status indicator labels for the Remote Control feature were renamed from "Remote Control active / connecting… / failed / reconnecting" to "/rc active / connecting… / failed / reconnecting". This makes them shorter and consistent with the `/rc` command name.

Evidence: Status label function (search for `"/rc active"`)


### MCP OAuth Token Clearing — Preserve Client Registration Option

What: When clearing stored OAuth tokens for an MCP server, Claude Code can now optionally preserve the OAuth client registration (the `clientId` and associated metadata) while clearing only the access/refresh tokens. This is useful when a token has expired or become invalid but re-registration is expensive.

Details:
- The clear function now distinguishes two modes: clearing only tokens (logs "Cleared stored tokens (preserved client registration)") vs. clearing everything (logs "Cleared stored tokens")
- The preserve-registration path zeroes out `accessToken`, `refreshToken`, `expiresAt`, and `scope` but keeps the `clientId`

Evidence: Updated clear function (search for `"Cleared stored tokens (preserved client registration)"`)


### Ultra (Cloud Review) Error Messages — More Specific and Actionable

What: When ultra (cloud review) is unavailable, Claude Code now explains precisely why rather than showing a generic error. Four distinct cases are handled:

- API key authentication (not a claude.ai account): "ultra (cloud review) requires a full-scope login token — run `claude auth login` to use it; see https://code.claude.com/docs/en/ultrareview."
- OAuth token missing `profile` scope: actionable message based on how the token was supplied, with a link to the docs
- Not yet in rollout: "ultra (cloud review) isn't enabled for your account yet — run `claude auth login` to refresh your entitlements"
- No claude.ai account at all: "ultra (cloud review) requires a claude.ai account — sign in to claude.ai to use it"

Evidence: Error message dispatcher (search for `"ultra (cloud review) requires claude.ai account auth"`)


### AWS Region Display Shows Source

What: When Claude Code displays the AWS region being used for Bedrock, it now indicates where the region came from.

Details:
- If set via `AWS_REGION` or `AWS_DEFAULT_REGION`: shown as-is
- If read from `~/.aws/config` or shared credentials file: shown as `"<region> (from AWS config)"`
- If using the built-in default: shown as `"<region> (default — set AWS_REGION or add a region to your AWS config)"`

Evidence: Region source formatter (search for `"(from AWS config)"` and `"default — set AWS_REGION"`)


### Team Memory Instructions — Two-Step Index Process

What: The system prompt explaining how to save team memories was updated to clearly document a two-step process: write the memory to its own file, then add a pointer to the index file. This replaces an older single-step approach.

Details:
- Step 1: write the memory to its own file in the team directory using the standard frontmatter format
- Step 2: add a one-line entry to the index file (`- [Title](file.md) — one-line hook`) — the index must not contain full memory content, only pointers
- Index entries should stay under ~150 characters each
- "The index file is loaded into your conversation context — lines after [limit] will be truncated, so keep it concise"
- New guidance: "When memories seem relevant, or the user references prior work with them or others in their organization."

Evidence: Team memory instruction builder (search for `"**Step 1** — write the memory to its own file"`)


### `--bg` with `--pool` Error Message Corrected

What: The error message shown when `--bg` is combined with `--pool` now gives the correct syntax for pool usage. Previously it said to use `--cloud`; now it says to use `--pool` directly with `-p`.

Before: `--bg and --cloud are different backends. Use 'claude --cloud '<task>'' directly to start a cloud session.`

After (when `--pool` is present): `--bg and --pool are different backends. Use 'claude -p '<task>' --pool <pool_id>' directly to start a session on the pool.`

Evidence: Error message selector (search for `"--bg and --pool are different backends"`)


### Trusted Device — Clearer Enrollment Error

What: When a session lacks a trusted device token, the error message is now "this device is not enrolled as a trusted device; run /login to enroll" (previously "run /login to enroll this device"). Small wording improvement for clarity.

Evidence: Error string (search for `"this device is not enrolled as a trusted device; run /login to enroll"`)


## Bug Fixes

- Deep-link injection prevention: `--handle-uri` now validates that no extra arguments follow the URI. Extra arguments after the URI indicate injection via the URL and are rejected with an explanatory error, directing users to place other flags before `--handle-uri` instead. (search for `"rejected deep-link invocation — unexpected arguments after the URI"`)

- Third-party transcript exclusion: Session history and transcript sharing now withholds raw transcripts that contain third-party transcript markers (`contains_3p_transcript_markers`), logging a notice instead of silently including them. (search for `"rawTranscriptJsonl withheld from session history: contains_3p_transcript_markers"`)

- Auto-mode classifier simplification: The two-stage classifier path (`nr7`, `dk5`, and the fast/thinking stage logic) was removed. The classifier now always runs a single-stage pass, eliminating a source of inconsistency when the two-stage gate evaluation disagreed with the single-stage fallback. (search for `"auto-mode"`)

- "Kill" changed to "end" in tmux session action: The label "Keep worktree, kill tmux session" was renamed to "Keep worktree, end tmux session" to use less alarming language. (search for `"Keep worktree, end tmux session"`)


## Notes

The `--plugin-dir-no-mcp` flag is intended for SDK embedders. If you are a plugin author whose host application manages MCP connections on your plugin's behalf, use `--plugin-dir-no-mcp` instead of `--plugin-dir` to prevent the engine from also connecting to those same MCP servers.

The Artifact tool is rolling out gradually via the `tengu_cobalt_plinth` feature flag. Users without access will not see the tool in their available tool list. Set `CLAUDE_CODE_DISABLE_ARTIFACT=1` if you need to suppress it once it becomes available for your account.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.172-2.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.172.txt`
