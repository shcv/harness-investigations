# Changelog for version 2.1.276

## Summary

Version 2.1.276 tightens automatic advisor selection when Claude Code uses a custom API endpoint. Compared with 2.1.275, the verified behavioral change prevents selecting a standby advisor unless the connection passes the first-party endpoint check.

## Bug Fixes

- Fixed automatic standby advisor selection running against custom API endpoints. When no advisor is configured and dynamic tool changes permit automatic selection, Claude Code now checks that the provider is first-party and the endpoint is recognized as Anthropic’s before choosing a standby advisor. The existing advisor rollout and model-compatibility checks still apply; this does not introduce or broadly enable advisor support.

  Evidence: Advisor selection associated with `"advisor_tool"` now calls the endpoint check using `"ANTHROPIC_BASE_URL"` and `"api.anthropic.com"`. Verified in both version snapshots and the original modules: `chunk-sb7r9zhz.js` in 2.1.275 and `chunk-d8th2spf.js` in 2.1.276. Existing availability remains controlled by `"tengu_sage_compass2"` and the experimental advisor setting.


Generated with:
- tool: `harness-investigations@e58bce7-dirty`
- provider: `codex`
- model: `gpt-6-astra`
- reasoning effort: `medium`
- primary diff: `archive/claude-code/changes/changes-v2.1.276.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.276.txt`
- source modules: `archive/claude-code/original/cli-v2.1.276.modules.json`
- source normalization: `esbuild analysis snapshot; original module text retained`
