---
allowed-tools: Read, Grep, Glob, LS, Task
description: Generate a user-focused changelog from code differences between versions
---

You are writing a changelog for Claude Code, an interactive CLI application, by reading the code changes between two releases. Readers are Claude Code users who want to know what they can do now that they couldn't before, and what is coming next. Official release notes are often brief or missing; reading the code is how this changelog adds value.

These instructions may be run by Claude Code or by Codex. If a tool named in the frontmatter is unavailable, use the closest read-only equivalent (`rg`, `sed`, targeted reads). Do not rely on subagents unless the active provider exposes them for this run.

## Inputs

- **Filtered AST diff** (astdiff output): structural changes between the prettified bundles, grouped into added, removed, and modified functions. Renames and version-bump noise are already filtered out. A 100% match score does not mean behavior is unchanged.
- **String diff**: string literals added and removed, extracted with an AST parser. It is the fastest way to spot new commands, flags, settings, messages, and tips.
- **Source files**: `pretty/pretty-v{old}.js` and `pretty/pretty-v{new}.js`, plus original module sources for split-module releases. Use them to understand a change and to check whether something already existed in the previous version.

The prompt says which of these are available for this run. When only a raw diff is available, expect more noise and lean harder on the string diff and the source.

Scope: the npm package contains only the CLI. VSCode extension, SDK, and native-installer changes are not visible here; skip them.

## Reading Minified Code

Identifiers are mangled and change every build (`$qB()`, `Sz2`). String literals and property keys survive, so they are what you search for and what you quote in the changelog:

| Pattern | Meaning |
|---------|---------|
| `"/command"`, `"--flag"` | Slash commands and CLI flags |
| `process.env.CLAUDE_CODE_*` | User-configurable environment variables |
| `.describe("...")` | Settings schema; the string is the setting's own documentation |
| `tengu_*` | Server-controlled feature gates |
| `"allowed-tools"`, `"user-invocable"`, `"context"` | Skill, agent, and command frontmatter fields |
| `"Bash("`, `"Read("`, `:*)` | Permission rule syntax |
| `id:` / `content:` entries in tip arrays | Tips; often the plainest description of a feature |

## Enablement

New code is not always a usable feature. Before calling something new, determine its state:

- **Enabled**: reachable without gates. Document as a feature.
- **Gradual rollout**: behind a `tengu_*` gate that may be on for some users. Document as a feature, labelled `[Gradual Rollout]`, noting the gate's default when visible.
- **In development**: gated off by default, stubbed (detector returns `!1`), or fully built but not wired to any entry point. Document under In Development.

Watch for tips or help text that advertise an in-development feature (a tip with `isRelevant: async () => !0` for a stubbed feature). Users will see the tip but the feature won't work; call that out.

## What to Include

Include anything a user could notice: new commands, flags, settings, environment variables, modes, UI, changed defaults, new or changed messages, fixed behavior, and removed functionality.

Exclude: renames, moved code, refactors with identical behavior, import changes, caching or memoization changes, telemetry (unless user-configurable), build and bundling artifacts, and anything that already existed in the previous version.

## Prioritization

Order matters more than completeness. Put effort where readers get the most value:

1. **New features**: new user-visible capabilities. Order by user impact first, then by size. A headline feature that changes how people work comes before a niche flag. Give each one enough detail to use it.
2. **In development**: features that are present but not yet usable. This is what code reading reveals ahead of any announcement, so describe what each will do and how far along it looks.
3. **Everything else**: improvements, fixes, removals, and minor additions, as a compact one-line-per-item list.

Breaking changes and behavior changes that require user action belong in the summary, and get migration guidance in Notes.

## Output Format

Write in this structure. Omit any section with nothing in it.

````markdown
# Changelog for version X.X.X

## Summary

Two or three sentences naming the most significant changes.

## New Features

### Feature Name

What it does and why a user would want it, in a short paragraph.

```bash
claude --example-flag
```

- Notable options, limits, or requirements (only if useful)


### Another Feature [Gradual Rollout]

...

## In Development

### Feature Name

What it will do when enabled, how complete it looks, and what gates it
(for example, the `tengu_feature_name` gate, off by default).

## Other Changes

- Improved `/command` output to show remaining quota
- Added `CLAUDE_CODE_EXAMPLE` environment variable to disable X
- Fixed resumed sessions losing their working directory
- Removed the deprecated `--old-flag` option

## Notes

Migration guidance for breaking changes.
````

Guidelines:

- Show usage from the user's side (commands, flags, settings JSON, environment variables), never as internal function calls.
- In Other Changes, start each item with a verb (Added, Improved, Changed, Fixed, Removed) and keep it to one line. List changes that could break an existing setup first (changed defaults, narrowed permission matching, reordered hooks), then improvements, then fixes.
- Keep Other Changes to what a user would actually notice: merge related items into one line and drop plumbing, wording tweaks, and narrow edge cases. A few dozen lines is plenty for a large release.
- Within New Features, list fully enabled features before ones that need opt-in or are still rolling out.
- Quote exact user-facing strings, flag names, and setting keys in backticks. Do not cite mangled identifiers or line numbers.
- Do not use emoji in headings, horizontal rules (`---`), or bold field labels. Leave a double blank line before each `###` heading.
- Begin directly with `# Changelog for version X.X.X`, with no preamble or commentary about your process.
