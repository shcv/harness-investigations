# Changelog for version 2.1.272

## Summary

Compared with 2.1.271, this version adds a gated artifact-editing workflow: JavaScript-driven edits, preloaded design resources, and guidance for opening artifacts before filling them. These changes require the `remote_cowork` entry point and the server-controlled `tengu_buzzing_lightning` flag, which defaults to off; they do not establish general availability in terminal sessions.


## In Development

The following implementations are present in the CLI source but depend on restricted enablement. Source inspection does not establish which accounts have access.


### Scripted Artifact Editing [In Development]

What: Claude can build or revise an artifact through a JavaScript program that performs multiple reads and writes in one tool call.

Status: Feature-flagged. Requires `tengu_buzzing_lightning`, the `remote_cowork` entry point, and artifact write availability.

Usage: In an eligible session, ask Claude to create or revise a design canvas or slide deck. Claude invokes the new `AppifactRepl` tool as part of that work; there is no new public slash command.

Details:

- A built-in runtime supports artifact database reads, updates, deletions, and batches, plus published-file access and asset operations.
- An existing artifact is bound using its URL or ID. Claude can optionally use the runtime supplied by an already-loaded user or plugin skill.
- Variables and database handles remain available throughout one call. They do not persist into subsequent calls.
- Scripts can return text and up to four PNG or JPEG images for Claude to inspect.
- Artifact operations pass through the existing validation, hooks, and permission checks. Plan mode requires approval before execution.
- Execution requires Node on `PATH`. This version refuses Windows, calls marked as remote callers, and execution that would require the sandbox.
- An uncaught error stops the remaining statements; earlier operations may already have completed.

Evidence: The tool name `"AppifactRepl"` is absent from 2.1.271 and present in 2.1.272. Search for `"Run appifact SDK JavaScript against an artifact"`, `"tengu_buzzing_lightning"`, and `"the REPL child does not run inside the sandbox in this version"`. The original modules confirm the default-false flag and the `"remote_cowork"` entry-point restriction.


### Preloaded Artifact Instructions and Design Files [In Development]

What: Eligible artifact sessions can receive type instructions, reference pages, and design-system files before Claude starts building.

Status: Feature-flagged through the same artifact-editing gate; individual reads also require the relevant tools and permissions.

Usage: Start an eligible session beside a newly created typed artifact, or ask Claude to create a design or slide deck through the existing artifact quickstart workflow.

Details:

- Opening-context handling can load a qualifying owned artifact’s type instructions and reference-file index before the first assistant response.
- The existing quickstart workflow gains a starter kit that saves type documentation and design-system resources to local scratch space.
- Follow-up guidance identifies files already saved, reducing repeated listing and download calls.
- The saved-file manifest reports skipped or unavailable resources rather than implying that every file was fetched.
- Preloading skips reads that require additional approval and avoids bypassing applicable `PreToolUse` hooks.
- Loading the type’s instructions does not mean the artifact’s own content has been read.

Evidence: Search for `"[artifactOpeningPrefetch]"`, `"[quickstartStartKit]"`, `"TYPE FILES"`, and `"DESIGN SYSTEM FILES"`. These implementation and guidance strings are absent from 2.1.271. Quickstart and the `"artifact_opening_prefetch"` record name already existed; this release adds the executable loading path and starter-kit behavior.


### Open Artifacts Before Scripted Edits [In Development]

What: The gated editing workflow opens newly created artifacts immediately so users can see them fill as scripted writes arrive.

Status: Feature-flagged; applies when the new artifact-editing tool is available in the session.

Usage: For this workflow, Claude creates the typed artifact without `auto_open: "after_first_write"`.

Details:

- Scripted writes do not trigger the existing “open after first write” mechanism.
- The CLI now activates a previously stubbed check that rejects that incompatible creation option before creating an artifact.
- The resulting message tells Claude to retry without `auto_open`, allowing the page to open at creation.

Evidence: Search for `"When you will fill it through the AppifactRepl tool instead, omit"` and `"Nothing was created. Retry this same create without"`. The `"auto_open_with_repl"` guard already existed in 2.1.271, but its tool-presence check always returned false; 2.1.272 connects it to the gated implementation.


Generated with:
- tool: `harness-investigations@9493cf6-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.272.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.272.txt`
- source modules: `archive/claude-code/original/cli-v2.1.272.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
