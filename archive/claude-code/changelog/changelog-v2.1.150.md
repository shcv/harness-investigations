# Changelog for version 2.1.150

## Summary
Claude Code 2.1.150 is a very small release. The diff shows no new user-facing commands, CLI flags, settings, tips, or error-message changes beyond the version/build metadata update. The only non-version structural change is a new server-controlled prompt-context slot named `heron_brook`, which appears to be dark-launched infrastructure rather than a feature users can invoke directly.

## In Development

Features with infrastructure added but not yet enabled. These are shipped "dark" and may become available in future versions.


### Server-Provided Heron Brook Guidance [In Development]
What: Claude Code can now add an extra prompt-context section from a server-provided or locally resolved `tengu_heron_brook` value.

Status: Feature-flagged/dark-launched. There is no user-facing command, setting description, tip, or documented invocation in this diff.

Details:
- A new helper reads `clientDataCache?.tengu_heron_brook` first, then falls back to `v$("tengu_heron_brook", "")`.
- If that value is a non-empty string, it is inserted into the generated context under a new `heron_brook` section.
- This replaces a previous `ant_model_override` context section, but that old section called a helper that returned `null`, so the removed section appears to have been inert.
- Because the string diff contains only build time and git SHA changes, this does not expose new user-facing text in the CLI.

Evidence: Prompt-context insertion reads the server/config value `tengu_heron_brook` and registers `Rv("heron_brook", () => nAA())`; both strings are absent from `pretty-v2.1.149.js` and present only in `pretty-v2.1.150.js` (search for `"tengu_heron_brook"` and `"heron_brook"`).

## Notes
No official release note file for `2.1.150` was present in the local changelog archive, and the AST-extracted string diff contains only the new build timestamp (`"2026-05-23T01:22:49Z"`) and git SHA (`"28d4819e0f0a51840356d175c2a710f0c83db5b4"`).


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.150.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.150.txt`
