# Changelog for version 2.1.162

## Summary

Claude Code 2.1.162 is a focused CLI release with admin-facing Cloud gateway login support, stricter safety checks around suspicious Git directories, and clearer handling for cloud sessions, notebook reads, MCP timeouts, and design-system uploads. It also improves several error messages so users know whether to retry, re-authenticate, change flags, or ask an administrator.


### Managed Cloud Gateway Login Policy

What: Enterprise managed settings can now force the Cloud gateway OIDC login flow, including an internal pre-filled gateway URL so users do not have to type it during login.

Usage:
```json
{
  "forceLoginMethod": "gateway",
  "cloudGatewayUrl": "https://your-gateway.example"
}
```

Details:
- `forceLoginMethod` now accepts `"gateway"` in addition to `"claudeai"` and `"console"`.
- Managed settings can pre-fill the Cloud gateway URL for interactive `/login`.
- The CLI now emits explicit guidance when gateway login is required but the user needs to authenticate interactively, or when a build lacks gateway support.

Evidence: Managed login schema now includes gateway (search for `"Force a specific login method: \"claudeai\" for Claude Pro/Max, \"console\" for Console billing, \"gateway\""`), and the gateway URL setting is documented internally (search for `"Cloud gateway URL to pre-fill"`).


### Safer Git Directory Detection

Claude Code now distinguishes ordinary bare-repository indicators from potentially planted `.git` file or symlink redirects. When a directory looks like it could redirect Git to an unsafe location, Git commands require approval with a clearer warning.

Details:
- Canonicalizes `.git` redirect targets and symlink paths before trusting them.
- Detects `.git` files containing NUL bytes and uncanonicalizable redirects as unsafe.
- Separates bare-repo warnings from `.git` redirect warnings, making the approval reason more specific.

Evidence: Git safety gate now returns `"gitdir-redirect-plantable"` and warns about `.git` redirects (search for `"The .git file or symlink here redirects to a location that cannot be verified as safe"`).


### Clearer Cloud Session Flag Validation

Cloud sessions through `--remote` now fail earlier with specific messages when combined with incompatible modes or non-interactive execution.

Usage:
```bash
claude --remote "investigate the failing test"
claude --remote <session-id>
```

Details:
- `--remote` now explicitly rejects `--print`, `--continue`, `--resume`, `--from-pr`, `claude ssh`, `claude assistant`, `cc://` connect URLs, and `--teleport`.
- Non-interactive invocations now explain that cloud sessions require a TTY instead of silently falling back to local behavior.
- The attach guidance now points users to `claude --remote <session-id>` and `claude.ai/code`.

Evidence: Cloud-session validation (search for `"Error: --remote cannot be combined with --print"` and `"Cloud sessions are interactive only"`).


### Better Notebook Read Validation

Notebook reads now report malformed `.ipynb` files with more actionable errors. Instead of generic parsing failures, users can tell whether the notebook is invalid JSON or has an invalid top-level `cells` structure.

Evidence: Notebook read errors (search for `"Notebook file is not valid JSON (it may be truncated, corrupted, or still being written):"` and `"Notebook file is not a valid Jupyter notebook (top-level \"cells\" must be an array of cell objects)."`).


### MCP Tool Timeout Semantics Clarified

Per-server MCP tool timeout documentation now says values below 1000ms are ignored and fall through to `MCP_TOOL_TIMEOUT` or the default, rather than being floored to 1000ms. The status display also marks sub-1000ms values as ignored.

Evidence: MCP timeout description (search for `"Values below 1000ms are ignored"` and `"(ignored: below 1000ms minimum)"`).


### DesignSync Upload Prompts Are More Explicit

Design-system upload approval now shows the destination project, source folder, upload patterns, and delete patterns. OAuth consent messaging also calls out that approving design scopes grants ongoing write access to design projects.

Evidence: DesignSync approval copy (search for `"Upload design system"`, `"To project:"`, `"From folder:"`, and `"Approving also grants Claude ongoing write access to your design projects."`).


### Usage Credit Display Adds Cowork One-Time Credits

The usage display can now show a separate “Claude Code and Cowork credit” bucket with one-time credit expiration text when the account has that credit type.

Evidence: Usage credit rendering (search for `"Claude Code and Cowork credit"` and `"One-time credit"`).


### Devin Desktop Detection in IDE-Related Flows

IDE/process detection now recognizes Devin Desktop process names on macOS, Windows, and Linux, alongside existing editors such as VS Code, Cursor, Windsurf, and JetBrains IDEs.

Evidence: IDE process scan strings now include Devin Desktop (search for `"Devin Helper"`, `"Devin.exe"`, and `"devin-desktop"`).


## Bug Fixes

- Fixed `claude purge` reporting when it cannot remove a project entry from `.claude.json`; it now tells users the config write failed and suggests checking config directory writability. Evidence: purge write failure (search for `"Failed to remove projects[\""` and `"is your config directory writable?"`).

- Fixed cloud-session availability messaging for cases where organization policy cannot be verified. Users now get a network/policy verification message instead of only a disabled-policy error. Evidence: cloud session precondition check (search for `"Couldn't verify your organization's policy for cloud sessions"`).

- Improved connector/MCP auth failures so users are told when a hosted connector needs to be connected from Claude settings, when a connector registry is unavailable, or when an OAuth refresh token is invalid. Evidence: connector and auth errors (search for `"ConnectorOptInRequired"`, `"Connect it via Settings"`, and `"OAuth refresh token is no longer valid; run /login to re-authenticate"`).

- Improved pasted-image failure handling by adding an explicit clipboard-read failure message. Evidence: image paste errors (search for `"Couldn't read an image from the clipboard"`).

## Notes

No official release-note file for `2.1.162` was present in the local archive, so this changelog is based on the filtered AST diff, AST-extracted string diff, and direct searches of `pretty-v2.1.161.js` and `pretty-v2.1.162.js`.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.162.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.162.txt`
