# Changelog for version 2.1.235

## Summary

This release adds optional spell checking to the interactive prompt and gives plugin authors flexible control over where plugin evaluation suites live. It also improves persistent permission choices and provides clearer handling when an OAuth account is restricted.

## New Features


### Prompt Spell Checking

What: Claude Code can underline misspelled words as you type in the prompt.

Usage:

```json
// ~/.claude/settings.json
{
  "spellcheck": {
    "enabled": true,
    "checker": "auto",
    "language": "en_GB",
    "color": "red"
  }
}
```

Details:

- Supports installed `aspell`, `hunspell`, or `ispell`; `checker: "auto"` selects the first available one on `PATH`.
- You can select a checker-specific dictionary with `language` and customize the underline color.
- Spell checking is off by default and remains off if no supported checker is installed.
- This setting is accepted from user, managed, or flag settings only; project and local project settings deliberately do not enable it.

Evidence: Prompt-input spell checking (search for `"Turn on spell checking of the prompt input (default: false)"` and `"[spellcheck] no checker found on PATH"`).

## Improvements


### Configurable Plugin Evaluation Directories [Gradual Rollout]

Plugin evaluation suites can now live outside the fixed `evals/` directory. Use `--eval-dir` for a one-off location, or set `experimental.evals` in `plugin.json` for a plugin-wide default.

Usage:

```bash
claude plugin eval . --eval-dir quality/evals
claude plugin eval init --eval-dir quality/evals
```

```json
{
  "experimental": {
    "evals": "quality/evals"
  }
}
```

Details:

- Resolution priority is `--eval-dir`, then `plugin.json`’s `experimental.evals`, then `evals/`.
- Results follow the selected directory, helping keep multiple suites separated.
- The CLI validates that configured directories remain below the plugin root and warns before falling back to `evals/`.
- Plugin evaluation remains early access and organization-enabled; users without access receive the existing early-access message.

Evidence: Configurable eval-suite directory (search for `"--eval-dir <dir>"`, `"experimental.evals"`, and ``"`plugin eval` is currently in early access"``).


### More Precise Persistent Permission Choices

Permission prompts can offer a scoped “don’t ask again” option that saves only the applicable allow rule, instead of requiring a broad session-wide approval.

Details:

- The persistent option is offered only when Claude Code can construct a valid permission rule.
- The selected rule is written to local settings for subsequent matching requests.
- Web permission prompts can similarly persist an approval for a specific domain.

Evidence: Scoped permission persistence (search for `"Yes, and don’t ask again for:"` and `"yes-dont-ask-again-domain"`).


### Clearer Restricted-Account Sign-in Feedback

OAuth sign-in now recognizes account-hold responses and directs affected users to the restriction details or appeal page instead of presenting a generic sign-in failure.

Evidence: Restricted-account handling (search for `"Your account is on hold and can't sign in to Claude Code. View details or appeal:"`).


Generated with:
- tool: `harness-investigations@20de8b6-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.235.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.235.txt`
