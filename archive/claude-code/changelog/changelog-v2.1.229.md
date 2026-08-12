# Changelog for version 2.1.229

## Summary

This release adds command-produced plugin sources, allowing locally installed tools to generate plugins for Claude Code to install. It also improves oversized-request recovery guidance and extends Artifact wake subscriptions to include comments sent to Claude.

## New Features


### Command-sourced plugins

What: Marketplace entries can now generate a plugin directory by running a local command.

Usage:

```json
{
  "name": "my-generated-plugin",
  "source": {
    "source": "command",
    "command": "my-tool export-claude-plugin",
    "mode": "copy"
  }
}
```

Then install or refresh the plugin normally:

```bash
claude plugin update my-generated-plugin
```

Details:

- The command must print one absolute plugin-directory path on stdout and exit successfully.
- `copy` mode, the default, copies and content-hashes the generated directory; `link` mode uses it in place for large exports on macOS and Linux.
- Claude Code re-resolves command sources during installation and updates, and once per session in the background.
- Each command requires explicit review/acceptance before it runs. Organizations can disable this source type through managed settings.

Evidence: New marketplace source schema (search for `"Plugin directory produced by a locally installed tool"` and `"Shell command that prints the absolute path of the plugin directory"`).


## Improvements


### Clearer recovery when a request is too large

Claude Code now distinguishes oversized conversations that can be reduced by removing media from ones where attachments are not the issue. It directs affected users to remove pasted or tool content, start a new session, go back with Escape, or use `/clear` as appropriate.

Evidence: Request-size guidance (search for `"Request too large for the API's"` and `"Double press esc to go back past the large content"`).


### Artifact wake subscriptions include comments

Artifact durable-wake subscriptions can now wake a remote session both when an artifact is republished and when someone sends a comment to Claude on that artifact. The session still re-reads the artifact after waking rather than receiving a live stream.

Evidence: Durable wake status (search for `"publish and to-Claude comment wakes"` and `"when a comment is sent to Claude on it"`).


## In Development

Features with infrastructure added but not yet enabled. These are shipped dark and may become available in future versions.


### Claude Design canvas [In Development]

What: Claude Code includes an early-preview `/design` workflow for creating multi-artboard visual designs as editable Artifact canvases.

Usage:

```bash
/design a landing page for a new product
```

Status: Feature-flagged

Details:

- The canvas is intended for mockups, UI flows, posters, brochures, social graphics, and other layouts users may want to refine visually.
- Where the account has the required Artifact capabilities, viewers can edit elements, use undo/redo, and save a new Artifact version; otherwise the canvas is view-and-export only, including PNG/PDF export.
- The command is gated by `tengu_ethereal_nova`, which defaults to disabled, so it is not generally available yet.

Evidence: Canvas command (search for `"Create a design canvas"` and `tengu_ethereal_nova`).


### Send an existing terminal session to the cloud [In Development]

What: `/teleport` is being extended from resuming a cloud session to offering a “Continue this session in the cloud” path.

Usage:

```bash
/teleport
```

Status: Feature-flagged

Details:

- The new menu offers both sending the current session and resuming one from claude.ai.
- The cloud session starts from the branch’s last push, so uncommitted local changes are not transferred.
- This path requires first-party Claude authentication, remote sessions permitted by policy, and the default-disabled `tengu_teleport_send_to_cloud` flag.

Evidence: Teleport menu (search for `"Continue this session in the cloud"` and `tengu_teleport_send_to_cloud`).


### Remote-session queued notifications [In Development]

What: Remote sessions now contain infrastructure to receive queued GitHub activity, scheduled triggers, and inter-session messages without injecting them directly as user prompts.

Status: Dark-launched

Details:

- The backend can send `queued_notification` events only to compatible remote clients.
- Claude Code buffers the events and has the main conversation drain them through the `ReadNotifications` tool.
- This depends on backend delivery and remote-session mode; it has no direct user-facing CLI command.

Evidence: Notification protocol support (search for `"queued_notifications"` and `"Read queued notifications"`).


Generated with:
- tool: `harness-investigations@c6e065f-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.229.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.229.txt`
