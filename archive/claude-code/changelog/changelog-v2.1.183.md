# Changelog for version 2.1.183

## Summary

This release removes the `/migrate` command and its `claude migrate` CLI counterpart, which previously allowed importing configuration from OpenAI Codex and Google Gemini CLI. No new user-facing features are added. The rest of the diff is internal refactoring and a version bump.

## Removed Features

### /migrate Command Removed

What: The `/migrate` slash command and the `claude migrate` CLI subcommand have been deleted. These were used to import MCP servers, slash commands, subagents, skills, and instruction files from OpenAI Codex (`~/.codex/config.toml`, `AGENTS.md`, `prompts/`) and Google Gemini CLI (`~/.gemini/settings.json`, `GEMINI.md`, `commands/`) into Claude Code.

Details:
- The interactive checkbox picker for selecting which items to import is gone.
- The `--dry-run` flag (preview without writing) is gone.
- The `--yes` flag (headless auto-import of safe user-level items) is gone.
- The fallback skill generator that created a `/migrate-to-claude-code` SKILL.md for items that couldn't be mapped automatically is gone.
- The `claude migrate [codex|gemini]` terminal entrypoint no longer exists.
- Both the interactive (terminal) and non-interactive (headless/API surface) code paths are removed.

If you previously used this workflow, your already-imported files remain unchanged. To bring over any remaining Codex or Gemini config, copy the relevant entries manually into your Claude Code settings, MCP config, or `~/.claude/` directories.

Evidence: All strings unique to the migrate feature are absent from v2.1.183 (search for `"Import config from another AI coding agent"`, `"OpenAI Codex"`, `"Google Gemini CLI"`, `"tengu_migrate_scan"`) — none are found in the new build.

## Notes

This is a net-removal release. If you were relying on `claude migrate` as part of an onboarding script or documentation, remove those steps. No replacement command or flag was added in this version.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.183.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.183.txt`
