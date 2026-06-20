# Changelog for version 2.1.148

## Summary
Claude Code 2.1.148 is a very small release. The only diff-backed behavior change is in shell environment snapshot generation: Claude Code now filters single-underscore shell functions from captured snapshots again, while explicitly keeping double-underscore helper functions such as `__zsh_like_cd` and `__pyenv_init`.


### Cleaner Shell Function Snapshots
What: Claude Code’s shell snapshot script now skips single-underscore functions, which are commonly shell completion functions, while preserving double-underscore helpers used by tools such as mise and pyenv.

Details:
- For zsh snapshots, function collection changed from capturing every function with `typeset +f` to piping through `grep -vE '^_[^_]'`.
- For bash-style snapshots, function collection changed from `declare -F | cut -d' ' -f3` to the same single-underscore filter.
- The filter keeps names beginning with two underscores, so helpers like `__zsh_like_cd` and `__pyenv_init` remain available in captured shell environments.
- This may reduce snapshot noise from completion functions. One caveat: custom helpers whose names begin with exactly one underscore may no longer be captured.

Evidence: Shell snapshot function filtering in `fs_()` changed to preserve double-underscore helpers while filtering single-underscore names (search for `"grep -vE '^_[^_]'"` and `"__zsh_like_cd"`).


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `codex`
- model: `gpt-5.5`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.148.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.148.txt`
