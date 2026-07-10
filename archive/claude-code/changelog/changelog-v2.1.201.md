# Changelog for version 2.1.201

## Summary

Patch release with one internal model behavior adjustment: `claude-sonnet-5` is now
explicitly excluded from mid-conversation system prompt injection, aligning it with
the behavior already applied to claude-3-*, claude-opus-4-*, claude-sonnet-4-*, and
claude-haiku-4-5. No user-facing changes.

## Improvements

### Mid-conversation system prompt behavior corrected for claude-sonnet-5

Claude Code has an internal mechanism for injecting updated system prompts during a
conversation (referred to internally as `mid_conversation_system`). This allows context
to be refreshed mid-session on models that support it. `claude-sonnet-5` was not
previously excluded from this path, but it is now explicitly listed alongside the other
models that don't use it.

In practice this is invisible to users — it aligns the API call pattern for
`claude-sonnet-5` with that of all other current-generation Sonnet and older models.

Evidence: exclusion check updated in the `ALn` capability resolver (search for
`"claude-sonnet-5"` near `"mid_conversation_system"`)


Generated with:
- tool: `harness-investigations@03136fb-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.201.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.201.txt`
