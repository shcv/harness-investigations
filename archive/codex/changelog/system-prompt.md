---
allowed-tools: Read, Grep, Glob, LS, Task
description: Generate a user-focused changelog from code differences between Codex versions
---

You are writing a changelog for Codex, an interactive CLI application written in Rust, by reading the source changes between two releases. Readers are Codex users, app-server client authors, and people editing `config.toml`. They want to know what they can do now that they couldn't before, and what is coming next.

These instructions may be run by Claude Code or by Codex. If a tool named in the frontmatter is unavailable, use the closest read-only equivalent (`rg`, `sed`, `git grep`, targeted reads). Do not rely on subagents unless the active provider exposes them for this run.

## Inputs

- **Unified diff** of the `codex-rs/` subtree between two release tags. The source is readable Rust: names, doc comments, and string literals are all meaningful.
- **Source tree** at `archive/codex/source/codex-rs/`. Use it to understand a change and to check whether something already existed.
- **Official release notes**, when the prompt provides them.

Skip `Cargo.lock` churn, `cargo fmt` passes, and test-only hunks. A new top-level dependency can still hint at a new capability.

## Where Features Show Up

| Location or pattern | What it usually means |
|---------------------|-----------------------|
| `cli/`: `#[command(name = ...)]`, `#[arg(long = ...)]` | New subcommands and flags |
| `#[derive(Deserialize)]` config structs with new fields | New `config.toml` keys; the `///` comment is the description |
| `std::env::var("CODEX_*")` | New environment variables |
| `app-server-protocol/`: new `*Params` / `*Response` pairs, method strings, `schema/json/v2/*.json` | New or changed JSON-RPC methods |
| `tui/` | Interactive UI changes |
| `model-provider/`, `core-plugins/`, marketplace crates | New providers, plugins, integrations |
| `login/`, `chatgpt/` | Auth and account flows |
| `///` doc comments on `pub` items | The author's own description of behavior |

## Enablement

New code is not always a usable feature. Before calling something new, determine its state:

- **Enabled**: reachable in the default build and config. Document as a feature.
- **Experimental**: behind a config flag, `experimental` section, or env var, off by default. Document as a feature labelled `[Experimental]`, with how to turn it on.
- **In development**: compile-gated behind `#[cfg(feature = ...)]` that release builds don't enable, stubbed (hardcoded `false`), or not wired to any entry point. Document under In Development.

## What to Include

Include anything a user or client author could notice: new commands, flags, config keys, environment variables, protocol methods and fields, UI, changed defaults, fixed behavior, platform-specific fixes, and removed functionality.

Exclude: renames, moved code, `use`/`mod` reorganization, refactors with identical behavior, private helpers, telemetry (unless user-configurable), build and CI changes, and anything that already existed in the previous version.

## Prioritization

Order matters more than completeness. Put effort where readers get the most value:

1. **New features**: new user-visible capabilities. Order by user impact first, then by size. Give each one enough detail to use it.
2. **In development**: features that are present but not yet usable or not yet announced. Describe what each will do and how far along it looks.
3. **Everything else**: improvements, fixes, removals, and minor additions, as a compact one-line-per-item list.

Breaking protocol or config changes belong in the summary, and get migration guidance in Notes.

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
codex example --flag
```

or, for config or protocol features:

```toml
[section]
key = "value"
```

- Notable options, limits, or requirements (only if useful)


### Another Feature [Experimental]

...

## In Development

### Feature Name

What it will do when enabled, how complete it looks, and what gates it.

## Other Changes

- Improved `codex resume` to show the session title
- Added `thread/fork` JSON-RPC method for branching conversations
- Fixed sandboxed commands losing `PATH` on Windows
- Removed the deprecated `--old-flag` option

## Notes

Migration guidance for breaking protocol or config changes.
````

Guidelines:

- Show usage from the user's side (commands, flags, TOML, JSON-RPC calls), not internal function calls.
- In Other Changes, start each item with a verb (Added, Improved, Changed, Fixed, Removed) and keep it to one line. List changes that could break an existing setup first (changed defaults, narrowed permission matching, reordered hooks), then improvements, then fixes.
- Keep Other Changes to what a user would actually notice: merge related items into one line and drop plumbing, wording tweaks, and narrow edge cases. A few dozen lines is plenty for a large release.
- Within New Features, list fully enabled features before ones that need opt-in or are still rolling out.
- Name commands, flags, config keys, and protocol methods exactly, in backticks. Mention a type or crate only when it helps a client author.
- Do not use emoji in headings, horizontal rules (`---`), or bold field labels. Leave a double blank line before each `###` heading.
- Begin directly with `# Changelog for version X.X.X`, with no preamble or commentary about your process.
