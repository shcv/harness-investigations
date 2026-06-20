# Changelog for version 2.1.144

## Summary
Claude Code 2.1.144 renames the extra-usage flow to usage credits, adds an interactive permission explainer for approval prompts, and makes `/model` changes session-scoped unless you explicitly save a default. This release also tightens safety checks around shell-command analysis, image attachments, plugin/MCP configuration, and sandbox initialization.

### Usage Credits Command
What: `/extra-usage` has been renamed to `/usage-credits`, with hidden compatibility aliases that tell users about the rename and forward to the new command.

Usage:
```bash
claude
# then run:
/usage-credits
```

Details:
- `/usage-credits` configures usage credits to keep working when limits are hit.
- Existing `/extra-usage` invocations still work, but now display “/extra-usage is now /usage-credits”.
- Fast-mode and limit-recovery messages now point users to `/usage-credits`.

Evidence: New command and alias definitions (search for `"name: \"usage-credits\""` and `"/extra-usage is now /usage-credits"`); old version only had `"name: \"extra-usage\""`.


### Permission Explainer for Approval Prompts
What: Permission confirmations can now show a contextual explanation of what a command does, why Claude is running it, and its risk level.

Usage:
```text
When a permission prompt is open, press Ctrl+E to explain the command.
```

Details:
- The explainer asks the model to return a short explanation, first-person reasoning, a risk summary, and LOW/MEDIUM/HIGH risk level.
- It includes recent conversation context so the explanation is tied to the active task.
- If generation fails, the UI shows “Explanation unavailable” instead of blocking the permission flow.

Evidence: Permission explainer implementation (search for `"Explain this command in context."`, `"confirm:toggleExplanation"`, and `"LOW (safe dev workflows), MEDIUM (recoverable changes), HIGH (dangerous/irreversible)"`).


### Save a Model as the Default from `/model`
What: The model picker now lets users make the selected model the default for new sessions with a dedicated shortcut.

Usage:
```bash
claude
# then run:
/model
# press d on a selected model to set it as the default for new sessions
```

Details:
- `/model` selection copy now says model changes apply to the current session only.
- A new `d` shortcut appears as “set as default for new sessions”.
- This separates temporary session changes from persistent default changes.

Evidence: Model picker shortcut and copy changes (search for `"modelPicker:setAsDefault"` and `"set as default for new sessions"`). The previous version said `/model` applied to “this session and future Claude Code sessions”.


### Safer Shell Static Analysis
Claude Code’s command analyzer now catches more cases where shell syntax can execute unexpectedly or defeat static analysis.

Details:
- Detects parser gaps such as trailing input and skipped top-level input.
- Treats unscanned heredoc bodies as too complex.
- Adds zsh-specific checks for `print -P`, `jobs -x`, `set -o/+o`, glob state changes, and array-subscript expansion.
- Adds `NO_BARE_GLOB_QUAL` to the shell prefix used when disabling glob behavior.

Evidence: New shell-analysis reasons (search for `"Parser skipped input between top-level statements"`, `"Heredoc body was not scanned by the parser"`, `"'jobs -x' executes its argument as a command"`, and `"NO_BARE_GLOB_QUAL"`).


### Clearer Image Attachment Errors
Claude Code now validates image file contents instead of trusting image extensions.

Details:
- Invalid image attachments can now identify likely HTML, XML/SVG, JSON/text, PDF, or unknown binary content.
- The error suggests checking the file type or reading the downloaded content when a URL saved an error/login page instead of an image.

Evidence: Image validation diagnostics (search for `"File has an image extension but its content is not a valid PNG/JPEG/GIF/WebP"` and `"HTML document (starts with"`).


### Better Plugin and MCP Configuration Diagnostics
Project-level plugin and MCP setup errors now produce more actionable messages.

Details:
- If a project enables a plugin that is not installed locally, Claude Code tells users to run `claude plugin install ... --scope project`.
- MCP configs using top-level `servers` now get a targeted warning that Claude Code expects `mcpServers`.
- Disabled plugin hooks are read but explicitly logged as not registered.

Evidence: Plugin and MCP config warnings (search for `"plugin-not-installed"`, `"Missing \"mcpServers\" — found \"servers\" instead"`, and `"will NOT register, plugin is disabled"`).


### Hook Configuration Guidance
Hook validation now points users toward exec-form versus shell-form command configuration.

Details:
- Invalid command-hook configs get an example showing `command` plus `args` for exec form.
- The diagnostic links to `/hooks#exec-form-and-shell-form`.

Evidence: Hook validation message (search for `"Command hooks require `command`. For exec form"` and `"/hooks#exec-form-and-shell-form"`).


### Feedback Command Is Broader
The `/feedback` command is now described as a place to submit feedback, report bugs, or share a conversation.

Usage:
```bash
claude
# then run:
/feedback
```

Evidence: Command description change (search for `"Submit feedback, report a bug, or share your conversation"`). The previous version said `"Submit feedback about Claude Code"`.


### Clearer Agent View Disable Reasons
When the agent view is unavailable, Claude Code can now distinguish between the environment variable and the settings flag.

Evidence: Agent-view diagnostics (search for `"is disabled by CLAUDE_CODE_DISABLE_AGENT_VIEW"` and `"is disabled by the 'disableAgentView' setting"`).


### Configurable Secure Storage Directory
Claude Code now recognizes `CLAUDE_SECURESTORAGE_CONFIG_DIR` in several runtime paths.

Usage:
```bash
CLAUDE_SECURESTORAGE_CONFIG_DIR=/path/to/config claude
```

Evidence: Environment variable support (search for `"CLAUDE_SECURESTORAGE_CONFIG_DIR"`).


## Bug Fixes

- Sandbox initialization failures now produce clearer required-versus-optional messages, and optional sandboxing can be disabled for the rest of the session instead of failing generically (search for `"Sandbox is required but failed to initialize"` and `"Sandbox is enabled but failed to initialize"`).
- Missing `rg` now produces a direct install/use-native-binary message instead of relying on a removed bundled vendor path (search for `"ripgrep not found on PATH"`).
- Transcript write and metadata re-append failures now log concrete filesystem-style errors without treating every failure as an unclassified exception (search for `"Transcript write failed ("` and `"Metadata re-append failed ("`).
- OAuth refresh failures caused by dead refresh tokens now get a specific `invalid_grant` diagnostic (search for `"OAuth refresh: invalid_grant (refresh token dead)"`).
- Terminal raw-mode setup now checks that `setRawMode` is actually a function before calling it, avoiding crashes in streams that expose a non-callable property (search for `"typeof H.setRawMode !== \"function\""`).
- Image files shorter than a valid signature or with unsupported content now fail as invalid images instead of defaulting to PNG (search for `"return null"` near image signature detection and `"Pasted path has image extension but content is not a supported image"`).


## In Development

Features with infrastructure added but not yet enabled. These are shipped "dark" and may become available in future versions.


### Background `--exec` Launcher [In Development]
What: Infrastructure exists for a background launcher mode that would run a shell command directly and optionally name the session.

Status: Stubbed

Details:
- New strings describe `--exec requires a command` and warn that only `--name` composes with `--exec`.
- The CLI argument list includes `"--exec"`.
- The trigger path appears disabled in this build: the parser strips `--exec`-style arguments, then the exec branch uses a hardcoded disabled index, so the command path is not reachable from normal invocation.

Evidence: Disabled background exec path (search for `"--exec requires a command."`, `"warning: --exec ignores"`, and `"--exec"`).

## Notes
Migration guidance: use `/usage-credits` instead of `/extra-usage`. The old command remains as a hidden compatibility alias, but user-facing copy and recovery suggestions now use the new name.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.144.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.144.txt`
