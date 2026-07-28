# Changelog for version 2.1.215

## Summary

This release introduces a new "subagent steer" system that lets Anthropic (and users) tune how aggressively Claude delegates work to subagents. Two slash commands (`/verify` and `/code-review`) also gain a `disableModelInvocation` optimization that skips an unnecessary LLM wrap turn when these multi-agent workflows are invoked.

## Improvements


### /verify and /code-review skip the initial model round-trip

What: When `/verify` or `/code-review` are invoked as slash commands, they now bypass the initial LLM call and launch their multi-agent workflow directly.

Details:
- Previously these commands were first processed as ordinary messages, causing the LLM to read the skill prompt and then re-dispatch to subagents — an unnecessary extra turn.
- With `disableModelInvocation: true` set on both commands, the CLI now routes them straight into their workflow without that wrapper step.
- Users should notice slightly faster startup for these two commands.
- The change applies to `/code-review` and `/verify` specifically; other slash commands are unaffected.

Evidence: `disableModelInvocation: !0` added to the code-review command (search for `name: k_e` near `"code-review"`) and the verify skill registration.


### Plan mode: "spawn teammates" suggestion is now mode-aware

What: The message suggesting parallel agent work after plan mode approval now only appears when the subagent steer mode is `"default"`.

Details:
- The suggestion "If this plan can be broken down into multiple independent tasks, consider spawning named teammates…" was previously shown to all users whenever the Agent tool was available.
- It is now gated behind the new `R9r()` helper, which suppresses it in `no_nudges` and `counter_steer` modes.
- In default mode the behavior is unchanged.

Evidence: `R9r(Boolean(n))` replaces the inline conditional (search for `"consider spawning named teammates"`)

## In Development

Features with infrastructure added but not yet fully enabled. These are shipped under feature flags and/or new environment variables.


### Subagent Delegation Control (`CLAUDE_CODE_THISTLE_GREBE`) [Gradual Rollout]

What: A new three-mode system for controlling how actively Claude delegates to subagents. The mode affects tool descriptions, system prompt sections, and UI notes across the session.

Status: Feature-flagged via `tengu_thistle_grebe` (server-side A/B experiment). Users can opt in or override by setting the environment variable.

Usage:
```bash
CLAUDE_CODE_THISTLE_GREBE=counter_steer claude
CLAUDE_CODE_THISTLE_GREBE=no_nudges claude
```

Details:
- Valid values: `"default"` (current behavior), `"no_nudges"`, `"counter_steer"`
- `no_nudges` — removes "use the Agent tool instead" guidance from Glob, Grep, and EnterPlanMode tool descriptions. Hides the per-turn concurrency note in the UI.
- `counter_steer` — does everything `no_nudges` does, and additionally injects a new "## Delegating to subagents" system prompt section. This section gives Claude explicit guidance on when NOT to spawn subagents: don't delegate small bounded tasks you could finish in a few tool calls, don't fan out multiple subagents on a single modest task, don't spawn just to verify work, and brief subagents precisely the first time rather than relaunching.
- The counter_steer guidance text (search for `"Subagents multiply cost and time"`) is injected only when the Agent tool is available and `x3() === "counter_steer"`.

Evidence: New `x3()` function reads `CLAUDE_CODE_THISTLE_GREBE` → client data → GrowthBook; `WBc` holds the delegation guidance text (search for `"Subagents multiply cost and time"`); `tengu_thistle_grebe` feature flag stored in `UBc`


### Bash tool: "Command output is displayed to you, not reliably to the user" note [Gradual Rollout]

What: A new clarifying bullet is added to the Bash tool's description to help Claude understand that shell output lands in its context, not the user's view.

Status: Gated by `tengu_marl_cormorant` feature flag / `CLAUDE_CODE_MARL_CORMORANT` env var.

Usage:
```bash
CLAUDE_CODE_MARL_CORMORANT=1 claude
```

Details:
- When enabled, the Bash tool description gains: `"- Command output is displayed to you, not reliably to the user."`
- The intent is to prevent Claude from assuming the user sees raw command output that is only visible in Claude's tool result.
- Controlled by `K_c()` (search for `"tengu_marl_cormorant"`).

Evidence: `K_c()` called in the Bash tool description builder (search for `"Command output is displayed to you, not reliably to the user"`)


### Softened overwrite-protection instruction (`tengu_gault_kestrel`) [Gradual Rollout]

What: An experiment that removes the explicit verification check from Claude's overwrite/delete guidance.

Status: Gated by `tengu_gault_kestrel` feature flag / `CLAUDE_CODE_GAULT_KESTREL` env var.

Details:
- Default behavior: "Before deleting or overwriting, look at the target — if what you find contradicts how it was described, or you didn't create it, surface that instead of proceeding."
- With `tengu_gault_kestrel` active: the clause after the em-dash is removed, leaving only "Before deleting or overwriting, look at the target."
- This tests whether the shorter form is sufficient to prevent unsafe overwrites without the fuller explicit check.
- Controlled by `Y_c()` (search for `"tengu_gault_kestrel"`).

Evidence: `Y_c()` applied in the caution instruction builder; `r = Y_c() ? "" : " — if what you find contradicts..."` (search for `"tengu_gault_kestrel"`)


Generated with:
- tool: `harness-investigations@d5cccf8-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.215.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.215.txt`
