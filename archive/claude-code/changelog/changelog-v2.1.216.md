# Changelog for version 2.1.216

## Summary

This release introduces the Workshop Decision Artifact — a new interactive document type where readers make choices on a published page that flow back into the session. It also adds JWT-aware credential masking for sandboxed environments, a selective relay mode for the CCR agent proxy, and major security hardening across FileHistory restore, agent worktree removal, and the Linux sandbox.

## New Features


### Workshop Decision Artifacts

What: A new artifact type and skill that lets Claude publish a structured decision document, have a reader answer choices from the live page, then pick up those decisions and republish an updated version — iterating until the workshop is finalized.

Usage:
```
Ask Claude to "workshop" a design, brainstorm options, or drive a decide-and-revise loop.
The document is authored as a .workshop.md file, published via the artifact tool.
```

Details:
- Claude writes a Markdown file ending in `.workshop.md` — the suffix routes the publish through the workshop renderer
- Decision blocks are declared with special fenced syntax in the Markdown; readers click choices on the live page
- The session receives the decisions, applies them, and republishes an updated artifact
- Every workshop document carries exactly one finalize block to signal completion
- A companion `workshop` skill drives the entire workflow, including recognizing when a prior decision is received for a missing source file
- Artifact thumbnails and a "Workshop ·" eyebrow label are shown in the session UI

Evidence: New workshop renderer and skill (search for `".workshop.md"` or `"Workshop a document through artifact decisions"`)


### JWT Credential Masking

What: `sandbox.credentials.envVars` entries can now set `decode: "jwt"` to intelligently mask JWT tokens inside the sandbox rather than treating the token as opaque text.

Usage:
```json
{
  "sandbox": {
    "credentials": {
      "envVars": [
        {
          "name": "MY_API_TOKEN",
          "mode": "mask",
          "decode": "jwt",
          "maskClaims": ["sub", "email"]
        }
      ]
    }
  }
}
```

Details:
- Without `maskClaims`: the whole token is replaced with a structurally valid fake JWT (same three-part header.payload.signature shape, so downstream JWT parsers don't crash)
- With `maskClaims`: only the listed claims are replaced with sentinel values inside the payload; the rest of the token structure is preserved
- If the env var's value does not parse as a JWT, a warning is logged and the variable is left unprotected — the config must be fixed
- Works alongside the existing `extract` pattern approach; the two mechanisms are independent

Evidence: New JWT decode path in credential masking (search for `"decode \"jwt\""` or `"has decode \"jwt\" but its value did not verify as a JWT"`)


### Agent Proxy Selective Relay Mode

What: Two new environment variables give CCR agent-proxy users fine-grained control over which outbound hosts are tunneled versus sent over normal networking.

Usage:
```bash
# Route only listed hosts through the CCR tunnel; everything else uses normal networking
CCR_AGENT_PROXY_RELAY_MODE=selective
CCR_AGENT_PROXY_INCLUDE_HOSTS=api.anthropic.com,sso.example.com

# Route all traffic through the tunnel (existing behavior, no change needed)
CCR_AGENT_PROXY_RELAY_MODE=  # omit or leave empty
```

Details:
- `CCR_AGENT_PROXY_RELAY_MODE=selective` enables per-host routing decisions
- `CCR_AGENT_PROXY_INCLUDE_HOSTS` is a comma-separated list of hosts that must go through the tunnel; unlisted hosts use normal networking
- A startup reachability probe confirms the proxy is reachable; failures are logged with a note that all traffic 502s until the relay restarts
- If the include-host list is empty/unparsable, the proxy fails closed and tunnels everything

Evidence: New env var exports (search for `"CCR_AGENT_PROXY_RELAY_MODE"` or `"[agent-proxy] selective relay:"`)


### Shared Memory Skills

What: SKILL.md files stored inside a shared team memory's skills folder are now automatically loaded as skills for every session that uses that team memory.

Details:
- A shared memory skill is a `SKILL.md` file placed in a skills subdirectory of a synced team memory store
- Once the memory is synced, the skill loads automatically for all teammates using that memory
- Claude is instructed to create or edit a shared memory skill only when explicitly asked — and to keep the total set small (fewer than 10 workspace-wide, at most 30 total)
- Capability frontmatter (`allowed-tools`, `hooks`, `model`, `shell`) is ignored when a skill loads from a memory store; inline shell (`!` commands) does not run; symlinked files are not loaded; files over 128 KB are skipped
- Skills sourced from memory stores are listed as such in skill registries and are not loaded on Windows (requires `O_NOFOLLOW`)

Evidence: Memory store skill loading (search for `"A shared memory skill is a"` or `"memory-skills: registered"`)

## Improvements


### skill-doctor Token Usage Column

The `/skill-doctor` output now includes a `7d tokens` column showing how many tokens each skill has been attributed over the last 7 days of sessions on this machine, alongside the existing `uses` column.

Evidence: Updated skill-doctor table header (search for `"7d tokens = tokens attributed to the skill over the last 7 days of sessions on this machine"`)


### Forge Classification for PR/MR URLs

A new URL classifier detects whether a pull request / merge request URL comes from GitHub, GitHub Enterprise, GitLab, or Bitbucket by inspecting the URL shape — `/-/merge_requests/` for GitLab, `/pull-requests/` for Bitbucket, and hostname matching for GitHub vs GitHub Enterprise.

This classification is exposed as a `forge` field (`'github'`, `'github-enterprise'`, `'gitlab'`, `'bitbucket'`) on the MCP code-review and VCS tools, described as "a naming hint, not host trust."

Evidence: New forge classifier (search for `"/-/merge_requests/"` or `"Forge classification derived from the URL's shape"`)


### Auto Mode Classifier Respects Org Model Policy

When a server-configured auto-mode classifier model is excluded by the org's model policy, the classifier now logs a message and skips it gracefully instead of attempting the request.

Evidence: New skip path (search for `"Auto mode classifier: skipping server-configured classifier model"`)


### MCP Tool Schema Validation Against JSON Schema 2020-12

The CLI now bundles the full suite of JSON Schema 2020-12 meta-schemas and uses them to validate MCP server tool input schemas before loading. Tools whose schemas would be rejected by the Anthropic API are excluded at load time, and the session receives a notification listing the excluded tools and the reason. If the meta-validator is unavailable, validation fails open.

Evidence: Bundled meta-schemas (search for `"https://json-schema.org/draft/2020-12/meta/core"` or `"MCP: draft 2020-12 meta-validator unavailable — tool schema checks fail open"`)


### /auto-mode-setup Accepts --request-id

The `/auto-mode-setup` command now accepts an optional `--request-id <uuid>` as its first flag, before `--expect-sha256` and `--apply-file`. This ties a non-interactive apply to a specific proposal review session. Better error messages explain ordering constraints: `--request-id` must come first, and `--expect-sha256` must precede `--apply-file`.

Evidence: Updated `/auto-mode-setup` usage string (search for `"[--request-id <uuid>] (--wizard posture"` or `"--request-id must come first, before --expect-sha256 and --apply-file"`)


### Background Sessions Redirect /mcp and /install-github-app

When `/mcp` or `/install-github-app` is invoked in a background session without an attached terminal, the session now explicitly marks itself as "needs input" in the agent view and reports a clear guidance message rather than failing silently.

Evidence: Updated background-session guard (search for `"Can't open MCP settings while no terminal is attached to this background session"`)


### Sandbox: Linux bwrap Drops All Capabilities

The Linux sandbox (`bwrap`) now passes `--cap-drop ALL` to explicitly drop all Linux capabilities from the sandboxed process. Previously capabilities were only constrained through the user namespace; now they are also explicitly surrendered.

Evidence: New bwrap argument (search for `"--cap-drop"` in the sandbox startup path)


### sandbox.filesystem.disabled Setting Description Clarified

The setting description now explains clearly: "macOS and Linux/WSL only: skip filesystem isolation entirely while keeping network and seccomp isolation. Ignored on native Windows, where the sandboxed process runs as a separate user with no inherent rights, so skipping the filesystem rules would withhold every access grant rather than loosen them."

Evidence: Updated `.describe()` string (search for `"macOS and Linux/WSL only: skip filesystem isolation entirely"`)


### FileHistory Rewind Hardening

The file restore operation (used when rewinding to a checkpoint) now validates the destination at multiple points using `O_NOFOLLOW` to prevent time-of-check/time-of-use races. It refuses to write over symlinks, hard-linked files (nlink > 1), FIFOs, and non-regular files. Parent directory identity is verified before and during the restore. Each refusal now returns a named reason code instead of silently failing.

Evidence: New rewrite using `O_NOFOLLOW` open flags (search for `"FileHistory: [Rewind] Refusing to restore"` or `"destination became a symlink (O_NOFOLLOW)"`)


### Agent Worktree Removal Security Hardening

The function that removes agent worktrees after a session ends now validates significantly more edge cases before deleting any directory:

- Symlinked worktree paths are detected and rejected with a specific error
- Network paths (UNC, automount) are rejected
- Paths outside `.claude/worktrees/` are refused
- Unverifiable ancestry (symlink in a path component) is blocked using a new sentinel value `\x00unverified-ancestry`
- A new code path handles "rootless" worktrees (where the git root is gone) separately from regular worktrees, with its own safety checks
- Hook-managed removals now also verify path integrity before dispatching the remove hook

Evidence: New worktree removal implementation (search for `"removeAgentWorktree: refused hook removal"` or `"not directly under a .claude/worktrees directory"`)


### Worktree Git Command Verification Expanded

The shell command parser used to verify that git operations from a worktree-isolated agent stay inside the worktree now catches many more redirection patterns:

- Commands that pipe git arguments through `xargs` or `parallel` at runtime
- `find -execdir`/`-okdir` before git
- Commands that invoke `env --ignore-environment` or multi-`-C`/`--chdir` combinations
- Multiple git invocations in a single piped command
- Runtime-computed `GIT_DIR`, `GIT_WORK_TREE`, `HOME`, `XDG_CONFIG_HOME`, and `CDPATH` assignments

Evidence: Expanded command verifier (search for `"feeds git its arguments from stdin at runtime (xargs/parallel)"` or `"passes more than one -C/--chdir to env"`)


### Hook Feedback Labels Unified

The separate `Stop hook feedback:`, `TeammateIdle hook feedback:`, `TaskCreated hook feedback:`, and `TaskCompleted hook feedback:` label functions were removed and replaced with a unified `hook feedback:` prefix. The string displayed to the user is now generic and consistent across all hook types.

Evidence: Removal of per-hook label functions (search for `"hook feedback:"`)

## Bug Fixes

- Worktree path validation now rejects paths with dot segments (`..`, `.`) emitted by a `WorktreeCreate` hook, preventing potential directory traversal (search for `"the hook emitted a path with dot segments"`)
- The `assertDirChainReal` helper now correctly propagates `ELOOP` (symlink loop) and `ENOTDIR` errors as hard refusals when writing under a path, preventing writes through symlinked directories (search for `"Refusing to write under symlinked or non-directory path"`)
- A/B test cleanup: the skill tool description variant controlled by `tengu_russet_linnet` (skill desc reframe) was retired; all sessions now use the single canonical description
- Session resume handling now correctly manages the case where the agent referenced in the saved session no longer exists — it logs the situation and continues with default behavior rather than crashing (search for `"Resume: agent"`)


Generated with:
- tool: `harness-investigations@d5cccf8-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.216.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.216.txt`
