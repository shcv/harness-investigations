# Changelog for version 2.1.167

## Summary

This is a small patch release focused on host-provider integration. When running under `CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST`, auth validation is now bypassed and HTTP proxy settings from project/user config files are no longer forwarded to the host, preventing configuration conflicts in managed environments like IDEs.

## Improvements


### Managed Host: Auth Validation Bypass

When `CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST` is set, the auth force-login-org check now returns `{ valid: true }` immediately instead of running the full validation pipeline. Previously this path would still evaluate org PIN enforcement and other auth guards, which could produce false negatives in environments where the host is entirely responsible for authentication.

Details:
- Applies only when `CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST` is set (not just `CLAUDE_CODE_HOST_AUTH_ENV_VAR`)
- If a force-login-org policy is also present, the event `auth_force_login_org / managed_by_host_under_pin` is still logged for telemetry
- Normal users unaffected; relevant only for IDE and enterprise host integrations

Evidence: auth validation short-circuit (search for `"auth_force_login_org"` and `"managed_by_host_under_pin"`)


### Managed Host: Proxy Settings Now Filtered from Forwarded Config

When Claude Code runs under `CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST` (not merely `CLAUDE_CODE_HOST_AUTH_ENV_VAR`), HTTP proxy environment variable names — `HTTP_PROXY`, `HTTPS_PROXY`, and `NO_PROXY` — are now stripped from the settings object forwarded to the host before it is read by the host process.

Previously, if a project's `settings.json` or `CLAUDE.md` env section specified proxy variables, those values could reach the host and override its own network routing. This fix ensures the host controls its own proxy configuration without interference from Claude Code settings files.

Details:
- Behavior change is scoped to the explicit flag (`CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST`) to avoid affecting installations that set `CLAUDE_CODE_HOST_AUTH_ENV_VAR` without the managed-host flag
- The distinction is tracked internally via a new `managedByHostFlag` boolean added to the host state object, separate from the broader `managedByHost` flag that also covers `CLAUDE_CODE_HOST_AUTH_ENV_VAR`

Evidence: proxy filter function (search for `"HTTP_PROXY"` near settings filtering logic); state initialization (search for `"managedByHostFlag"`)


### MCP Marketplace: Official Scope Check Extracted as Standalone Function

The inline logic for determining whether an MCP marketplace entry comes from an officially recognized scope (e.g., `claude-code-marketplace`, `anthropic-marketplace`, `agent-skills`) has been extracted into a dedicated helper. This ensures the check is consistent with the same approval set used by MCP permission and auto-update logic elsewhere in the codebase.

No behavior change for users. Affects how LSP server recommendations from MCP marketplace plugins are tagged as `isOfficial`.

Evidence: new helper (search for `"claude-code-marketplace"` near `K$H` Set definition)

## Notes

No user-facing breaking changes. All modifications are internal plumbing for host-managed (IDE/enterprise) deployments.


Generated with:
- tool: `harness-investigations@1d6cc84-dirty`
- provider: `claude`
- model: `claude-sonnet-4-6`
- primary diff: `archive/claude-code/changes/changes-v2.1.167-2.md` (filtered astdiff)
- string diff: `archive/claude-code/changes/string-diff-v2.1.167.txt`
