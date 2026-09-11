# Changelog for version 2.1.269

## Summary

Plugin evaluation is now generally available, with HTML reporting and optional private report publishing. This release also adds PR-comment posting for cloud code reviews, clearer Bash edit diffs, and a safety fix for unsafe globbed read paths.

## New Features

### Generally available plugin evaluation

What: `claude plugin eval` and `claude plugin eval init` are now available by default for authoring and running plugin evaluation suites.

Usage:

```bash
claude plugin eval ./my-plugin --ablation with-without
```

Details:

- Evaluate a plugin by path, installed name, or `plugin@marketplace` identifier.
- `claude plugin eval init` starts an interactive workflow for creating an eval suite.
- The first run against an untrusted plugin directory asks for confirmation; CI can use `--trust-plugin` only for plugins you trust.
- A server-side kill switch can temporarily disable the command, but it is otherwise generally available rather than organization-gated early access.

Evidence: Plugin evaluation now reports it is “generally available; no enablement setting is needed,” replacing the prior “currently in early access” state (search for `"claude plugin eval"` and `tengu_sharded_snowflake`).


### HTML reports for plugin evaluations

What: Plugin evaluation runs can produce a self-contained HTML report and, where supported, publish it privately to claude.ai.

Usage:

```bash
claude plugin eval ./my-plugin --report ./eval-report.html --no-publish
```

Details:

- `--report <path>` writes scores, prompts, and grader verdicts to a specified HTML file.
- Reports otherwise go to the results directory.
- Publishing is enabled by default when the account supports it; use `--no-publish` to keep reports local.
- `--publish-report` requires publishing and explains why it is unavailable if the account, provider, or privacy mode cannot publish.

Evidence: Eval options include `"--report <path>"`, `"--publish-report"`, and `"--no-publish"`; report publishing says `"Publishing report to claude.ai (private to you)"`.


### Post cloud-review findings to pull requests

What: Cloud-hosted multi-agent reviews can now post their completed findings as a single comment on the reviewed pull request.

Usage:

```bash
claude ultrareview 123 --post
```

Details:

- `--post` is for PR targets and posts one plain comment rather than a GitHub review.
- Requires a Claude account with a connected GitHub account.
- Posting is limited to github.com pull requests; `--no-post` remains the default behavior.

Evidence: `ultrareview` adds `"--post"` with the description `"Post the finished review's findings to the PR as you"`.

## Improvements

### Bash-command edit diffs

Claude Code can now show a concise diff of files changed by a Bash command, making shell-driven edits easier to inspect and making changed-file information available to PostToolUse Bash hooks.

Usage:

```json
{
  "bashEditDiffEnabled": false
}
```

Details:

- Set `bashEditDiffEnabled` to `false` to disable the display.
- `CLAUDE_CODE_BASH_EDIT_DIFF` can also override the behavior.
- By default, diffs appear when Bash handles file edits in auto or bypass-permissions modes; other modes require an explicit user, flag, or policy setting to enable them.

Evidence: New setting description `"Whether the Bash tool shows a diff of the files a Bash command changed"` and environment override `CLAUDE_CODE_BASH_EDIT_DIFF`.

## Bug Fixes

- Read requests that place a glob before `..` are now refused when outside-working-directory read blocking or Read deny rules apply. This prevents shell expansion from bypassing the path that Claude Code intended to validate. Evidence: `"A glob before the '..'"` and `"Spell the path without the glob."`


Generated with:
- tool: `harness-investigations@81531cb-dirty`
- provider: `codex`
- model: `gpt-5.6-terra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.269.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.269.txt`
- source modules: `archive/claude-code/original/cli-v2.1.269.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
