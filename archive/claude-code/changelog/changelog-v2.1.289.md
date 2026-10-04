# Changelog for version 2.1.289

## Official Release Highlights

Version 2.1.289 strengthens shell and file permission enforcement, fixes local plugin refresh behavior, and makes plugin interfaces more resilient to rendering failures. Plugin authors also gain teammate support in the existing agent API, consistent agent identities, and more informative agent states.

The following covers the CLI changes in the [published release notes](https://github.com/anthropics/claude-code/releases/tag/v2.1.289), checked against 2.1.288 and 2.1.289. The separately tagged VSCode authentication change is outside this CLI analysis.


### Shell permission rules hold in more command forms

Deny and ask rules now apply more consistently when commands are nested inside compound shell expressions or preceded by environment assignments.

Details:
- On managed machines, a user-installed mod’s approval no longer overrides a deny or ask decision on a nested command.
- Sandbox auto-approval now checks the underlying command even when an environment prefix contains an expanded value, such as `TZ="$HOME"`.
- A standalone variable assignment before a command no longer causes its Bash rule to be skipped.

Existing permission rules require no syntax changes. Users may see approval prompts or refusals for commands that previously slipped through these checks.

Evidence: Command matching now includes the command with its environment prefix removed, and plugin permission decisions preserve hook attribution. Search for `"allowModsToOverrideDenyRules"`, `"Permission to use"`, and `"hook"` in the permission-decision handling.


### Read restrictions apply through symlinks

Files attached through `@` mentions, automatic changed-file updates, or IDE selections now respect Read deny rules on their resolved paths.

Details:
- Attachment handling checks the path spellings reached through symlinks before reading contents.
- Reads retain the checked file identity and recheck it when opening the file.
- If a path cannot be examined reliably, Claude can receive a reference indicating that its contents were not attached.

This closes a gap where an apparently permitted symlink could expose a denied target.

Evidence: Attachment reads now resolve and check their landing paths and carry a permission stash into the Read operation. Search for `"attached-read-"`, `"at-mention"`, and `"They could not be examined and were not attached"`.


### Organization-managed MCP sign-in tools retain their descriptions

User-installed plugins can no longer rewrite the descriptions of sign-in tools belonging to an organization-managed MCP server.

This preserves the organization’s intended authentication instructions when personal plugins also participate in tool customization.

Evidence: Managed MCP tool handling and description customization are covered by the changes. Search for `"managedMcpServers"` and `"tool.describe"`.


### Local plugins use their current source folders

Plugin listing, evaluation, and updating now reflect the source folder of a plugin installed from a local folder marketplace, instead of showing a stale installed copy. Hot reload also works when `--plugin-dir` points through a symlink.

Usage:
```bash
claude plugin list
claude plugin eval ./my-plugin
claude plugin update my-plugin@my-marketplace
claude --plugin-dir ./linked-plugin
```

Details:
- `plugin list` identifies the folder being read.
- JSON listings include `readFromFolder` and, when available, `folderVersion`.
- An update that needs no downloaded replacement explains that local edits apply at the next session start or through `/reload-plugins`.
- File watchers resolve symlinked plugin roots and map change events back to the requested path.

Evidence: Local plugin resolution distinguishes live folders from installed copies. Search for `"Read from:"`, `"re-read from its folder"`, and `"nothing to update. Edits there take effect at the next session start or /reload-plugins."`.


### Installed mods load after an upgrade

Installed mods are more reliably loaded in the first session after upgrading Claude Code.

Startup now handles rollout-state initialization and a late answer that enables installed hook modules, reducing cases where a mod remained absent until another session.

Evidence: Startup waits for hook-module rollout initialization and can trigger loading after a saved disabled state is superseded. Search for `"installed plugins' hooks modules held"` and `"installed plugins' hooks modules load late"`.


### Plugin validation checks mixed plugin and marketplace folders

Validation no longer stops at the marketplace manifest when a directory also contains a plugin manifest.

Usage:
```bash
claude plugin validate ./my-plugin
claude plugin validate ./my-plugin --json
```

Details:
- Directories containing both manifests have both validated, along with the plugin’s components.
- Plugins belonging to an Anthropic marketplace receive the appropriate validation context.
- JSON output no longer incorrectly lists a clean `plugin.json` as a problem.

Evidence: Validation help now explicitly describes checking both manifests, and manifest parsing uses the appropriate marketplace context. Search for `"both, and the plugin, if both exist"`, `".claude-plugin/plugin.json"`, and `"anthropic"`.


### Plugin agent APIs support teammates and clearer lifecycle states

The existing `$.agent.spawn()` API now handles teammate launches, while `$.agent.list()` distinguishes agents that are working, idle, or waiting.

Usage, inside a plugin hook:
```javascript
const launched = await $.agent.spawn({
  prompt: "Review the current changes",
  description: "Review changes",
  name: "reviewer"
});

const agents = await $.agent.list();
```

Details:
- A teammate launch can return both `agentId` and `teammateId`.
- Agent identity remains consistent across plugin hook events.
- Listings preserve teammate descriptions, agent types, and parent identities.
- `idle` and `waiting` convey more useful states than the previous raw task status alone.
- Teammate spawn rewrites cannot change fields such as `background` and `cwd` that do not apply to that launch.

These extend APIs that already existed in 2.1.288.

Evidence: Spawn results now extract `teammate_id`, and agent listings derive lifecycle states and deduplicate identities. Search for `"$.agent.spawn"`, `"teammate_spawned"`, `"agent.list"`, and `"not apply to a teammate"`.


### Pathological code blocks no longer freeze highlighting

Syntax highlighting now limits work on short inputs that generate excessive nesting or output, including repeated unclosed `<script>` tags and deeply nested `${` substitutions.

This prevents terminal freezes caused by unusually expensive code blocks. The published notes also report the corresponding fix for code blocks on published artifact pages.

Evidence: The highlighting implementation adds work and nesting bounds. Search for `"HighlightBoundError"` and `"highlighting this text takes more work than its length allows"`.


### Large files open faster in plugin code panes

Plugin code panes lay out highlighted content at its final width, avoiding an expensive preliminary layout followed by another layout at the actual pane width.

The benefit is most noticeable when opening large files.

Evidence: The changed code-view layout passes its available width into the highlighted view. Search for `"Code"` in the plugin pane renderer and inspect the associated width-constrained rendering changes.


### Plugin rendering failures stay contained

Several failures that could previously terminate a session or invalidate a whole plugin interface now have narrower recovery behavior.

Details:
- An unsupported Box border style is removed, allowing the Box to draw without a border.
- Asynchronous failures in on-screen handlers no longer end supervised or background sessions.
- Repeatedly growing regions are bounded during measurement rather than causing an interface failure.
- A transcript row broken by a mod’s `ui.render` result falls back to the engine’s own row.
- A failing `Client` is isolated from surrounding plugin content and reports `ui.fault`.
- Client regions can recover after a terminal drawing failure instead of remaining failed for the session.
- A band that fails to draw no longer briefly displaces the cards beneath it.

Evidence: Rendering now includes border sanitization, measurement bounds, row fallbacks, and separate Client error boundaries. Search for `"the Box is drawn with no border"`, `"the engine drew its own"`, `"ui.fault"`, and `"so it is drawn as last measured"`.


### Plugin failure messages explain what happened

Plugin authors receive clearer diagnostics when panes, bands, or Clients fail.

Details:
- Pane and band errors identify the responsible mod and explain whether nothing was drawn or the pane was closed.
- Failures without an error message receive a useful fallback reason instead of displaying only `Error` or nothing.
- Asynchronous Client rejections are attributed to their source.

Evidence: Search for `"nothing was drawn"`, `"the pane was closed"`, `"the module failed without a message"`, and `"a promise it returned was rejected"`.


### Terminal rows and plugin controls draw correctly

Several display fixes prevent stale or overlapping content:

- Plugin rows above the prompt refresh correctly while the Background tasks dialog is open in fullscreen.
- Tabs combined with stray escapes, C1 controls, or CRLF line endings no longer cause text to overwrite following rows.
- Right-aligned pane and band content respects the space reserved for close and collapse controls.
- Close and collapse controls remain one column inside the terminal edge.
- A plugin pane no longer becomes blank merely because a link uses localhost, an `@` in its path, an uppercase hostname, or a `file:` URL.

Link rendering also separates terminal behavior from the stricter validation used for remote surfaces; an unsuitable link can be rendered as plain text.

Evidence: Search for `"AbovePrompt"`, `"Background tasks"`, `"is drawn as plain text, no link made of it"`, and `"surface is sent no other link"`. The text-output changes explicitly handle tab, escape, and C1 sequences.

## Additional Changes Beyond Official Notes

These changes extend behavior beyond the items called out in the published notes.


### More conservative approval of ambiguous find commands

`find` approval checks now recognize additional option forms whose interpretation can vary between implementations or obscure a later action.

Details:
- Ambiguous combined options are rejected from automatic approval.
- Combined options that consume an argument are tracked more carefully.
- Sandbox auto-approval also rejects suspicious expanded options and unquoted glob arguments.
- Some commands that previously ran automatically may now require permission.

For ordinary filename matching, keep patterns quoted:
```bash
find . -name '*.js'
```

Evidence: Both the prefix-rule checker and sandbox approval path use the expanded option checks. Search for `"find option"`, `"is read differently by different versions of find"`, and `"Bash(find:*)"`.


### Existing selection API gains support for attached app surfaces

The CLI adds a request-and-response path for plugins to read selected text from compatible attached app surfaces through the existing `$.ui.selection()` API.

Usage, inside a plugin hook:
```javascript
const selection = await $.ui.selection();
```

Details:
- An attached client must advertise `ui_read_selection` in its `ui_attach` capabilities.
- If several clients are attached, the first nonempty selection wins.
- Results can include the selected text and the transcript row’s `instance_id` when the selection lies within one row.
- No selection, an invalid response, or no answer within five seconds resolves to no selection.
- Selection requests use the spawning host’s pipes; they are not sent over remote transport or persisted service lanes.

Status: The CLI implementation is active, but availability depends on a compatible attached client. This archive does not establish support in separately packaged apps.

Evidence: `ui.selection` existed in both versions; `ui_read_selection`, its response schema, and host dispatch are added in 2.1.289. Search for `"ui_read_selection"`, `"readSelection"`, and `"Unanswered by all within 5 s"`.


Generated with:
- tool: `harness-investigations@a4a08d7-dirty`
- provider: `codex`
- model: `gpt-6.1-sol`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.289.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.289.txt`
- source modules: `archive/claude-code/original/cli-v2.1.289.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
- official release notes: `archive/claude-code/changes/release-notes-v2.1.289.md`
