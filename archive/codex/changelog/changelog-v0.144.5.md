# Changelog for version 0.144.5

## Official Release Highlights

This release sharpens dangerous-command detection and improves the clarity of rejection messages. Per the upstream notes:

- The `rm` force-option check now covers many more invocation forms beyond the original `rm -f` / `rm -rf` exact matches.
- When Codex blocks a command, the rejection reason is now specific to the type of violation rather than always saying "blocked by policy."


## Additional Changes Beyond Official Notes


### Forced `rm` detection inside complex shell scripts

The previous shell-script scanner only recognized dangerous commands in simple sequential pipelines. The new implementation parses the full shell syntax tree and walks every command node, so `rm -f` is caught anywhere it appears — inside `for` loops, `if`/`then`/`fi` blocks, command substitutions, pipelines, and `trap` action strings.

Examples that are now detected:

```bash
for target in /tmp/a /tmp/b; do rm -rf "$target"; done
if test -d /tmp/x; then rm --force /tmp/x; fi
echo "$(rm -rf /tmp/example)"
bash -c 'rm -rf /tmp/example'
trap 'rm -rf /tmp/example' EXIT
```

The scanner also traverses `env VAR=val rm -rf …` invocations, stripping environment-variable prefixes before checking the actual command. A recursion depth cap of 8 prevents pathological nesting from running forever.

Code references:
- `parse_shell_lc_literal_commands()` in `codex-rs/shell-command/src/bash.rs`
- `dangerous_command_match_for_env()`, `dangerous_command_match_for_trap()` in `codex-rs/shell-command/src/command_safety/is_dangerous_command.rs`


### Expanded forced-`rm` flag matching

The old check matched only `rm -f` and `rm -rf` by comparing exactly the second argument. The new `rm_args_include_force_option()` function scans all arguments up to `--` and accepts any of the following:

- `--force` (long form)
- Any short-option cluster containing `f` regardless of order (`-fr`, `-r -f`, `-Rf`, etc.)
- The force flag appearing after the target path (`rm /path -f`)
- Full path to the binary (`/bin/rm -rf …`)

Commands that are explicitly NOT dangerous under the new logic:

- `rm -r /tmp/example` (recursive without force)
- `rm -- -f` (double-dash ends option parsing; `-f` becomes a filename)

Code references:
- `rm_args_include_force_option()` in `codex-rs/shell-command/src/command_safety/is_dangerous_command.rs`
- `DangerousCommandMatch` enum (`ForcedRm` | `Other`) in the same file


## Bug Fixes

- Dangerous commands are now always forbidden when `AskForApproval::Never` is set, even if the sandbox is explicitly disabled (`PermissionProfile::Disabled` / `PermissionProfile::External`). Previously Codex would allow the command to run in that specific configuration. (`render_decision_for_unmatched_command()` in `codex-rs/core/src/exec_policy.rs`)

- When a command is blocked because it matched a prompt-style rule (not a hard-deny rule) but prompts are disabled, Codex now preserves the original policy-level rejection reason for generic dangerous commands while surfacing the specific `rm -f` message for force-remove matches. Previously both cases received the same generic reason. (`derive_rejected_prompt_reason()` in `codex-rs/core/src/exec_policy.rs`)


Generated with:
- tool: `harness-investigations@d5cccf8-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/codex/diff/v0.144.5.diff` (raw diff)
- official release notes: `archive/codex/changes/release-notes-v0.144.5.md`
